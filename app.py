import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="AMIS HD Schedule", layout="wide")

st.title("🖼️ AMIS CSV to HD Schedule")
st.write("Converts your UPLB AMIS CSV into a clean, professional PNG schedule.")

# Mapping for the shorthand days in your CSV
DAY_MAP = {
    'M': 'Monday',
    'T': 'Tuesday',
    'W': 'Wednesday',
    'TH': 'Thursday',
    'F': 'Friday',
    'S': 'Saturday'
}

# --- STEP 1: UPLOAD CSV ---
uploaded_file = st.file_uploader("Upload your 2S2425-SCHED.csv", type="csv")

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file)
        
        # Grid Setup
        days_full = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        header_labels = ["Time"] + days_full
        hours_labels = ["7-8", "8-9", "9-10", "10-11", "11-12", "12-1", "1-2", "2-3", "3-4", "4-5", "5-6", "6-7"]
        
        # Initialize Matrix (12 rows for hours x 7 columns for Time + Days)
        matrix = [["" for _ in range(7)] for _ in range(12)]
        
        # Fill Time labels
        for i, label in enumerate(hours_labels):
            matrix[i][0] = f"<b>{label}</b>"

        # --- STEP 2: DATA PROCESSING ---
        for _, row in df.iterrows():
            day_key = str(row['Day']).strip()
            day_name = DAY_MAP.get(day_key)
            
            if day_name and day_name in days_full:
                d_idx = days_full.index(day_name) + 1 # +1 because col 0 is Time
                
                # Parse Start and End Times
                # Examples from your file: "10:00 AM", "05:30PM", "11:30 "
                def parse_t(t_str):
                    t_str = t_str.strip()
                    # Add AM/PM if missing (heuristics for UPLB schedule)
                    if "AM" not in t_str and "PM" not in t_str:
                        h = int(t_str.split(':')[0])
                        t_str += " AM" if (7 <= h <= 11) else " PM"
                    return datetime.strptime(t_str, "%I:%M %p")

                try:
                    start_dt = parse_t(row['Start Time'])
                    end_dt = parse_t(row['End Time'])
                    
                    # Calculate which hour rows this class spans
                    # Start row: 7AM is index 0, 8AM is index 1, etc.
                    # AMIS hours 1, 2, 3... PM are 13, 14, 15...
                    def get_row_idx(dt):
                        h = dt.hour
                        if 7 <= h <= 12: return h - 7
                        if 1 <= h <= 6: return h + 5 # 1PM is index 6
                        return -1

                    start_row = get_row_idx(start_dt)
                    # End row calculation (e.g., 11:30 ends in the 11-12 slot)
                    # If it ends exactly at :00, we don't include the next slot
                    end_row = get_row_idx(end_dt)
                    if end_dt.minute == 0:
                        end_row -= 1

                    # Fill all slots the class occupies
                    for r_idx in range(start_row, end_row + 1):
                        if 0 <= r_idx < 12:
                            # Content formatting
                            time_range = f"{start_dt.strftime('%-I:%M')}-{end_dt.strftime('%-I:%M')}"
                            content = f"<b>{row['Class']}</b><br>{row['Location']}<br><span style='font-size:10px;'>{time_range}</span>"
                            
                            # Add to matrix (handle overlaps)
                            if matrix[r_idx][d_idx] == "":
                                matrix[r_idx][d_idx] = content
                            elif row['Class'] not in matrix[r_idx][d_idx]:
                                matrix[r_idx][d_idx] += f"<hr style='margin:2px;'>{content}"
                except Exception as e:
                    continue

        # --- STEP 3: RENDER HD TABLE ---
        fig = go.Figure(data=[go.Table(
            columnorder = [0,1,2,3,4,5,6],
            columnwidth = [70, 140, 140, 140, 140, 140, 140],
            header=dict(
                values=[f"<b>{h}</b>" for h in header_labels],
                fill_color='#1B5E20',
                align='center',
                font=dict(color='white', size=15),
                height=40
            ),
            cells=dict(
                values=list(zip(*matrix)),
                fill_color=[['#f8f9fa', '#e8f5e9']*6],
                align='center',
                font=dict(color='#212121', size=11),
                height=85 # Increased height to fit lab class details
            )
        )])

        fig.update_layout(width=1100, height=1100, margin=dict(l=10, r=10, t=10, b=10))

        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': True})
        st.success("✅ Schedule Layout Generated!")
        st.info("📸 **To Save:** Hover over the table and click the **Camera Icon** in the top right.")

    except Exception as e:
        st.error(f"Error: {e}")
