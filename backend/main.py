from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import driver
import os

app = FastAPI(title="Omen Linux Fan Control")

# No CORS middleware: the frontend is served by this same app (see the
# StaticFiles mount below) and is only ever accessed same-origin via
# http://localhost:8000/ui/ (see scripts/start.sh, scripts/launch.sh). This
# API writes directly to Embedded Controller memory and runs as root, so it
# must never accept cross-origin requests.

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
    try:
        if mode == "max":
            fan.set_max_mode()
            return {"status": "success", "mode": "max"}
        elif mode == "auto":
            fan.set_auto_mode()
            return {"status": "success", "mode": "auto"}
        elif mode == "manual":
            # Manual mode is implicitly set when setting speed, but we allow the call to acknowledge it.
            return {"status": "success", "mode": "manual"}
        else:
            raise HTTPException(status_code=400, detail="Invalid mode. Use 'max', 'auto', or 'manual'.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hardware access failed: {e}. Is the server running as root?")

@app.post("/fan/speed")
def set_speed(percentage: int):
    if 0 <= percentage <= 100:
        try:
            fan.set_manual_speed(percentage)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Hardware access failed: {e}. Is the server running as root?")
        return {"status": "success", "speed": percentage}
    else:
        raise HTTPException(status_code=400, detail="Speed must be 0-100")

if __name__ == "__main__":
    # Bind to localhost only: this API writes directly to Embedded
    # Controller memory and runs as root. The frontend only ever calls it
    # same-origin via http://localhost:8000/ui/ - there is no legitimate
    # reason to expose it on the network.
    uvicorn.run(app, host="127.0.0.1", port=8000)
