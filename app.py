import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="CSV to HD Schedule", layout="wide")

# Custom Styling
st.markdown("""
    <style>
    .main { background-color: #f5f5f5; }
    </style>
    """, unsafe_allow_html=True)

st.title("🖼️ CSV to HD Schedule Converter")
st.write("Turn your AMIS data into a crystal-clear, high-definition PNG schedule.")

# --- STEP 1: UPLOAD CSV ---
uploaded_file = st.file_uploader("Upload your schedule CSV", type="csv")

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file)
        
        # Clean column names just in case
        df.columns = [c.strip() for c in df.columns]

        # Define Grid Constants
        days = ["Time", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        hours = ["7:00", "8:00", "9:00", "10:00", "11:00", "12:00", "1:00", "2:00", "3:00", "4:00", "5:00", "6:00"]
        
        # Initialize an empty matrix (12 hours x 7 columns)
        schedule_matrix = [["" for _ in range(len(days))] for _ in range(len(hours))]
        
        # Pre-fill the Time column
        for i, h in enumerate(hours):
            schedule_matrix[i][0] = f"<b>{h}</b>"

        # --- STEP 2: DATA MAPPING ---
        for _, row in df.iterrows():
            day_val = str(row['Day']).strip()
            time_val = str(row['Time']).strip()
            
            if day_val in days:
                d_idx = days.index(day_val)
                
                # Logic to find the correct hour row (matches "7-8" to "7:00")
                h_start = time_val.split('-')[0].strip()
                h_idx = -1
                for i, h in enumerate(hours):
                    if h_start in h or h.split(':')[0] == h_start:
                        h_idx = i
                        break
                
                if h_idx != -1:
                    class_name = row.get('Class', 'N/A')
                    loc = row.get('Location', '')
                    is_shift = row.get('Type', '') == "30-min Shift"
                    
                    # Formatting text for the cell
                    cell_content = f"<b>{class_name}</b><br>{loc}"
                    if is_shift:
                        cell_content += "<br><span style='color:red; font-size:10px;'><i>(30m Shift)</i></span>"
                    
                    schedule_matrix[h_idx][d_idx] = cell_content

        # --- STEP 3: CREATE PLOTLY TABLE ---
        fig = go.Figure(data=[go.Table(
            columnorder = [0,1,2,3,4,5,6],
            columnwidth = [80, 150, 150, 150, 150, 150, 150],
            header=dict(
                values=[f"<b>{d}</b>" for d in days],
                fill_color='#1B5E20', # UPLB Forest Green
                align='center',
                font=dict(color='white', size=16),
                height=45,
                line_color='white'
            ),
            cells=dict(
                values=list(zip(*schedule_matrix)),
                fill_color=[['#ffffff', '#f1f8e9']*6], # Zebra striping
                align='center',
                font=dict(color='#333333', size=13),
                height=70,
                line_color='#e0e0e0'
            )
        )])

        fig.update_layout(
            width=1100,
            height=950,
            margin=dict(l=20, r=20, t=20, b=20)
        )

        # Display results
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': True})

        # --- STEP 4: DOWNLOAD ---
        st.success("✅ HD Schedule Generated!")
        st.info("💡 **How to Save:** Hover over the schedule above and click the **Camera Icon** 📸 in the top right corner to download as a high-quality PNG.")

    except Exception as e:
        st.error(f"Error processing CSV: {e}")
        st.info("Ensure your CSV has columns: Day, Time, Class, Location")

else:
    # Template Help
    st.info("Waiting for CSV upload...")
    with st.expander("See Sample CSV Format"):
        sample_df = pd.DataFrame({
            "Day": ["Monday", "Wednesday"],
            "Time": ["7-8", "10-11"],
            "Class": ["MATH 27", "CMSC 11"],
            "Location": ["CAS B-2", "ICS LH-3"],
            "Type": ["Regular", "30-min Shift"]
        })
        st.dataframe(sample_df)
