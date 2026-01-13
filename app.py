import streamlit as st
import pandas as pd
import json
import plotly.graph_objects as go
from datetime import datetime, timedelta
import re

st.set_page_config(page_title="AMIS 30-Min Schedule Plotter", layout="wide")

st.title("📅 AMIS 30-Minute HD Schedule")
st.write("Grid updated to 30-minute intervals (7:00 AM to 7:00 PM).")

DAY_MAP = {
    'M': 'Monday', 'T': 'Tuesday', 'W': 'Wednesday', 
    'TH': 'Thursday', 'F': 'Friday', 'S': 'Saturday'
}

# --- IMPROVED 30-MIN TIME LOGIC ---
def robust_time_parse(t_str):
    if not t_str or pd.isna(t_str):
        return None
    t_str = str(t_str).strip().upper()
    # Add space before AM/PM (fix 05:30PM -> 05:30 PM)
    t_str = re.sub(r'([AP]M)', r' \1', t_str).strip()
    
    try:
        return datetime.strptime(t_str, "%I:%M %p")
    except ValueError:
        try:
            # Fallback for "11:30" or "05:00"
            dt = datetime.strptime(t_str, "%H:%M")
            # UPLB Heuristic: 1-6 is PM
            if 1 <= dt.hour <= 6:
                return dt.replace(hour=dt.hour + 12)
            return dt
        except:
            return None

def get_row_index(dt):
    """Maps time to 30-minute rows. 7:00 AM is 0, 7:30 AM is 1, etc."""
    if not dt: return -1
    h = dt.hour
    m = dt.minute
    # Calculate index based on 7:00 AM start
    # Formula: (Hours from 7) * 2 + (1 if minutes >= 30)
    if 7 <= h <= 19:
        idx = (h - 7) * 2 + (1 if m >= 30 else 0)
        return idx
    return -1

# --- FILE LOADING ---
uploaded_file = st.file_uploader("Upload your CSV or JSON", type=["csv", "json"])

if uploaded_file:
    try:
        raw_data = []
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

        # --- 30-MIN GRID INITIALIZATION ---
        days_list = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        header = ["Time"] + days_list
        
        # Generate 24 labels for 30-minute intervals
        time_labels = []
        current_time = datetime.strptime("07:00 AM", "%I:%M %p")
        for _ in range(24):
            time_labels.append(current_time.strftime("%I:%M %p"))
            current_time += timedelta(minutes=30)
        
        # 24 rows x 7 columns
        matrix = [["" for _ in range(7)] for _ in range(24)]
        for i, lbl in enumerate(time_labels):
            matrix[i][0] = f"<b>{lbl}</b>"

        # --- PLOTTING ---
        for entry in raw_data:
            day_name = DAY_MAP.get(str(entry['day']).strip())
            if day_name in days_list:
                col_idx = days_list.index(day_name) + 1
                
                start_dt = robust_time_parse(entry['start'])
                end_dt = robust_time_parse(entry['end'])
                
                if start_dt and end_dt:
                    s_row = get_row_index(start_dt)
                    e_row = get_row_index(end_dt)
                    
                    # If end time is exactly on a 30-min mark (e.g., 10:30), 
                    # don't fill the slot starting at 10:30.
                    if end_dt.minute % 30 == 0:
                        e_row -= 1

                    if s_row != -1:
                        e_row = min(e_row, 23) # Cap at the last 6:30 PM slot
                        for r_idx in range(s_row, e_row + 1):
                            if 0 <= r_idx < 24:
                                t_range = f"{start_dt.strftime('%I:%M')}-{end_dt.strftime('%I:%M')}"
                                info = f"<b>{entry['subject']}</b><br>{entry['room']}<br><small>{t_range}</small>"
                                
                                # Add content or append if overlapping
                                if matrix[r_idx][col_idx] == "":
                                    matrix[r_idx][col_idx] = info
                                elif entry['subject'] not in matrix[r_idx][col_idx]:
                                    matrix[r_idx][col_idx] += f"<hr style='margin:1px;'>{info}"

        # --- RENDER ---
        fig = go.Figure(data=[go.Table(
            columnwidth = [80, 150, 150, 150, 150, 150, 150],
            header=dict(
                values=[f"<b>{h}</b>" for h in header],
                fill_color='#1B5E20', font=dict(color='white', size=14),
                height=40, align='center'
            ),
            cells=dict(
                values=list(zip(*matrix)),
                fill_color=[['#ffffff', '#f1f8e9']*12], # Zebra rows
                align='center', 
                font=dict(color='#212121', size=10),
                height=60 # Slightly shorter cells because there are more rows
            )
        )])

        fig.update_layout(width=1100, height=1600, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
        st.success("Successfully generated 30-minute interval schedule.")

    except Exception as e:
        st.error(f"Error: {e}")
