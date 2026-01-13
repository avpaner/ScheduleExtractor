import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="AMIS CSV to HD Schedule", layout="wide")

# Custom Styling
st.markdown("""
    <style>
    .main { background-color: #f5f5f5; }
    </style>
    """, unsafe_allow_html=True)

st.title("🖼️ AMIS Schedule Converter")
st.write("Upload your extracted CSV to generate a high-definition PNG schedule.")

# --- STEP 1: UPLOAD CSV ---
uploaded_file = st.file_uploader("Upload your schedule CSV", type="csv")

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file)
        
        # Clean column names
        df.columns = [c.strip() for c in df.columns]

        # Define Grid Constants
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        header_labels = ["Time"] + days
        hours = ["7:00", "8:00", "9:00", "10:00", "11:00", "12:00", "1:00", "2:00", "3:00", "4:00", "5:00", "6:00"]
        
        # Initialize an empty matrix (12 hours x 7 columns)
        # We add 1 to columns to account for the "Time" column at index 0
        schedule_matrix = [["" for _ in range(len(header_labels))] for _ in range(len(hours))]
        
        # Pre-fill the Time column (Index 0)
        for i, h in enumerate(hours):
            schedule_matrix[i][0] = f"<b>{h}-{int(h.split(':')[0])+1}:00</b>" if h != "12:00" else "<b>12:00-1:00</b>"

        # --- STEP 2: DATA MAPPING ---
        for _, row in df.iterrows():
            day_val = str(row['Day']).strip()
            start_val = str(row['Start Time']).strip()
            end_val = str(row['End Time']).strip()
            
            if day_val in days:
                # Column index is day index + 1 (because of Time column)
                d_idx = days.index(day_val) + 1
                
                # Logic to find the correct hour row based on Start Time
                # Matches "7:00" or "7:30" to the "7:00" row
                h_prefix = start_val.split(':')[0]
                h_idx = -1
                for i, h in enumerate(hours):
                    if h.startswith(h_prefix + ":"):
                        h_idx = i
                        break
                
                if h_idx != -1:
                    class_name = row.get('Class', 'N/A')
                    loc = row.get('Location', 'TBA')
                    
                    # Detect if it's a 30-min shift based on the time strings
                    is_shifted = ":30" in start_val or ":30" in end_val
                    
                    # Formatting text for the cell
                    cell_content = f"<b>{class_name}</b><br>{loc}<br>{start_val}-{end_val}"
                    if is_shifted:
                        cell_content = f"<span style='font-size:11px;'>{cell_content}</span>"
                    
                    # If multiple classes land in one slot, append them
                    if schedule_matrix[h_idx][d_idx] != "":
                        schedule_matrix[h_idx][d_idx] += "<br>---<br>" + cell_content
                    else:
                        schedule_matrix[h_idx][d_idx] = cell_content

        # --- STEP 3: CREATE PLOTLY TABLE ---
        fig = go.Figure(data=[go.Table(
            columnorder = [0,1,2,3,4,5,6],
            columnwidth = [100, 150, 150, 150, 150, 150, 150],
            header=dict(
                values=[f"<b>{d}</b>" for d in header_labels],
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
                font=dict(color='#333333', size=12),
                height=80,
                line_color='#e0e0e0'
            )
        )])

        fig.update_layout(width=1100, height=1000, margin=dict(l=20, r=20, t=20, b=20))

        # Display results
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': True})

        # --- STEP 4: DOWNLOAD ---
        st.success("✅ HD Schedule Generated!")
        st.info("💡 **How to Save:** Hover over the table and click the **Camera Icon** 📸 to download your PNG.")

    except Exception as e:
        st.error(f"Error processing CSV: {e}")
        st.info("Required CSV Columns: Day, Start Time, End Time, Class, Location")

else:
    st.info("Waiting for CSV upload...")
    with st.expander("See Required CSV Format"):
        sample_df = pd.DataFrame({
            "Day": ["Monday", "Tuesday"],
            "Start Time": ["8:00", "10:30"],
            "End Time": ["9:00", "11:30"],
            "Class": ["FST 130", "ABME 10"],
            "Location": ["TBA", "CEM FH"]
        })
        st.dataframe(sample_df)
