import streamlit as st
import json
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import re

# Page Config
st.set_page_config(page_title="AMIS JSON Schedule Plotter", layout="wide")

st.title("📅 AMIS JSON to HD Schedule")
st.write("Upload your `2S2425-SCHED.json` to generate a high-definition, printable schedule.")

# Mapping for AMIS shorthands
DAY_MAP = {
    'M': 'Monday', 
    'T': 'Tuesday', 
    'W': 'Wednesday', 
    'TH': 'Thursday', 
    'F': 'Friday', 
    'S': 'Saturday'
}

def robust_time_parse(t_str, reference_dt=None):
    """
    Parses '10:00 AM', '05:30PM', or '11:30 ' (inferring AM/PM).
    """
    if not t_str or not isinstance(t_str, str): 
        return None
    
    # 1. Clean string
    t_str = t_str.strip().upper()
    t_str = re.sub(r'([AP]M)', r' \1', t_str).strip() # Ensure space: 05:30PM -> 05:30 PM
    
    # 2. Try Standard Parse (%I:%M %p)
    try:
        return datetime.strptime(t_str, "%I:%M %p")
    except ValueError:
        pass

    # 3. Try Fallback Parse (No AM/PM)
    try:
        dt = datetime.strptime(t_str, "%H:%M")
        # Heuristic: If hour is 1-6, it's PM. If 7-11, it's AM. 12 is PM.
        if 1 <= dt.hour <= 6:
            return dt.replace(hour=dt.hour + 12)
        elif dt.hour == 12:
            return dt
        # If still unsure and we have a start time, use start time's meridian
        if reference_dt and dt.hour < reference_dt.hour:
            return dt.replace(hour=dt.hour + 12)
        return dt
    except:
        return None

def get_row_index(dt):
    """Maps time to 1-hour rows: 7AM=0, 8AM=1 ... 12PM=5, 1PM=6 ... 6PM=11."""
    if not dt: return -1
    h = dt.hour
    if 7 <= h <= 12: 
        return h - 7
    if 1 <= h <= 7: # Afternoon/Early Evening
        return h + 5
    return -1

# --- FILE UPLOAD ---
uploaded_file = st.file_uploader("Upload your schedule JSON", type="json")

if uploaded_file:
    try:
        data = json.load(uploaded_file)
        
        # Grid Setup
        days_list = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        header = ["Time"] + days_list
        hours_labels = ["7-8", "8-9", "9-10", "10-11", "11-12", "12-1", "1-2", "2-3", "3-4", "4-5", "5-6", "6-7"]
        
        # 12 rows for time slots, 7 columns (Time + 6 Days)
        matrix = [["" for _ in range(7)] for _ in range(12)]
        for i, lbl in enumerate(hours_labels):
            matrix[i][0] = f"<b>{lbl}</b>"

        # --- PROCESS JSON DATA ---
        for item in data:
            # Map Day
            day_key = str(item.get('day', '')).strip()
            day_name = DAY_MAP.get(day_key)
            
            if day_name in days_list:
                col_idx = days_list.index(day_name) + 1
                
                # Parse Times
                start_dt = robust_time_parse(item.get('startTime'))
                end_dt = robust_time_parse(item.get('endTime'), reference_dt=start_dt)
                
                if start_dt and end_dt:
                    s_row = get_row_index(start_dt)
                    e_row = get_row_index(end_dt)
                    
                    # If end time is exactly on the hour (e.g., 09:00), 
                    # don't occupy the 9-10 slot.
                    if end_dt.minute == 0: 
                        e_row -= 1

                    # Fill the matrix for every hour spanned
                    if s_row != -1:
                        e_row = min(e_row, 11) # Cap at 7 PM
                        for r_idx in range(s_row, e_row + 1):
                            if 0 <= r_idx < 12:
                                time_range = f"{start_dt.strftime('%I:%M')}-{end_dt.strftime('%I:%M')}"
                                cell_text = f"<b>{item.get('subject')}</b><br><small>{item.get('room')}<br>{time_range}</small>"
                                
                                # If cell is empty, add; otherwise append (for overlapping slots)
                                if matrix[r_idx][col_idx] == "":
                                    matrix[r_idx][col_idx] = cell_text
                                elif item.get('subject') not in matrix[r_idx][col_idx]:
                                    matrix[r_idx][col_idx] += f"<hr style='margin:2px;'>{cell_text}"

        # --- CREATE VISUAL TABLE ---
        fig = go.Figure(data=[go.Table(
            columnwidth = [70, 150, 150, 150, 150, 150, 150],
            header=dict(
                values=[f"<b>{h}</b>" for h in header],
                fill_color='#1B5E20', # UPLB Green
                font=dict(color='white', size=15),
                height=45,
                align='center',
                line_color='white'
            ),
            cells=dict(
                values=list(zip(*matrix)),
                fill_color=[['#ffffff', '#f1f8e9']*6], # Zebra striping
                align='center',
                font=dict(color='#212121', size=11),
                height=100,
                line_color='#e0e0e0'
            )
        )])

        fig.update_layout(
            width=1200, 
            height=1300, 
            margin=dict(l=10, r=10, t=10, b=10)
        )

        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': True})
        
        st.success(f"Successfully plotted all classes from JSON.")
        st.info("💡 **Tip:** To save as PNG, hover over the schedule and click the **Camera Icon** 📸.")

    except Exception as e:
        st.error(f"Error loading JSON: {e}")
        st.info("Ensure your JSON uses keys: 'day', 'startTime', 'endTime', 'subject', 'room'")
