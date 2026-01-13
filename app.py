import streamlit as st
import cv2
import numpy as np
import pytesseract
import pandas as pd
from PIL import Image
from streamlit_drawable_canvas import st_canvas

st.set_page_config(page_title="Pen-Marking Schedule Learner", layout="wide")

st.title("🖊️ Pen-Marking Schedule Learner")
st.write("1. Upload your image. 2. **Draw a rectangle** over one or two class boxes. 3. The system will learn the grid and extract everything.")

# --- STEP 1: UPLOAD ---
uploaded_file = st.file_uploader("Upload Schedule", type=["png", "jpg", "jpeg"])

if uploaded_file:
    bg_image = Image.open(uploaded_file)
    w, h = bg_image.size
    # Resize for display if too large, while keeping aspect ratio
    max_display_width = 800
    display_ratio = max_display_width / w
    display_w = int(w * display_ratio)
    display_h = int(h * display_ratio)

    # --- STEP 2: PEN TOOL (CANVAS) ---
    st.subheader("Mark a few classes with the Rectangle Tool")
    canvas_result = st_canvas(
        fill_color="rgba(255, 165, 0, 0.3)",  # Transparent orange
        stroke_width=2,
        stroke_color="#ff0000",
        background_image=bg_image,
        update_streamlit=True,
        height=display_h,
        width=display_w,
        drawing_mode="rect",
        key="canvas",
    )

    # --- STEP 3: LEARN & PROCESS ---
    if canvas_result.json_data is not None:
        objects = canvas_result.json_data["objects"]
        if len(objects) > 0:
            st.success(f"System learned from {len(objects)} markings!")
            
            # Analyze the first marking to set the grid
            first_mark = objects[0]
            # Convert canvas coordinates back to original image coordinates
            mx = first_mark["left"] / display_ratio
            my = first_mark["top"] / display_ratio
            mw = first_mark["width"] / display_ratio
            mh = first_mark["height"] / display_ratio

            # Calculate Grid based on the position of your marking
            # (Assuming standard 7-col, 13-row structure)
            col_w = w / 7
            row_h = h / 13
            
            # Convert image for OpenCV
            img = cv2.cvtColor(np.array(bg_image), cv2.COLOR_RGB2BGR)
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            
            # LEARN COLOR: Sample the color inside your marking
            roi_hsv = hsv[int(my):int(my+mh), int(mx):int(mx+mw)]
            avg_h = np.median(roi_hsv[:,:,0])
            
            # Create mask based on LEARNED color
            lower_green = np.array([avg_h - 10, 40, 20])
            upper_green = np.array([avg_h + 10, 255, 120])
            mask = cv2.inRange(hsv, lower_green, upper_green)

            # Process Grid
            DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
            HOURS = ["7-8", "8-9", "9-10", "10-11", "11-12", "12-1", "1-2", "2-3", "3-4", "4-5", "5-6", "6-7"]
            results = []

            for c in range(1, 7): # Skip Time col
                for r in range(1, 13): # Skip Header row
                    x1, y1 = int(c * col_w), int(r * row_h)
                    x2, y2 = int((c+1) * col_w), int((r+1) * row_h)
                    
                    cell_mask = mask[y1:y2, x1:x2]
                    if np.sum(cell_mask == 255) / cell_mask.size > 0.3:
                        # OCR
                        cell_roi = img[y1:y2, x1:x2]
                        cell_roi = cv2.resize(cell_roi, None, fx=2, fy=2)
                        gray = cv2.cvtColor(cell_roi, cv2.COLOR_BGR2GRAY)
                        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
                        
                        text = pytesseract.image_to_string(thresh, config='--psm 6').strip()
                        
                        # Diagonal check (is the corner empty?)
                        is_diag = np.mean(cell_mask[:10, -10:]) < 100

                        if text:
                            lines = text.split('\n')
                            results.append({
                                "Day": DAYS[c-1],
                                "Time": HOURS[r-1],
                                "Class": lines[0] if len(lines) > 0 else "N/A",
                                "Type": "30-min Shift" if is_diag else "Full Hour"
                            })

            if results:
                st.dataframe(pd.DataFrame(results))
                st.download_button("Download CSV", pd.DataFrame(results).to_csv().encode('utf-8'))
