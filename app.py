import streamlit as st
import cv2
import numpy as np
import pytesseract
import pandas as pd
from PIL import Image

st.set_page_config(page_title="Schedule Parser Pro", layout="wide")

st.title("📅 Precision Schedule Extractor")
st.write("This tool separates individual class blocks from the grid and detects 30-minute shifts.")

# Constants for Mapping
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
HOURS = ["7-8", "8-9", "9-10", "10-11", "11-12", "12-1", "1-2", "2-3", "3-4", "4-5", "5-6", "6-7"]

uploaded_file = st.file_uploader("Upload Schedule Image", type=["png", "jpg", "jpeg"])

if uploaded_file:
    # Load and Pre-process Image
    file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    h_img, w_img, _ = img.shape
    img_display = cv2.cvtColor(img.copy(), cv2.COLOR_BGR2RGB)
    
    # 1. Color Masking (Dark Green blocks)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    # Range adjusted for the dark green blocks in your schedule
    lower_green = np.array([35, 40, 20])
    upper_green = np.array([85, 255, 120])
    mask = cv2.inRange(hsv, lower_green, upper_green)

    # 2. BREAK THE GRID: Morphological Operations
    # Shrink the green blocks slightly to disconnect them from the grid lines
    kernel = np.ones((5,5), np.uint8)
    eroded_mask = cv2.erode(mask, kernel, iterations=1)
    
    # 3. Find Contours
    contours, _ = cv2.findContours(eroded_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    extracted_data = []

    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        
        # Filter: Only process shapes that look like class blocks (not noise, not the whole grid)
        if 40 < w < (w_img * 0.4) and 20 < h < (h_img * 0.4):
            
            # --- Grid Mapping Logic ---
            col_width = w_img / 7
            day_idx = int((x + w/2) / col_width) - 1
            
            row_height = h_img / 13 # Header + 12 Slots
            hour_idx = int((y + h/2) / row_height) - 1
            
            if 0 <= day_idx < len(DAYS) and 0 <= hour_idx < len(HOURS):
                day = DAYS[day_idx]
                time_slot = HOURS[hour_idx]
                
                # Solidity Check for 30-min Diagonal Shift
                # Perfect rectangle = 1.0. Diagonal cut ≈ 0.80
                actual_area = cv2.contourArea(cnt)
                solidity = actual_area / (w * h)
                # Check variable: using 'shift_detected' for clarity
                shift_detected = solidity < 0.90
                
                # OCR Extraction
                roi = img[y:y+h, x:x+w]
                if roi.size > 0:
                    roi = cv2.resize(roi, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
                    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                    # Use OTSU thresholding to handle lighting variations
                    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
                    
                    text = pytesseract.image_to_string(thresh, config='--psm 6').strip()
                    
                    if text:
                        lines = [line.strip() for line in text.split('\n') if len(line.strip()) > 1]
                        extracted_data.append({
                            "Day": day,
                            "Time": time_slot,
                            "Class": lines[0] if len(lines) > 0 else "N/A",
                            "Location": lines[1] if len(lines) > 1 else "N/A",
                            "30m_Shift": "Yes" if shift_detected else "No"
                        })
                        
                        # Visual feedback on the image
                        rect_color = (255, 0, 0) if shift_detected else (0, 255, 0)
                        cv2.rectangle(img_display, (x, y), (x+w, y+h), rect_color, 3)

    # UI Presentation
    if extracted_data:
        df = pd.DataFrame(extracted_data)
        # Sort by day order so Monday is first
        day_map = {day: i for i, day in enumerate(DAYS)}
        df['day_sort'] = df['Day'].map(day_map)
        df = df.sort_values(by=['day_sort', 'Time']).drop(columns=['day_sort'])
        
        st.subheader("Extracted Schedule Table")
        st.dataframe(df, use_container_width=True)
        
        # Download Button
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download as CSV", csv, "schedule.csv", "text/csv")
    else:
        st.warning("No classes detected. Check if the image is clear or if the green color is different.")
    
    st.image(img_display, caption="Detection Result (Green = Hourly, Blue = 30-min Shift)")
