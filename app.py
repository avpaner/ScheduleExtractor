import streamlit as st
import cv2
import numpy as np
import pytesseract
from PIL import Image

st.set_page_config(page_title="Schedule Parser Pro", layout="wide")

st.title("📅 Smart Schedule Extractor")
st.write("Automatically detects **Day**, **Time**, **Class**, and **30-minute shifts**.")

# Define the grid mapping based on your reference image
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
HOURS = ["7-8", "8-9", "9-10", "10-11", "11-12", "12-1", "1-2", "2-3", "3-4", "4-5", "5-6", "6-7"]

uploaded_file = st.file_uploader("Upload your schedule image", type=["png", "jpg", "jpeg"])

if uploaded_file:
    file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    h_img, w_img, _ = img.shape
    img_rgb = cv2.cvtColor(img.copy(), cv2.COLOR_BGR2RGB)
    
    # 1. Isolate the dark green blocks
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lower_green = np.array([35, 40, 20])
    upper_green = np.array([85, 255, 120])
    mask = cv2.inRange(hsv, lower_green, upper_green)
    
    # 2. Contour detection
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    extracted_data = []

    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        
        if w > 40 and h > 20:
            # Map X position to Day (Approximate columns)
            # Dividing image width by 7 (Time column + 6 Days)
            day_index = int((x / w_img) * 7) - 1 
            day = DAYS[day_index] if 0 <= day_index < len(DAYS) else "Unknown"
            
            # Map Y position to Hour (Approximate rows)
            # The top ~10% is usually the header
            hour_index = int(((y / h_img) - 0.08) * 12)
            time_slot = HOURS[hour_index] if 0 <= hour_index < len(HOURS) else "Unknown"

            # 30-minute shift check (Solidity)
            actual_area = cv2.contourArea(cnt)
            solidity = actual_area / (w * h)
            is_30_min = solidity < 0.90

            # OCR for Text
            roi = img[y:y+h, x:x+w]
            roi = cv2.resize(roi, None, fx=2, fy=2)
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            text = pytesseract.image_to_string(gray, config='--psm 6').strip()
            
            if text:
                lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 1]
                extracted_data.append({
                    "Day": day,
                    "Time": f"{time_slot} (Shifted)" if is_30_min else time_slot,
                    "Class": lines[0] if len(lines) > 0 else "N/A",
                    "Location": lines[1] if len(lines) > 1 else "N/A"
                })
                
                # Visual Feedback
                cv2.rectangle(img_rgb, (x, y), (x+w, y+h), (255, 0, 0) if is_30_min else (0, 255, 0), 2)

    # Sort data by Day then Time for a clean table
    day_order = {day: i for i, day in enumerate(DAYS)}
    extracted_data.sort(key=lambda x: (day_order.get(x['Day'], 99)))

    st.image(img_rgb, use_column_width=True)
    st.dataframe(extracted_data, use_container_width=True)

    # Download Button
    import pandas as pd
    df = pd.DataFrame(extracted_data)
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Schedule as CSV", csv, "my_schedule.csv", "text/csv")
