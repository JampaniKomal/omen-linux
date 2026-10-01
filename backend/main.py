"""Omen Linux backend: a localhost API over the fan driver, plus the dashboard.

It runs as root (the EC is reached through /dev/mem), so it protects itself:

- **Only this machine's own pages can call it.** The API listens on 127.0.0.1,
  rejects requests whose Host is not localhost (DNS rebinding), and every POST
  must carry the X-Omen-Linux header. A web page on another site cannot add
  that header without a CORS preflight, which this server never approves, so
  the sites open in your browser cannot drive your fans.
- **The fans cannot be left too slow while the machine is hot.** A watchdog
  hands control back to the BIOS when the CPU or GPU reaches OMEN_SAFE_TEMP
  (90 C by default) and the fan is below full speed, and lower speeds are
  refused while it is that hot.
- **The BIOS gets the fans back when the backend stops**, including after the
  dashboard is closed when OMEN_IDLE_EXIT is set (the desktop launcher sets it).

OMEN_SIMULATE=1 runs everything against an in-memory EC, for trying the
dashboard on any machine; OMEN_FORCE=1 allows writes on unconfirmed models.
"""

import os
import signal
import threading
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

import driver

ALLOWED_HOSTS = {"localhost", "127.0.0.1", "[::1]"}
CSRF_HEADER = "x-omen-linux"
FRONTEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")


def _hostname(host_header):
    """'localhost:8000' -> 'localhost', '[::1]:8000' -> '[::1]'."""
    if host_header.startswith("["):
        return host_header.split("]")[0] + "]"
    return host_header.rsplit(":", 1)[0]


def _env_flag(name):
    return os.environ.get(name, "") == "1"


def _simulated_temps(fan):
    """Temperatures for simulation mode: a busy laptop that runs cooler as the fan speeds up."""

    def read():
        rpm = fan.get_rpm()
        return {"cpu": round(84 - rpm / 200, 1), "gpu": round(70 - rpm / 300, 1)}

    return read


class Safety:
    """Thermal watchdog state, shared by the API and the background thread."""

    def __init__(self, limit):
        self.limit = limit
        self.last_event = None

    def too_hot(self, temps):
        hot = [t for t in temps.values() if t is not None and t >= self.limit]
        return max(hot) if hot else None


def create_app(fan=None, read_temps=driver.read_temps, safe_temp=None, idle_exit=None, watchdog_interval=2.0):
    simulated = fan is None and _env_flag("OMEN_SIMULATE")
    if fan is None:
        ec = driver.FakeEC() if simulated else driver.DevMemEC()
        fan = driver.FanDriver(ec, model="Simulated Victus 16" if simulated else None, force=_env_flag("OMEN_FORCE"))
    if simulated and read_temps is driver.read_temps:
        read_temps = _simulated_temps(fan)
    safety = Safety(float(os.environ.get("OMEN_SAFE_TEMP", "90")) if safe_temp is None else safe_temp)
    idle_exit = int(os.environ.get("OMEN_IDLE_EXIT", "0")) if idle_exit is None else idle_exit
    last_request = [time.monotonic()]
    stop = threading.Event()

    def check_safety():
        """Return control to the BIOS if it is too hot for a reduced fan speed."""
        hot = safety.too_hot(read_temps())
        if hot is None:
            return None
        try:
            state = fan.state()
        except OSError:
            return None
        if state["mode"] != "auto" and (state["target_percent"] or 0) < 100:
            fan.set_auto_mode()
            safety.last_event = {
                "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "message": f"{hot:.0f} C reached with the fan at {state['target_percent']}%: "
                "control returned to the BIOS",
            }
            print(f"Safety: {safety.last_event['message']}")
        return safety.last_event

    def watchdog():
        while not stop.wait(watchdog_interval):
            check_safety()
            if idle_exit and time.monotonic() - last_request[0] > idle_exit:
                print(f"No dashboard requests for {idle_exit}s: restoring BIOS control and exiting")
                os.kill(os.getpid(), signal.SIGINT)
                return

    @asynccontextmanager
    async def lifespan(_app):
        thread = threading.Thread(target=watchdog, daemon=True)
        thread.start()
        yield
        stop.set()
        try:
            fan.set_auto_mode()  # never leave the fans under OS control without the backend
        except OSError as exc:
            print(f"Could not restore BIOS fan control: {exc}")

    app = FastAPI(title="Omen Linux Fan Control", lifespan=lifespan)
    app.state.fan, app.state.safety, app.state.check_safety = fan, safety, check_safety

    @app.middleware("http")
    async def protect(request: Request, call_next):
        if _hostname(request.headers.get("host", "")) not in ALLOWED_HOSTS:
            return JSONResponse({"detail": "Requests must be addressed to localhost"}, status_code=403)
        if request.method not in ("GET", "HEAD", "OPTIONS") and request.headers.get(CSRF_HEADER) != "1":
            return JSONResponse(
                {"detail": "Missing X-Omen-Linux header: requests must come from the dashboard"}, status_code=403
            )
        last_request[0] = time.monotonic()
        return await call_next(request)

    if os.path.isdir(FRONTEND):
        app.mount("/ui", StaticFiles(directory=FRONTEND, html=True), name="ui")

    def hardware(call, *args):
        try:
            return call(*args)
        except driver.UnsupportedHardware as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except OSError as exc:
            raise HTTPException(
                status_code=500, detail=f"Hardware access failed: {exc}. Is the backend running as root?"
            ) from exc

    @app.get("/")
    def root():
        return {"status": "online", "model": fan.model, "confirmed_model": fan.supported, "simulated": simulated}

    @app.get("/status")
    def status():
        temps = read_temps()
        try:
            fan_state, error = fan.state(), None
        except OSError as exc:
            fan_state, error = None, f"Cannot read the EC: {exc}. Is the backend running as root?"
        return {
            "temps": temps,
            "fan": fan_state,
            "error": error,
            "hardware": {"model": fan.model, "confirmed_model": fan.supported, "simulated": simulated},
            "safety": {"limit": safety.limit, "last_event": safety.last_event},
        }

    @app.post("/fan/mode/{mode}")
    def set_mode(mode: str):
        if mode == "auto":
            hardware(fan.set_auto_mode)
        elif mode == "max":
            hardware(fan.set_max_mode)
        elif mode != "manual":  # manual takes effect with the first speed set
            raise HTTPException(status_code=400, detail="Invalid mode. Use 'max', 'auto', or 'manual'.")
        return {"status": "success", "mode": mode}

    @app.post("/fan/speed")
    def set_speed(percentage: int):
        if not 0 <= percentage <= 100:
            raise HTTPException(status_code=400, detail="Speed must be 0-100")
        hot = safety.too_hot(read_temps())
        if hot is not None and percentage < 100:
            raise HTTPException(
                status_code=409,
                detail=f"{hot:.0f} C is above the {safety.limit:.0f} C safety limit: the BIOS keeps control",
            )
        hardware(fan.set_manual_speed, percentage)
        return {"status": "success", "speed": percentage}

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    # Localhost only: this API runs as root and writes to the Embedded Controller.
    uvicorn.run(app, host="127.0.0.1", port=8000)
