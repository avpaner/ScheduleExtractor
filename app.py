import streamlit as st
import pandas as pd
import plotly.figure_factory as ff
import plotly.graph_objects as go

st.set_page_config(page_title="CSV to HD Schedule", layout="wide")

st.title("🖼️ CSV to HD Schedule Converter")
st.write("Upload your CSV to generate a crystal-clear, high-resolution PNG schedule.")

uploaded_file = st.file_uploader("Upload Schedule CSV", type="csv")

if uploaded_file:
    df = pd.DataFrame(pd.read_csv(uploaded_file))
    
    # Define the 7x13 Grid Structure
    days = ["Time", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    hours = ["7:00", "8:00", "9:00", "10:00", "11:00", "12:00", "1:00", "2:00", "3:00", "4:00", "5:00", "6:00"]
    
    # Create an empty matrix for the table
    schedule_matrix = [["" for _ in range(len(days))] for _ in range(len(hours))]
    
    # Fill the Time column
    for i, h in enumerate(hours):
        schedule_matrix[i][0] = f"<b>{h}</b>"

    # Fill the matrix with CSV data
    for _, row in df.iterrows():
        try:
            d_idx = days.index(row['Day'])
            # Logic to find the hour row (e.g., "7-8" matches "7:00")
            h_str = row['Time'].split('-')[0].strip()
            h_idx = -1
            for i, h in enumerate(hours):
                if h_str in h:
                    h_idx = i
                    break
            
            if h_idx != -1:
                # Format cell text
                cell_text = f"<b>{row['Class']}</b><br>{row['Location']}"
                if row.get('Type') == "30-min Shift":
                    cell_text += "<br><i>(30m Shift)</i>"
                schedule_matrix[h_idx][d_idx] = cell_text
        except:
            continue

    # Create the Table Figure
    fig = go.Figure(data=[go.Table(
        header=dict(
            values=[f"<b>{d}</b>" for d in days],
            fill_color='#1B5E20', # Dark UPLB Green
            align='center',
            font=dict(color='white', size=14),
            height=40
        ),
        cells=dict(
            values=list(zip(*schedule_matrix)),
            fill_color=[['#f8f9fa', '#e8f5e9']*6], # Alternating row colors
            align='center',
            font=dict(color='black', size=12),
            height=60
        )
    )])

    fig.update_layout(width=1200, height=800, margin=dict(l=10, r=10, t=10, b=10))

    # Display in App
    st.plotly_chart(fig, use_container_width=True)

    # Export Logic
    st.info("To save as PNG: Hover over the chart above and click the **Camera Icon** (Download plot as a png).")
