import streamlit as st
import pandas as pd
import json
import plotly.graph_objects as go
from datetime import datetime
import re

# --- CONFIG ---
st.set_page_config(page_title="AMIS HD Plotter", layout="wide")

st.title("🎓 AMIS HD Schedule Plotter")
st.write("Upload your CSV or JSON to generate a professional, high-definition schedule grid.")

# Day mapping for AMIS shorthand
DAY_MAP = {
    'M': 'Monday', 'T': 'Tuesday', 'W': 'Wednesday', 
    'TH': 'Thursday', 'F': 'Friday', 'S': 'Saturday'
}

# --- ROBUST TIME LOGIC ---
def robust_time_parse(t_str):
    """
    Handles '10:00 AM', '05:30PM', or '11:30' (missing AM/PM).
    """
    if not t_str or pd.isna(t_str):
        return None
    
    t_str = str(t_str).strip().upper()
    
    # 1. Clean format: Ensure space before AM/PM (e.g., 05:30PM -> 05:30 PM)
    t_str = re.sub(r'([AP]M)', r' \1', t_str).strip()
    
    # 2. Try parsing with AM/PM
    try:
        return datetime.strptime(t_str, "%I:%M %p")
    except ValueError:
        pass

    # 3. Fallback for missing AM/PM (e.g., 1:00 or 5:30)
    try:
        dt = datetime.strptime(t_str, "%H:%M")
        # UPLB Heuristic: 1-6 is almost always PM, 7-11 is AM
        if 1 <= dt.hour <= 6:
            return dt.replace(hour=dt.hour + 12)
        return dt
    except:
        return None

def get_row_index(dt):
    """
    Maps a datetime object to the correct row index (0-11).
    7 AM = Row 0, 12 PM = Row 5, 1 PM = Row 6, 6 PM = Row 11.
    """
    if not dt: return -1
    h = dt.hour
    if 7 <= h <= 12: 
        return h - 7
    if 13 <= h <= 19: # 1 PM to 7 PM
        return h - 7
    return -1

# --- FILE LOADING ---
uploaded_file = st.file_uploader("Upload your schedule file", type=["csv", "json"])

if uploaded_file:
    try:
        raw_data = []
        # Support for both your CSV and JSON formats
        if uploaded_file.name.endswith('.json'):
            data = json.load(uploaded_file)
            for item in data:
                raw_data.append({
                    'day': item.get('day'),
                    'start': item.get('startTime'),
                    'end': item.get('endTime'),
                    'subject': item.get('subject'),
                    'room': item.get('room')
                })
        else:
            df = pd.read_csv(uploaded_file)
            for _, row in df.iterrows():
                raw_data.append({
                    'day': row.get('Day'),
                    'start': row.get('Start Time'),
                    'end': row.get('End Time'),
                    'subject': row.get('Class'),
                    'room': row.get('Location')
                })

        # --- GRID INITIALIZATION ---
        days_list = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        header = ["Time"] + days_list
        hours_labels = ["7:00", "8:00", "9:00", "10:00", "11:00", "12:00", 
                        "1:00", "2:00", "3:00", "4:00", "5:00", "6:00"]
        
        # 12 hours x 7 columns
        matrix = [["" for _ in range(7)] for _ in range(12)]
        for i, lbl in enumerate(hours_labels):
            matrix[i][0] = f"<b>{lbl}</b>"

        # --- PLOTTING LOGIC ---
        for entry in raw_data:
            day_name = DAY_MAP.get(str(entry['day']).strip())
            if day_name in days_list:
                col_idx = days_list.index(day_name) + 1
                
                start_dt = robust_time_parse(entry['start'])
                end_dt = robust_time_parse(entry['end'])
                
                if start_dt and end_dt:
                    s_row = get_row_index(start_dt)
                    e_row = get_row_index(end_dt)
                    
                    # Prevent overflow if class ends exactly on the hour
                    if end_dt.minute == 0:
                        e_row -= 1

                    # Fill all slots the class spans (e.g., 3-hour labs)
                    if s_row != -1:
                        e_row = min(e_row, 11)
                        for r_idx in range(s_row, e_row + 1):
                            if 0 <= r_idx < 12:
                                t_range = f"{start_dt.strftime('%I:%M')}-{end_dt.strftime('%I:%M')}"
                                cell_text = f"<b>{entry['subject']}</b><br><small>{entry['room']}<br>{t_range}</small>"
                                
                                # Handle overlapping classes in the same slot
                                if matrix[r_idx][col_idx] == "":
                                    matrix[r_idx][col_idx] = cell_text
                                elif entry['subject'] not in matrix[r_idx][col_idx]:
                                    matrix[r_idx][col_idx] += f"<hr style='margin:2px;'>{cell_text}"

        # --- RENDER TABLE ---
        fig = go.Figure(data=[go.Table(
            columnwidth = [60, 140, 140, 140, 140, 140, 140],
            header=dict(
                values=[f"<b>{h}</b>" for h in header],
                fill_color='#1B5E20', # UPLB Green
                font=dict(color='white', size=14),
                height=45, align='center'
            ),
            cells=dict(
                values=list(zip(*matrix)),
                fill_color=[['#ffffff', '#f1f8e9']*6],
                align='center', 
                font=dict(color='#212121', size=11),
                height=100
            )
        )])

        fig.update_layout(width=1100, height=1300, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': True})
        st.success("✅ Schedule successfully generated!")
        st.info("💡 **To Save:** Hover over the table and click the **Camera Icon** 📸 (Download plot as a png).")

    except Exception as e:
        st.error(f"Error processing file: {e}")
