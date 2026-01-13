import streamlit as st
import cv2
import numpy as np
import pytesseract
import pandas as pd
from PIL import Image

# Setup
st.set_page_config(page_title="Adaptive Schedule Learner", layout="wide")

# Constants
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
HOURS = ["7-8", "8-9", "9-10", "10-11", "11-12", "12-1", "1-2", "2-3", "3-4", "4-5", "5-6", "6-7"]

st.sidebar.header("🧠 Calibration & Learning")
st.sidebar.info("Adjust these if the green boxes don't align with your classes.")

# Learning Sliders (These replace manual 'code changes')
top_pad = st.sidebar.slider("Header Height Offset", 0.0, 0.2, 0.08)
left_pad = st.sidebar.slider("Time Column Width Offset", 0.0, 0.2, 0.14)
sensitivity = st.sidebar.slider("Color Sensitivity", 10, 100, 40)
min_area = st.sidebar.slider("Min Class Size", 0.05, 0.5, 0.25)

st.title("📅 Class Schedule Parser")
uploaded_file = st.file_uploader("Upload your schedule (e.g., my_schedule.png)", type=["png", "jpg", "jpeg"])

if uploaded_file:
    # 1. Load and prepare images
    file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    h_img, w_img, _ = img.shape
    img_display = cv2.cvtColor(img.copy(), cv2.COLOR_BGR2RGB)
    
    # 2. Color Detection (Learning from the sensitivity slider)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lower_green = np.array([sensitivity, 40, 20])
    upper_green = np.array([85, 255, 120])
    mask = cv2.inRange(hsv, lower_green, upper_green)

    # 3. Grid-Based Cell Extraction
    # We divide the image into 7 columns and 13 rows based on offsets
    col_w = (w_img * (1 - left_pad)) / 6
    row_h = (h_img * (1 - top_pad)) / 12
    
    extracted_data = []

    for c in range(6): # Days
        for r in range(12): # Hours
            # Define exact coordinates for this cell
            x1 = int((w_img * left_pad) + (c * col_w))
            y1 = int((h_img * top_pad) + (r * row_h))
            x2 = int(x1 + col_w)
            y2 = int(y1 + row_h)

            cell_mask = mask[y1:y2, x1:x2]
            
            # If the cell is significantly green (min_area), process it
            if np.sum(cell_mask == 255) / cell_mask.size > min_area:
                # OCR Pre-processing
                roi = img[y1:y2, x1:x2]
                roi = cv2.resize(roi, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
                gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                # Invert colors for white text on dark background
                thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
                
                text = pytesseract.image_to_string(thresh, config='--psm 6').strip()
                
                # Diagonal Detection: Check top-right corner of the cell
                is_diagonal = np.mean(cell_mask[:10, -10:]) < 127
                
                if text:
                    lines = [line.strip() for line in text.split('\n') if len(line.strip()) > 1]
                    extracted_data.append({
                        "Day": DAYS[c],
                        "Time": HOURS[r],
                        "Class": lines[0] if len(lines) > 0 else "N/A",
                        "Location": lines[1] if len(lines) > 1 else "N/A",
                        "Shift": "30-min" if is_diagonal else "Regular"
                    })
                    
                    # Highlight cell on display
                    cv2.rectangle(img_display, (x1, y1), (x2, y2), (0, 255, 0), 2)

    # Output Display
    if extracted_data:
        df = pd.DataFrame(extracted_data)
        st.subheader("Extracted Schedule Table")
        st.dataframe(df, use_container_width=True)
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Schedule CSV", csv, "schedule.csv", "text/csv")
    else:
        st.error("No classes detected. Adjust the 'Color Sensitivity' or 'Offsets' in the sidebar.")

    st.image(img_display, caption="Detection Result (Green boxes = Scanned Grid Cells)")
