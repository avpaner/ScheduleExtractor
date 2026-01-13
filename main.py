from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from datetime import datetime, timedelta
import re
import io

app = FastAPI()

# IMPORTANT: This allows your HTML website to talk to this Python API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

def robust_time_parse(t_str):
    if not t_str or pd.isna(t_str): return None
    t_str = str(t_str).strip().upper()
    t_str = re.sub(r'([AP]M)', r' \1', t_str).strip()
    try:
        return datetime.strptime(t_str, "%I:%M %p")
    except:
        try:
            dt = datetime.strptime(t_str, "%H:%M")
            if 1 <= dt.hour <= 7: return dt.replace(hour=dt.hour + 12)
            return dt
        except: return None

@app.post("/process")
async def process_schedule(file: UploadFile = File(...)):
    # Read the uploaded CSV
    content = await file.read()
    df = pd.read_csv(io.BytesIO(content))
    
    DAY_MAP = {'M': 'Monday', 'T': 'Tuesday', 'W': 'Wednesday', 'TH': 'Thursday', 'F': 'Friday', 'S': 'Saturday'}
    busy_ids = []
    
    for _, row in df.iterrows():
        day_full = DAY_MAP.get(str(row['Day']).strip())
        start_dt = robust_time_parse(row['Start Time'])
        end_dt = robust_time_parse(row['End Time'])
        
        if day_full and start_dt and end_dt:
            curr = start_dt
            while curr < end_dt:
                # This creates IDs like "Monday-800AM" to match your HTML
                hour = curr.hour
                ampm = "AM" if hour < 12 else "PM"
                dh = hour - 12 if hour > 12 else (12 if hour == 0 else hour)
                minute = curr.strftime("%M")
                
                slot_id = f"{day_full}-{dh}{minute}{ampm}"
                busy_ids.append(slot_id)
                curr += timedelta(minutes=30)
                
    return {"busy_slots": list(set(busy_ids))}