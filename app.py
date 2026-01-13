import streamlit as st
import json
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import re

st.set_page_config(page_title="AMIS HD Schedule Fixed", layout="wide")

st.title("📅 AMIS 30-Min Precision Schedule")
st.write("Fixed time discrepancy for PM classes and 30-minute interval accuracy.")

# Mapping for AMIS shorthand days
DAY_MAP = {'M': 'Monday', 'T': 'Tuesday', 'W': 'Wednesday', 'TH': 'Thursday', 'F': 'Friday', 'S': 'Saturday'}

def robust_time_parse(t_str):
    if not t_str or pd.isna(t_str): return None
    t_str = str(t_str).strip().upper()
    # Add space before AM/PM to fix "05:30PM"
    t_str = re.sub(r'([AP]M)', r' \1', t_str).strip()
    
    try:
        # Standard 12-hour parse
        return datetime.strptime(t_str, "%I:%M %p")
    except ValueError:
        try:
            # Fallback for "11:30" or "05:00" missing AM/PM
            dt = datetime.strptime(t_str, "%H:%M")
            # School logic: 1-6 is PM (13:00-18:00)
            if 1 <= dt.hour <= 6:
                return dt.replace(hour=dt.hour + 12)
            return dt
        except:
            return None

def get_row_index(dt):
    """Calculates row index based on 30-minute steps from 7:00 AM."""
    if not dt: return -1
    # We use a reference time of 7:00 AM to calculate the offset
    start_of_day = dt.replace(hour=7, minute=0)
    delta = dt - start_of_day
    total_minutes = delta.total_seconds() / 60
    return int(total_minutes // 30)

uploaded_file = st.file_uploader("Upload 2S2425-SCHED (JSON or CSV)", type=["csv", "json"])

if uploaded_file:
    try:
        # --- DATA NORMALIZATION ---
        raw_data = []
        if uploaded_file.name.endswith('.json'):
            data = json.load(uploaded_file)
            for item in data:
                raw_data.append({
                    'day': item.get('day'), 'start': item.get('startTime'),
                    'end': item.get('endTime'), 'subject': item.get('subject'), 'room': item.get('room')
                })
        else:
            df = pd.read_csv(uploaded_file)
            for _, row in df.iterrows():
                raw_data.append({
                    'day': row.get('Day'), 'start': row.get('Start Time'),
                    'end': row.get('End Time'), 'subject': row.get('Class'), 'room': row.get('Location')
                })

        # --- GRID SETUP (7:00 AM to 7:00 PM = 24 slots) ---
        days_list = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        header = ["Time"] + days_list
        
        time_labels = []
        curr = datetime.strptime("07:00 AM", "%I:%M %p")
        for _ in range(25): # Up to 7:00 PM
            time_labels.append(curr.strftime("%I:%M %p"))
            curr += timedelta(minutes=30)
        
        # 24 rows (each representing a 30-min block), 7 columns
        matrix = [["" for _ in range(7)] for _ in range(24)]
        for i in range(24):
            matrix[i][0] = f"<b>{time_labels[i]}</b>"

        # --- PRECISION PLOTTING ---
        for entry in raw_data:
            day_name = DAY_MAP.get(str(entry['day']).strip())
            if day_name in days_list:
                col_idx = days_list.index(day_name) + 1
                
                s_dt = robust_time_parse(entry['start'])
                e_dt = robust_time_parse(entry['end'])
                
                if s_dt and e_dt:
                    s_row = get_row_index(s_dt)
                    e_row = get_row_index(e_dt)
                    
                    # Fill all 30-minute slots between start and end
                    # Example: 1:00 PM (row 12) to 4:00 PM (row 18)
                    for r_idx in range(s_row, e_row):
                        if 0 <= r_idx < 24:
                            t_range = f"{s_dt.strftime('%I:%M')}-{e_dt.strftime('%I:%M')}"
                            info = f"<b>{entry['subject']}</b><br>{entry['room']}<br><small>{t_range}</small>"
                            
                            if matrix[r_idx][col_idx] == "":
                                matrix[r_idx][col_idx] = info
                            elif entry['subject'] not in matrix[r_idx][col_idx]:
                                matrix[r_idx][col_idx] += f"<hr style='margin:1px;'>{info}"

        # --- RENDER HD TABLE ---
        fig = go.Figure(data=[go.Table(
            columnwidth = [90, 150, 150, 150, 150, 150, 150],
            header=dict(
                values=[f"<b>{h}</b>" for h in header],
                fill_color='#1B5E20', font=dict(color='white', size=14), height=40
            ),
            cells=dict(
                values=list(zip(*matrix)),
                fill_color=[['#ffffff', '#f9f9f9']*12],
                align='center', font=dict(color='#212121', size=10), height=55
            )
        )])

        fig.update_layout(width=1100, height=1500, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
        st.success("Precision grid generated. No more time discrepancies.")

    except Exception as e:
        st.error(f"Error: {e}")
