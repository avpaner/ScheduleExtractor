import streamlit as st
import json
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import re

st.set_page_config(page_title="AMIS Final Precision Plotter", layout="wide")

st.title("📅 AMIS HD Precision Schedule")
st.write("Fixed: End-time accuracy and grid alignment for 1-hour and multi-hour classes.")

DAY_MAP = {'M': 'Monday', 'T': 'Tuesday', 'W': 'Wednesday', 'TH': 'Thursday', 'F': 'Friday', 'S': 'Saturday'}

def robust_time_parse(t_str):
    """Parses AMIS time strings and ensures PM/AM logic is consistent."""
    if not t_str or pd.isna(t_str): return None
    t_str = str(t_str).strip().upper()
    # Ensure space before AM/PM (fix "05:30PM")
    t_str = re.sub(r'([AP]M)', r' \1', t_str).strip()
    
    try:
        # Try standard 12-hour format first
        return datetime.strptime(t_str, "%I:%M %p")
    except ValueError:
        try:
            # Fallback for missing AM/PM (like "09:00 " or "05:00 ")
            dt = datetime.strptime(t_str, "%H:%M")
            # School heuristic: 1:00 to 7:59 is PM
            if 1 <= dt.hour <= 7:
                return dt.replace(hour=dt.hour + 12)
            return dt
        except:
            return None

def get_row_index(dt):
    """Calculates exactly which 30-minute slot a time falls into."""
    if not dt: return -1
    # Reference: Grid starts at 7:00 AM
    ref = dt.replace(hour=7, minute=0, second=0, microsecond=0)
    diff_seconds = (dt - ref).total_seconds()
    # Using round to handle float precision (e.g. 59.999 -> 60)
    return int(round(diff_seconds / 1800)) # 1800 seconds = 30 minutes

uploaded_file = st.file_uploader("Upload 2S2425-SCHED", type=["csv", "json"])

if uploaded_file:
    try:
        # --- 1. NORMALIZE DATA ---
        raw_data = []
        if uploaded_file.name.endswith('.json'):
            data = json.load(uploaded_file)
            for item in data:
                raw_data.append({'d': item.get('day'), 's': item.get('startTime'), 'e': item.get('endTime'), 'subj': item.get('subject'), 'rm': item.get('room')})
        else:
            df = pd.read_csv(uploaded_file)
            for _, row in df.iterrows():
                raw_data.append({'d': row.get('Day'), 's': row.get('Start Time'), 'e': row.get('End Time'), 'subj': row.get('Class'), 'rm': row.get('Location')})

        # --- 2. GRID SETUP (7 AM to 7:30 PM = 25 slots) ---
        days_list = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        header = ["Time Range"] + days_list
        matrix = [["" for _ in range(7)] for _ in range(25)]
        
        # Create clear Range Labels for the first column
        curr = datetime.strptime("07:00 AM", "%I:%M %p")
        for i in range(25):
            next_t = curr + timedelta(minutes=30)
            matrix[i][0] = f"<b>{curr.strftime('%I:%M')} - {next_t.strftime('%I:%M %p')}</b>"
            curr = next_t

        # --- 3. PRECISION FILLING ---
        for entry in raw_data:
            day_full = DAY_MAP.get(str(entry['d']).strip())
            if day_full in days_list:
                col_idx = days_list.index(day_full) + 1
                start_dt = robust_time_parse(entry['s'])
                end_dt = robust_time_parse(entry['e'])
                
                if start_dt and end_dt:
                    s_idx = get_row_index(start_dt)
                    e_idx = get_row_index(end_dt)
                    
                    # Fill every slot between start and end
                    # Example: 8:00 (2) to 9:00 (4) fills index 2 and 3.
                    for r_idx in range(s_idx, e_idx):
                        if 0 <= r_idx < 25:
                            t_str = f"{start_dt.strftime('%-I:%M')}-{end_dt.strftime('%-I:%M%p')}"
                            info = f"<b>{entry['subj']}</b><br>{entry['rm']}<br><span style='font-size:9px;'>{t_str}</span>"
                            
                            if matrix[r_idx][col_idx] == "":
                                matrix[r_idx][col_idx] = info
                            elif entry['subj'] not in matrix[r_idx][col_idx]:
                                matrix[r_idx][col_idx] += f"<hr style='margin:1px;'>{info}"

        # --- 4. RENDER ---
        fig = go.Figure(data=[go.Table(
            columnwidth = [110, 150, 150, 150, 150, 150, 150],
            header=dict(
                values=[f"<b>{h}</b>" for h in header],
                fill_color='#1B5E20', font=dict(color='white', size=13), height=40
            ),
            cells=dict(
                values=list(zip(*matrix)),
                # Correct multi-column zebra striping
                fill_color=[['#f5f5f5']*25] + [['#ffffff', '#f9f9f9']*13]*6,
                align='center', font=dict(size=10), height=75
            )
        )])

        fig.update_layout(width=1200, height=1900, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
        st.success("Accurate grid generated. Time ranges now match your schedule exactly.")

    except Exception as e:
        st.error(f"Error processing schedule: {e}")
