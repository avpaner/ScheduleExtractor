import streamlit as st
import cv2
import numpy as np
import pytesseract
import pandas as pd
from PIL import Image

st.set_page_config(page_title="Schedule Parser Pro", layout="wide")

st.title("📅 Day-by-Day Schedule Extractor")
st.write("Detecting classes based on 7-column grid layout.")

# Define our structure
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
HOURS = ["7-8", "8-9", "9-10", "10-11", "11-12", "12-1", "1-2", "2-3", "3-4", "4-5", "5-6", "6-7"]

uploaded_file = st.file_uploader("Upload Schedule Image", type=["png", "jpg", "jpeg"])

if uploaded_file:
    file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    h_img, w_img, _ = img.shape
    img_display = cv2.cvtColor(img.copy(), cv2.COLOR_BGR2RGB)
    
    # Isolate green class blocks
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array([35, 40, 20]), np.array([85, 255, 120]))
    
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    extracted_data = []

    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        
        if w > 40 and h > 20:
            # --- GRID LOGIC ---
            # 1. Calculate Day: Divide width by 7 columns
            col_width = w_img / 7
            day_idx = int((x + w/2) / col_width) - 1 # -1 because column 0 is 'Time'
            
            # 2. Calculate Time: Divide height by 13 (Header + 12 rows)
            row_height = h_img / 13
            hour_idx = int((y + h/2) / row_height) - 1
            
            # Validate indices
            if 0 <= day_idx < len(DAYS) and 0 <= hour_idx < len(HOURS):
                day = DAYS[day_idx]
                time_slot = HOURS[hour_idx]
                
                # Check for 30-min shift (Diagonal Solidity)
                solidity = cv2.contourArea(cnt) / (w * h)
                is_shifted = solidity < 0.88
                
                # OCR for Class Name and Location
                roi = img[y:y+h, x:x+w]
                # Improve OCR by enlarging and inverting for white-on-green text
                roi = cv2.resize(roi, None, fx=2, fy=2)
                gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                text = pytesseract.image_to_string(gray, config='--psm 6').strip()
                
                if text:
                    lines = [line.strip() for line in text.split('\n') if len(line.strip()) > 1]
                    extracted_data.append({
                        "Day": day,
                        "Time": time_slot,
                        "Class": lines[0] if len(lines) > 0 else "N/A",
                        "Location": lines[1] if len(lines) > 1 else "N/A",
                        "Is_30min": "Yes" if is_shifted else "No"
                    })
                    
                    # Draw visual feedback
                    cv2.rectangle(img_display, (x, y), (x+w, y+h), (0, 255, 0), 3)
                    cv2.putText(img_display, f"{day}", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

    # Display and Download
    if extracted_data:
        df = pd.DataFrame(extracted_data)
        
        # Sort by day and time for a readable schedule
        day_map = {day: i for i, day in enumerate(DAYS)}
        df['day_sort'] = df['Day'].map(day_map)
        df = df.sort_values(by=['day_sort', 'Time']).drop(columns=['day_sort'])
        
        st.subheader("Extracted Classes per Day")
        st.dataframe(df, use_container_width=True)
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Download Schedule CSV", csv, "extracted_schedule.csv", "text/csv")
    
    st.image(img_display, caption="Processed Image with Day Detection")
