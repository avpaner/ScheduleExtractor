import streamlit as st
import cv2
import numpy as np
import pytesseract
import pandas as pd
from PIL import Image

st.set_page_config(page_title="Ultra-Accurate Schedule Parser", layout="wide")

st.title("📅 Precision Grid-Based Schedule Parser")
st.write("This version uses a fixed grid-masking technique to prevent 'big box' merging.")

# Define Schedule Structure
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
HOURS = ["7-8", "8-9", "9-10", "10-11", "11-12", "12-1", "1-2", "2-3", "3-4", "4-5", "5-6", "6-7"]

uploaded_file = st.file_uploader("Upload your schedule image", type=["png", "jpg", "jpeg"])

if uploaded_file:
    # 1. Load Image
    file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    h_img, w_img, _ = img.shape
    img_display = cv2.cvtColor(img.copy(), cv2.COLOR_BGR2RGB)
    
    # 2. Identify the 'Class Green' Color
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lower_green = np.array([35, 40, 20])
    upper_green = np.array([85, 255, 120])
    mask = cv2.inRange(hsv, lower_green, upper_green)

    # 3. Grid-Based Scanning (7 Columns x 13 Rows)
    col_w = w_img / 7
    row_h = h_img / 13
    
    extracted_data = []

    # Loop through each Column (Starting from index 1 to skip 'Time' column)
    for c in range(1, 7):
        # Loop through each Row (Starting from index 1 to skip 'Day' headers)
        for r in range(1, 13):
            # Define the exact coordinates for this specific cell
            x1, y1 = int(c * col_w), int(r * row_h)
            x2, y2 = int((c + 1) * col_w), int((r + 1) * row_h)
            
            # Crop the mask for this cell to check for presence of a class
            cell_mask = mask[y1:y2, x1:x2]
            green_pixel_ratio = np.sum(cell_mask == 255) / cell_mask.size
            
            # If the cell is mostly green, we have a class!
            if green_pixel_ratio > 0.25:
                # OCR on the specific cell
                roi = img[y1:y2, x1:x2]
                roi = cv2.resize(roi, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
                gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
                
                text = pytesseract.image_to_string(thresh, config='--psm 6').strip()
                
                # Diagonal Detection (Check corner pixels of the cell)
                # If the top-right or bottom-left corner of the cell mask is empty, it's a diagonal
                corner_sample = 10
                is_diagonal = np.mean(cell_mask[:corner_sample, -corner_sample:]) < 127
                
                if text:
                    lines = [line.strip() for line in text.split('\n') if len(line.strip()) > 1]
                    extracted_data.append({
                        "Day": DAYS[c-1],
                        "Time": HOURS[r-1],
                        "Class": lines[0] if len(lines) > 0 else "N/A",
                        "Location": lines[1] if len(lines) > 1 else "N/A",
                        "Shift": "30-min" if is_diagonal else "Regular"
                    })
                    
                    # Visual feedback: Draw individual cell box
                    cv2.rectangle(img_display, (x1, y1), (x2, y2), (0, 255, 0), 2)

    # 4. Result Presentation
    if extracted_data:
        df = pd.DataFrame(extracted_data)
        # Sort by day order
        day_map = {day: i for i, day in enumerate(DAYS)}
        df['day_sort'] = df['Day'].map(day_map)
        df = df.sort_values(by=['day_sort', 'Time']).drop(columns=['day_sort'])
        
        st.subheader("Extracted Schedule")
        st.dataframe(df, use_container_width=True)
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download CSV", csv, "schedule.csv", "text/csv")
    else:
        st.error("Could not find any class blocks. Ensure the image grid is aligned.")

    st.image(img_display, caption="Grid-Based Detection (Green boxes show scanned cells)")
