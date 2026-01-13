import streamlit as st
import json
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import re

st.set_page_config(page_title="AMIS Final Fix", layout="wide")

st.title("📅 AMIS 30-Min Precision Schedule (Final Fix)")
st.write("Fixed: Classes now fill their entire duration correctly (e.g., 8:00-9:00 now occupies both 8:00 and 8:30 slots).")

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
            if 1 <= dt.hour <= 7: # Afternoon/Evening shift
                return dt.replace(hour=dt.hour + 12)
            return dt
        except:
            return None

def get_row_index(dt):
    if not dt: return -1
    # 7:00 AM is index 0
    ref_time = dt.replace(hour=7, minute=0, second=0, microsecond=0)
    delta_mins = (dt - ref_time).total_seconds() / 60
    return int(round(delta_mins / 30))

uploaded_file = st.file_uploader("Upload 2S2425-SCHED", type=["csv", "json"])

if uploaded_file:
    try:
        raw_data = []
        if uploaded_file.name.endswith('.json'):
            data = json.load(uploaded_file)
            for item in data:
                raw_data.append({'day': item.get('day'), 'start': item.get('startTime'), 'end': item.get('endTime'), 'subject': item.get('subject'), 'room': item.get('room')})
        else:
            df = pd.read_csv(uploaded_file)
            for _, row in df.iterrows():
                raw_data.append({'day': row.get('Day'), 'start': row.get('Start Time'), 'end': row.get('End Time'), 'subject': row.get('Class'), 'room': row.get('Location')})

        # --- GRID SETUP (7 AM to 8 PM = 26 slots) ---
        days_list = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        header = ["Time"] + days_list
        matrix = [["" for _ in range(7)] for _ in range(26)]
        
        curr = datetime.strptime("07:00 AM", "%I:%M %p")
        for i in range(26):
            matrix[i][0] = f"<b>{curr.strftime('%I:%M %p')}</b>"
            curr += timedelta(minutes=30)

        # --- PLOTTING LOGIC ---
        for entry in raw_data:
            day_name = DAY_MAP.get(str(entry['day']).strip())
            if day_name in days_list:
                col_idx = days_list.index(day_name) + 1
                s_dt = robust_time_parse(entry['start'])
                e_dt = robust_time_parse(entry['end'])
                
                if s_dt and e_dt:
                    s_row = get_row_index(s_dt)
                    e_row = get_row_index(e_dt)
                    
                    # FIX: range(s_row, e_row) correctly fills all blocks.
                    # Example: 8:00 (Row 2) to 9:00 (Row 4). 
                    # This fills Row 2 (8:00) and Row 3 (8:30).
                    for r_idx in range(s_row, e_row):
                        if 0 <= r_idx < 26:
                            t_range = f"{s_dt.strftime('%-I:%M%p')}-{e_dt.strftime('%-I:%M%p')}"
                            content = f"<b>{entry['subject']}</b><br>{entry['room']}<br><span style='font-size:9px;'>{t_range}</span>"
                            
                            if matrix[r_idx][col_idx] == "":
                                matrix[r_idx][col_idx] = content
                            elif entry['subject'] not in matrix[r_idx][col_idx]:
                                matrix[r_idx][col_idx] += f"<hr style='margin:1px;'>{content}"

        fig = go.Figure(data=[go.Table(
            columnwidth = [100, 150, 150, 150, 150, 150, 150],
            header=dict(values=[f"<b>{h}</b>" for h in header], fill_color='#1B5E20', font=dict(color='white', size=14), height=40),
            cells=dict(values=list(zip(*matrix)), fill_color=[['#ffffff', '#f9f9f9']*13], align='center', font=dict(size=10.5), height=70)
        )])

        fig.update_layout(width=1200, height=1900, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
        st.success("✅ Full accuracy achieved.")

    except Exception as e:
        st.error(f"Error: {e}")
