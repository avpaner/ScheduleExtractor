import streamlit as st
import json
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import re

st.set_page_config(page_title="AMIS Precision Schedule", layout="wide")

st.title("📅 AMIS 30-Min Precision Plotter")
st.write("Fixed: Row index accuracy and time label discrepancies.")

# Shorthand mapping
DAY_MAP = {'M': 'Monday', 'T': 'Tuesday', 'W': 'Wednesday', 'TH': 'Thursday', 'F': 'Friday', 'S': 'Saturday'}

def robust_time_parse(t_str):
    """Parses various AMIS time strings into datetime objects."""
    if not t_str or pd.isna(t_str): return None
    t_str = str(t_str).strip().upper()
    # Fix "05:30PM" -> "05:30 PM"
    t_str = re.sub(r'([AP]M)', r' \1', t_str).strip()
    
    try:
        # Standard 12-hour format
        return datetime.strptime(t_str, "%I:%M %p")
    except ValueError:
        try:
            # Fallback for "11:30" or "05:00" without AM/PM tags
            dt = datetime.strptime(t_str, "%H:%M")
            # UPLB Heuristic: 1:00-6:59 is PM
            if 1 <= dt.hour <= 6:
                return dt.replace(hour=dt.hour + 12)
            return dt
        except:
            return None

def get_row_index(dt):
    """Calculates row index (0-23) based on 30-min steps from 7:00 AM."""
    if not dt: return -1
    # Use round() to prevent floating point errors (e.g., 20.999 -> 20)
    # Reference: 7:00 AM is the start of our grid
    ref_time = dt.replace(hour=7, minute=0, second=0, microsecond=0)
    delta_mins = (dt - ref_time).total_seconds() / 60
    return int(round(delta_mins / 30))

uploaded_file = st.file_uploader("Upload 2S2425-SCHED (JSON or CSV)", type=["csv", "json"])

if uploaded_file:
    try:
        # --- 1. DATA LOADING ---
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

        # --- 2. GRID INITIALIZATION ---
        days_list = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        header = ["Time"] + days_list
        
        # 24 rows for 30-min blocks from 7:00 AM to 7:00 PM
        matrix = [["" for _ in range(7)] for _ in range(24)]
        
        # Generate row labels
        curr = datetime.strptime("07:00 AM", "%I:%M %p")
        for i in range(24):
            matrix[i][0] = f"<b>{curr.strftime('%I:%M %p')}</b>"
            curr += timedelta(minutes=30)

        # --- 3. PLOTTING WITH ROUNDING FIX ---
        for entry in raw_data:
            day_name = DAY_MAP.get(str(entry['day']).strip())
            if day_name in days_list:
                col_idx = days_list.index(day_name) + 1
                
                s_dt = robust_time_parse(entry['start'])
                e_dt = robust_time_parse(entry['end'])
                
                if s_dt and e_dt:
                    s_row = get_row_index(s_dt)
                    e_row = get_row_index(e_dt)
                    
                    # Fill all slots the class spans
                    # (Uses range(s, e) so a class ending at 9:00 doesn't fill the 9:00 slot)
                    for r_idx in range(s_row, e_row):
                        if 0 <= r_idx < 24:
                            # Show specific range in the cell for verification
                            t_range = f"{s_dt.strftime('%-I:%M%p')}-{e_dt.strftime('%-I:%M%p')}"
                            content = f"<b>{entry['subject']}</b><br>{entry['room']}<br><span style='font-size:9px;'>{t_range}</span>"
                            
                            if matrix[r_idx][col_idx] == "":
                                matrix[r_idx][col_idx] = content
                            elif entry['subject'] not in matrix[r_idx][col_idx]:
                                matrix[r_idx][col_idx] += f"<hr style='margin:1px;'>{content}"

        # --- 4. RENDER TABLE ---
        fig = go.Figure(data=[go.Table(
            columnwidth = [95, 150, 150, 150, 150, 150, 150],
            header=dict(
                values=[f"<b>{h}</b>" for h in header],
                fill_color='#1B5E20', font=dict(color='white', size=14), height=40
            ),
            cells=dict(
                values=list(zip(*matrix)),
                fill_color=[['#ffffff', '#f9f9f9']*12], # Clean zebra stripes
                align='center', font=dict(color='#212121', size=10.5), height=65
            )
        )])

        fig.update_layout(width=1200, height=1700, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
        st.success("Precision 30-minute grid generated.")

    except Exception as e:
        st.error(f"Critical error during plotting: {e}")
