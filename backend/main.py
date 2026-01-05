from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import driver
import os

app = FastAPI(title="Omen Linux Fan Control")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve Frontend
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_path):
    app.mount("/ui", StaticFiles(directory=frontend_path, html=True), name="static")

fan = driver.FanDriver()

class FanSpeed(BaseModel):
    percentage: int

class FanMode(BaseModel):
    mode: str # "auto", "max", "manual"

@app.get("/")
def read_root():
    return {"status": "online", "system": "HP Victus"}

@app.get("/status")
def get_status():
    temps = fan.get_temps()
    rpm = fan.get_rpm()
    return {
        "temps": temps,
        "fan": {
            "rpm": rpm,
            "rpm_approx": rpm, # Legacy field support
            "mode": "unknown" 
        }
    }

@app.post("/fan/mode/{mode}")
def set_mode(mode: str):
    if mode == "max":
        fan.set_max_mode()
        return {"status": "success", "mode": "max"}
    elif mode == "auto":
        fan.set_auto_mode()
        return {"status": "success", "mode": "auto"}
    else:
        raise HTTPException(status_code=400, detail="Invalid mode. Use 'max' or 'auto'.")

@app.post("/fan/speed")
def set_speed(speed: FanSpeed):
    if 0 <= speed.percentage <= 100:
        fan.set_manual_speed(speed.percentage)
        return {"status": "success", "speed": speed.percentage}
    else:
        raise HTTPException(status_code=400, detail="Speed must be 0-100")

if __name__ == "__main__":
    # We need to run as root for ACPI calls to work
    uvicorn.run(app, host="0.0.0.0", port=8000)
