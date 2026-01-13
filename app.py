import streamlit as st
import cv2
import numpy as np
import pytesseract
from PIL import Image

# Page Configuration
st.set_page_config(page_title="Schedule OCR", page_icon="📅")
st.title("📅 Class Schedule Extractor")
st.write("Upload your green-grid schedule to detect classes and 30-minute shifts.")

# 1. File Uploader
uploaded_file = st.file_uploader("Choose a schedule image...", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    # Convert uploaded file to OpenCV format
    image = Image.open(uploaded_file)
    img_array = np.array(image)
    img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    
    st.image(image, caption="Uploaded Schedule", use_column_width=True)
    
    with st.spinner("Analyzing colors and diagonal lines..."):
        # 2. Color Masking (Targeting the Dark Green boxes)
        hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        lower_green = np.array([35, 40, 40])
        upper_green = np.array([85, 255, 150])
        mask = cv2.inRange(hsv, lower_green, upper_green)
        
        # 3. Finding Contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        results = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if w > 50 and h > 20: # Filter noise
                # Diagonal Detection (Area check)
                rect_area = w * h
                actual_area = cv2.contourArea(cnt)
                is_30_min = actual_area < (rect_area * 0.88)

                # OCR logic
                roi = img_bgr[y:y+h, x:x+w]
                roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                text = pytesseract.image_to_string(roi_gray, config='--psm 6').strip()
                
                if text:
                    lines = [line.strip() for line in text.split('\n') if line.strip()]
                    results.append({
                        "Class/Section": lines[0] if len(lines) > 0 else "Unknown",
                        "Location": lines[1] if len(lines) > 1 else "TBA",
                        "Type": "30-min Shift" if is_30_min else "Full Hour"
                    })

        # 4. Display Results
        if results:
            st.success(f"Found {len(results)} class blocks!")
            st.table(results)
        else:
            st.warning("No class blocks detected. Try adjusting the green color threshold.")