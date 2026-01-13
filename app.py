import streamlit as st
import cv2
import numpy as np
import pytesseract
import pandas as pd
from PIL import Image
from streamlit_drawable_canvas import st_canvas

st.set_page_config(page_title="Pen-Marking Schedule Learner", layout="wide")

st.title("🖊️ Pen-Marking Schedule Learner")
st.write("1. Upload Image | 2. Draw a rectangle over ONE class to 'teach' the color | 3. Get results")

# --- STEP 1: UPLOAD ---
uploaded_file = st.file_uploader("Upload Schedule", type=["png", "jpg", "jpeg"])

if uploaded_file:
    # Use PIL to open the image
    bg_image = Image.open(uploaded_file)
    
    # FIX: Convert PIL image to a NumPy array to avoid internal AttributeErrors 
    # in the drawable-canvas library's image_to_url function.
    bg_array = np.array(bg_image)
    
    w_orig, h_orig = bg_image.size
    
    # Scale for display to fit the screen
    display_width = 1000
    ratio = display_width / w_orig
    display_height = int(h_orig * ratio)

    # --- STEP 2: PEN TOOL (RECTANGLE) ---
    st.subheader("Draw a rectangle over a dark green class box")
    
    # We pass the NumPy array (bg_array) instead of the PIL object
    canvas_result = st_canvas(
        fill_color="rgba(255, 165, 0, 0.3)",
        stroke_width=2,
        stroke_color="#ff0000",
        background_image=Image.fromarray(bg_array), # Re-wrap just for the component
        update_streamlit=True,
        height=display_height,
        width=display_width,
        drawing_mode="rect",
        key="canvas",
    )

    # --- STEP 3: PROCESS DATA ---
    if canvas_result.json_data is not None:
        # Use .get() to safely access the list of drawn objects
        objects = canvas_result.json_data.get("objects", [])
        
        if len(objects) > 0:
            st.success(f"System learning from your marking...")
            
            # Use the most recent mark
            last_mark = objects[-1]
            
            # Rescale coordinates back to original image size
            mx = last_mark["left"] / ratio
            my = last_mark["top"] / ratio
            mw = last_mark["width"] / ratio
            mh = last_mark["height"] / ratio

            # Convert to OpenCV BGR for processing
            img = cv2.cvtColor(bg_array, cv2.COLOR_RGB2BGR)
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            
            # Sample color from your pen mark
            roi_hsv = hsv[int(my):int(my+mh), int(mx):int(mx+mw)]
            
            if roi_hsv.size > 0:
                avg_h = np.median(roi_hsv[:,:,0])
                
                # Create mask based on YOUR learned color
                lower_green = np.array([avg_h - 10, 40, 20])
                upper_green = np.array([avg_h + 10, 255, 255])
                mask = cv2.inRange(hsv, lower_green, upper_green)

                # Grid Layout (7 cols, 13 rows)
                col_w = w_orig / 7
                row_h = h_orig / 13
                
                DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
                HOURS = ["7-8", "8-9", "9-10", "10-11", "11-12", "12-1", "1-2", "2-3", "3-4", "4-5", "5-6", "6-7"]
                results = []

                for c in range(1, 7): # Skip Time column
                    for r in range(1, 13): # Skip Header row
                        x1, y1 = int(c * col_w), int(r * row_h)
                        x2, y2 = int((c+1) * col_w), int((r+1) * row_h)
                        
                        cell_mask = mask[y1:y2, x1:x2]
                        
                        # If cell is > 20% green, it's a class
                        if np.sum(cell_mask == 255) / cell_mask.size > 0.2:
                            cell_roi = img[y1:y2, x1:x2]
                            cell_roi = cv2.resize(cell_roi, None, fx=2, fy=2)
                            gray = cv2.cvtColor(cell_roi, cv2.COLOR_BGR2GRAY)
                            thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
                            
                            text = pytesseract.image_to_string(thresh, config='--psm 6').strip()
                            is_diag = np.mean(cell_mask[:10, -10:]) < 100 

                            if text:
                                lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 1]
                                results.append({
                                    "Day": DAYS[c-1],
                                    "Time": HOURS[r-1],
                                    "Class": lines[0] if len(lines) > 0 else "N/A",
                                    "Location": lines[1] if len(lines) > 1 else "N/A",
                                    "Type": "30-min Shift" if is_diag else "Full Hour"
                                })

                if results:
                    df = pd.DataFrame(results)
                    st.subheader("Extracted Schedule")
                    st.dataframe(df, use_container_width=True)
                    st.download_button("Download CSV", df.to_csv(index=False).encode('utf-8'), "schedule.csv", "text/csv")
        else:
            st.info("Draw a rectangle over one of the green class boxes to start detection.")
