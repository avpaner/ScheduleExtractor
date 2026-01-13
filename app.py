import streamlit as st
import json
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import re

st.set_page_config(page_title="AMIS Violet Precision Schedule", layout="wide")

st.title("📅 AMIS HD Precision Schedule")
st.write("Updated: Violet highlighting for classes and thickened grid lines.")

DAY_MAP = {'M': 'Monday', 'T': 'Tuesday', 'W': 'Wednesday', 'TH': 'Thursday', 'F': 'Friday', 'S': 'Saturday'}

def robust_time_parse(t_str):
    if not t_str or pd.isna(t_str): return None
    t_str = str(t_str).strip().upper()
    t_str = re.sub(r'([AP]M)', r' \1', t_str).strip()
    try:
        return datetime.strptime(t_str, "%I:%M %p")
    except ValueError:
        try:
            dt = datetime.strptime(t_str, "%H:%M")
            if 1 <= dt.hour <= 7:
                return dt.replace(hour=dt.hour + 12)
            return dt
        except:
            return None

def get_row_index(dt):
    if not dt: return -1
    ref = dt.replace(hour=7, minute=0, second=0, microsecond=0)
    diff_seconds = (dt - ref).total_seconds()
    return int(round(diff_seconds / 1800))

uploaded_file = st.file_uploader("Upload 2S2425-SCHED", type=["csv", "json"])

if uploaded_file:
    try:
        raw_data = []
        if uploaded_file.name.endswith('.json'):
            data = json.load(uploaded_file)
            for item in data:
                raw_data.append({'d': item.get('day'), 's': item.get('startTime'), 'e': item.get('endTime'), 'subj': item.get('subject'), 'rm': item.get('room')})
        else:
            df = pd.read_csv(uploaded_file)
            for _, row in df.iterrows():
                raw_data.append({'d': row.get('Day'), 's': row.get('Start Time'), 'e': row.get('End Time'), 'subj': row.get('Class'), 'rm': row.get('Location')})

        # --- 1. GRID & COLOR SETUP ---
        days_list = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        header = ["Time Range"] + days_list
        
        # 25 rows for 7:00 AM to 7:30 PM
        matrix = [["" for _ in range(7)] for _ in range(25)]
        # Initialize colors: White for empty, Light Grey for the time column
        color_matrix = [["#FFFFFF" for _ in range(7)] for _ in range(25)]
        
        curr = datetime.strptime("07:00 AM", "%I:%M %p")
        for i in range(25):
            next_t = curr + timedelta(minutes=30)
            matrix[i][0] = f"<b>{curr.strftime('%I:%M')} - {next_t.strftime('%I:%M %p')}</b>"
            color_matrix[i][0] = "#F3E5F5" # Very light violet for sidebar
            curr = next_t

        # --- 2. PRECISION FILLING & HIGHLIGHTING ---
        for entry in raw_data:
            day_full = DAY_MAP.get(str(entry['d']).strip())
            if day_full in days_list:
                col_idx = days_list.index(day_full) + 1
                start_dt = robust_time_parse(entry['s'])
                end_dt = robust_time_parse(entry['e'])
                
                if start_dt and end_dt:
                    s_idx = get_row_index(start_dt)
                    e_idx = get_row_index(end_dt)
                    
                    for r_idx in range(s_idx, e_idx):
                        if 0 <= r_idx < 25:
                            t_str = f"{start_dt.strftime('%-I:%M')}-{end_dt.strftime('%-I:%M%p')}"
                            info = f"<b>{entry['subj']}</b><br>{entry['rm']}<br><span style='font-size:9px;'>{t_str}</span>"
                            
                            if matrix[r_idx][col_idx] == "":
                                matrix[r_idx][col_idx] = info
                            elif entry['subj'] not in matrix[r_idx][col_idx]:
                                matrix[r_idx][col_idx] += f"<hr style='margin:1px;'>{info}"
                            
                            # HIGHLIGHT: Set this specific cell to Violet
                            color_matrix[r_idx][col_idx] = "#E1BEE7" # Soft Violet

        # --- 3. RENDER WITH THICK GRID LINES ---
        fig = go.Figure(data=[go.Table(
            columnwidth = [120, 150, 150, 150, 150, 150, 150],
            header=dict(
                values=[f"<b>{h}</b>" for h in header],
                fill_color='#4A148C', # Deep Violet Header
                font=dict(color='white', size=13),
                height=45,
                line=dict(color='black', width=2.5) # Thicker Border
            ),
            cells=dict(
                values=list(zip(*matrix)),
                fill_color=list(zip(*color_matrix)), # Apply our dynamic color matrix
                align='center',
                font=dict(size=10, color='black'),
                height=80,
                line=dict(color='black', width=2) # Thicker grid lines
            )
        )])

        fig.update_layout(width=1200, height=2000, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
        st.success("Visuals updated: Violet highlighting and thick grid lines active.")

    except Exception as e:
        st.error(f"Error: {e}")
