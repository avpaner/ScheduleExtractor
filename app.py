import streamlit as st
import cv2
import numpy as np
import pytesseract
import pandas as pd
from PIL import Image

st.set_page_config(page_title="AMIS Schedule Extractor", layout="wide")

st.title("📅 AMIS Schedule to CSV")
st.write("Extracts classes based on your 7-column grid and handles diagonal shifts.")

# Constants based on the AMIS Grid
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
HOURS = [
    ("7:00", "8:00"), ("8:00", "9:00"), ("9:00", "10:00"), 
    ("10:00", "11:00"), ("11:00", "12:00"), ("12:00", "1:00"), 
    ("1:00", "2:00"), ("2:00", "3:00"), ("3:00", "4:00"), 
    ("4:00", "5:00"), ("5:00", "6:00"), ("6:00", "7:00")
]

uploaded_file = st.file_uploader("Upload your schedule image", type=["png", "jpg", "jpeg"])

if uploaded_file:
    # Load Image
    file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    h_img, w_img, _ = img.shape
    img_display = cv2.cvtColor(img.copy(), cv2.COLOR_BGR2RGB)
    
    # 1. Color Masking for Dark Green Boxes
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lower_green = np.array([35, 40, 20])
    upper_green = np.array([85, 255, 120])
    mask = cv2.inRange(hsv, lower_green, upper_green)

    # 2. Grid Scanning (Using the 7-col / 13-row logic learned from marks)
    col_w = w_img / 7
    row_h = h_img / 13
    
    schedule_list = []

    for c in range(1, 7):  # Columns 1-6 (Mon-Sat)
        for r in range(1, 13):  # Rows 1-12 (Time slots)
            x1, y1 = int(c * col_w), int(r * row_h)
            x2, y2 = int((c + 1) * col_w), int((r + 1) * row_h)
            
            cell_mask = mask[y1:y2, x1:x2]
            # Check if cell is occupied by a class (learned threshold)
            if np.sum(cell_mask == 255) / cell_mask.size > 0.2:
                
                # --- OCR Processing ---
                roi = img[y1:y2, x1:x2]
                roi = cv2.resize(roi, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
                gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                # Invert for white text on green background
                thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
                
                raw_text = pytesseract.image_to_string(thresh, config='--psm 6').strip()
                
                if raw_text:
                    lines = [l.strip() for l in raw_text.split('\n') if len(l.strip()) > 1]
                    
                    # --- Time Logic for Diagonal Shifts ---
                    # Check top-right corner to see if class starts at :30
                    is_start_shifted = np.mean(cell_mask[:15, -15:]) < 127
                    # Check bottom-left corner to see if class ends at :30
                    is_end_shifted = np.mean(cell_mask[-15:, :15]) < 127
                    
                    start_time, end_time = HOURS[r-1]
                    
                    if is_start_shifted:
                        start_time = start_time.replace(":00", ":30")
                    if is_end_shifted:
                        end_time = end_time.replace(":00", ":30")

                    schedule_list.append({
                        "Day": DAYS[c-1],
                        "Start Time": start_time,
                        "End Time": end_time,
                        "Class": lines[0] if len(lines) > 0 else "N/A",
                        "Location": lines[1] if len(lines) > 1 else "TBA"
                    })
                    
                    # Highlight for preview
                    cv2.rectangle(img_display, (x1, y1), (x2, y2), (0, 255, 0), 2)

    # --- Result Display ---
    if schedule_list:
        df = pd.DataFrame(schedule_list)
        # Reorder to match your CSV format image exactly
        df = df[["Day", "Start Time", "End Time", "Class", "Location"]]
        
        st.subheader("Extracted Schedule")
        st.dataframe(df, use_container_width=True)
        
        # Download Button
        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download CSV", csv_data, "my_schedule.csv", "text/csv")
    else:
        st.error("No classes detected. Make sure the grid is visible and green.")
    
    st.image(img_display, caption="Detection Preview")
