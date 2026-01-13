from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import json
import io
from datetime import datetime, timedelta
import re

app = FastAPI()

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
    content = await file.read()
    
    # Handle JSON or CSV
    if file.filename.endswith('.json'):
        data = json.loads(content)
        df = pd.DataFrame(data)
        # Normalize keys if JSON uses different naming
        df = df.rename(columns={'startTime': 'Start Time', 'endTime': 'End Time', 'day': 'Day'})
    else:
        df = pd.read_csv(io.BytesIO(content))

    DAY_MAP = {'M': 'Monday', 'T': 'Tuesday', 'W': 'Wednesday', 'TH': 'Thursday', 'F': 'Friday', 'S': 'Saturday'}
    busy_ids = []

    for _, row in df.iterrows():
        day_val = str(row.get('Day', '')).strip().upper()
        day_full = DAY_MAP.get(day_val, day_val)
        start_dt = robust_time_parse(row.get('Start Time'))
        end_dt = robust_time_parse(row.get('End Time'))

        if day_full and start_dt and end_dt:
            curr = start_dt
            while curr < end_dt:
                hour = curr.hour
                ampm = "AM" if hour < 12 else "PM"
                dh = hour - 12 if hour > 12 else (12 if hour == 0 else hour)
                minute = curr.strftime("%M")
                # Format exactly matches HTML ID: Monday-800AM
                busy_ids.append(f"{day_full}-{dh}{minute}{ampm}")
                curr += timedelta(minutes=30)

    return {"busy_slots": list(set(busy_ids))}
