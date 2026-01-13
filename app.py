import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="AMIS Schedule Plotter", layout="wide")

st.title("📅 AMIS Class Schedule Plotter")
st.write("Generating a high-definition schedule from your uploaded AMIS CSV file.")

# Shorthand mapping based on your CSV content
DAY_MAP = {
    'M': 'Monday',
    'T': 'Tuesday',
    'W': 'Wednesday',
    'TH': 'Thursday',
    'F': 'Friday',
    'S': 'Saturday'
}

# --- STEP 1: LOAD DATA ---
# Using your specific file structure
uploaded_file = st.file_uploader("Upload 2S2425-SCHED.csv", type="csv")

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file)
        df.columns = [c.strip() for c in df.columns]

        # Define Grid Structure
        days_full = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        header_labels = ["Time"] + days_full
        # Standard UPLB Time Slots
        hours_labels = ["7-8", "8-9", "9-10", "10-11", "11-12", "12-1", "1-2", "2-3", "3-4", "4-5", "5-6", "6-7"]
        
        # Initialize Matrix (12 rows x 7 columns)
        matrix = [["" for _ in range(7)] for _ in range(12)]
        
        # Fill Time labels in Column 0
        for i, label in enumerate(hours_labels):
            matrix[i][0] = f"<b>{label}</b>"

        # --- STEP 2: PLOT ALL CLASSES ---
        for _, row in df.iterrows():
            day_key = str(row['Day']).strip()
            day_name = DAY_MAP.get(day_key)
            
            if day_name and day_name in days_full:
                d_idx = days_full.index(day_name) + 1 # Column index

                # Helper to parse times like "10:00 AM" or "05:30PM"
                def parse_t(t_str):
                    t_str = t_str.strip().upper()
                    if ":" not in t_str: return None
                    
                    # Heuristic for AM/PM if missing in your CSV strings
                    if "AM" not in t_str and "PM" not in t_str:
                        h = int(t_str.split(':')[0])
                        t_str += " AM" if (7 <= h <= 11) else " PM"
                    
                    # Handle cases like "05:30PM" (no space)
                    if "AM" in t_str and " AM" not in t_str: t_str = t_str.replace("AM", " AM")
                    if "PM" in t_str and " PM" not in t_str: t_str = t_str.replace("PM", " PM")
                    
                    return datetime.strptime(t_str, "%I:%M %p")

                try:
                    start_dt = parse_t(row['Start Time'])
                    end_dt = parse_t(row['End Time'])
                    
                    if not start_dt or not end_dt: continue

                    # Map to row indices (7 AM = row 0, 1 PM = row 6)
                    def get_row_idx(dt):
                        h = dt.hour
                        if 7 <= h <= 12: return h - 7
                        if 1 <= h <= 6: return h + 5 
                        return -1

                    s_row = get_row_idx(start_dt)
                    e_row = get_row_idx(end_dt)
                    # If it ends exactly at :00, don't color the next slot
                    if end_dt.minute == 0: e_row -= 1

                    # Plot the class across all relevant time rows
                    for r_idx in range(s_row, e_row + 1):
                        if 0 <= r_idx < 12:
                            time_info = f"{start_dt.strftime('%-I:%M')}-{end_dt.strftime('%-I:%M')}"
                            cell_text = f"<b>{row['Class']}</b><br>{row['Location']}<br><small>{time_info}</small>"
                            
                            if matrix[r_idx][d_idx] == "":
                                matrix[r_idx][d_idx] = cell_text
                            elif row['Class'] not in matrix[r_idx][d_idx]:
                                # If two classes share an hour, stack them
                                matrix[r_idx][d_idx] += f"<hr style='margin:2px;'>{cell_text}"
                except:
                    continue

        # --- STEP 3: RENDER HD PLOT ---
        fig = go.Figure(data=[go.Table(
            columnwidth = [70, 140, 140, 140, 140, 140, 140],
            header=dict(
                values=[f"<b>{h}</b>" for h in header_labels],
                fill_color='#1B5E20', # UPLB Green
                align='center',
                font=dict(color='white', size=15),
                height=40
            ),
            cells=dict(
                values=list(zip(*matrix)),
                fill_color=[['#ffffff', '#f1f8e9']*6], # Zebra rows
                align='center',
                font=dict(color='#212121', size=11),
                height=90 # Tall cells for multiple classes/labs
            )
        )])

        fig.update_layout(width=1100, height=1200, margin=dict(l=10, r=10, t=10, b=10))

        st.plotly_chart(fig, use_container_width=True)
        st.success("✅ All classes from 2S2425-SCHED.csv have been plotted.")
        st.info("📸 **Save Image:** Hover over the chart and click the **Camera Icon**.")

    except Exception as e:
        st.error(f"Critical Error: {e}")
