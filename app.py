import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import re

st.set_page_config(page_title="AMIS HD Schedule", layout="wide")

st.title("📅 AMIS Class Schedule Plotter")
st.write("Ensuring all classes from your 2S2425-SCHED.csv are accurately plotted.")

# Day mapping for AMIS shorthands
DAY_MAP = {
    'M': 'Monday',
    'T': 'Tuesday',
    'W': 'Wednesday',
    'TH': 'Thursday',
    'F': 'Friday',
    'S': 'Saturday'
}

uploaded_file = st.file_uploader("Upload 2S2425-SCHED.csv", type="csv")

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file)
        
        # Grid Setup: 7:00 AM to 7:00 PM
        days_full = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        header_labels = ["Time"] + days_full
        hours_labels = ["7-8", "8-9", "9-10", "10-11", "11-12", "12-1", "1-2", "2-3", "3-4", "4-5", "5-6", "6-7"]
        
        matrix = [["" for _ in range(7)] for _ in range(12)]
        for i, label in enumerate(hours_labels):
            matrix[i][0] = f"<b>{label}</b>"

        # --- REFINED TIME PARSING LOGIC ---
        def clean_and_parse_time(t_str):
            if pd.isna(t_str): return None
            t_str = str(t_str).strip().upper()
            
            # Fix "05:30PM" -> "05:30 PM"
            t_str = re.sub(r'([AP]M)', r' \1', t_str).strip()
            
            # Try parsing with AM/PM
            try:
                return datetime.strptime(t_str, "%I:%M %p")
            except ValueError:
                # If AM/PM is missing, guess based on UPLB typical hours
                try:
                    dt = datetime.strptime(t_str, "%H:%M")
                    if 7 <= dt.hour <= 11:
                        return dt.replace(hour=dt.hour) # Keeps as AM
                    else:
                        return dt.replace(hour=dt.hour + 12 if dt.hour < 12 else dt.hour)
                except:
                    return None

        for _, row in df.iterrows():
            day_key = str(row['Day']).strip()
            day_name = DAY_MAP.get(day_key)
            
            if day_name in days_full:
                d_idx = days_full.index(day_name) + 1
                
                start_dt = clean_and_parse_time(row['Start Time'])
                end_dt = clean_and_parse_time(row['End Time'])
                
                if start_dt and end_dt:
                    # Mapping to rows (7AM = 0, 1PM = 6)
                    def get_row_idx(dt):
                        h = dt.hour
                        if 7 <= h <= 12: return h - 7
                        if 1 <= h <= 6: return h + 5
                        return -1

                    s_row = get_row_idx(start_dt)
                    e_row = get_row_idx(end_dt)
                    if end_dt.minute == 0: e_row -= 1

                    for r_idx in range(s_row, e_row + 1):
                        if 0 <= r_idx < 12:
                            # Format content for your specific classes
                            content = f"<b>{row['Class']}</b><br><small>{row['Location']}</small>"
                            
                            if matrix[r_idx][d_idx] == "":
                                matrix[r_idx][d_idx] = content
                            elif row['Class'] not in matrix[r_idx][d_idx]:
                                matrix[r_idx][d_idx] += f"<hr style='margin:2px;'>{content}"

        # --- DISPLAY ---
        fig = go.Figure(data=[go.Table(
            columnwidth = [60, 140, 140, 140, 140, 140, 140],
            header=dict(
                values=[f"<b>{h}</b>" for h in header_labels],
                fill_color='#1B5E20', font=dict(color='white', size=14),
                height=40, align='center'
            ),
            cells=dict(
                values=list(zip(*matrix)),
                fill_color=[['#ffffff', '#f1f8e9']*6],
                align='center', font=dict(color='#212121', size=11),
                height=90
            )
        )])

        fig.update_layout(width=1100, height=1100, margin=dict(l=5, r=5, t=5, b=5))
        st.plotly_chart(fig, use_container_width=True)
        st.success(f"Plotted {len(df)} entries successfully.")

    except Exception as e:
        st.error(f"Error: {e}")
