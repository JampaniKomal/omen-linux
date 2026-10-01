"""The driver's register logic, temperature discovery, and the API's safety and security rules.

The EC is replaced by driver.FakeEC (the same registers in memory), so none of
this needs root, /dev/mem or an HP laptop.
"""

import pytest
from fastapi.testclient import TestClient

import driver
from main import create_app

HEADERS = {"X-Omen-Linux": "1"}


@pytest.fixture
def ec():
    return driver.FakeEC()


@pytest.fixture
def fan(ec):
    return driver.FanDriver(ec, model="Victus by HP Gaming Laptop 16-s0xxx")


class Temps:
    def __init__(self, cpu=55.0, gpu=50.0):
        self.value = {"cpu": cpu, "gpu": gpu}

    def __call__(self):
        return dict(self.value)


@pytest.fixture
def temps():
    return Temps()


@pytest.fixture
def client(fan, temps):
    app = create_app(fan=fan, read_temps=temps, safe_temp=90, idle_exit=0, watchdog_interval=3600)
    with TestClient(app, base_url="http://localhost:8000") as c:
        yield c


# --- driver ---------------------------------------------------------------------


def test_modes_set_the_documented_registers(fan, ec):
    ec.mem[driver.OFF_CTRL] = 0b0100_0001  # other bits in the control register must survive
    assert fan.state()["mode"] == "auto"
    fan.set_manual_speed(50)
    assert ec.mem[driver.OFF_CTRL] == 0b0100_1001 and ec.mem[driver.OFF_PWM] == round(0.5 * driver.MAX_PWM)
    state = fan.state()  # the register has 54 steps (0x00-0x35), so 50% reads back as 49%
    assert state["mode"] == "manual" and abs(state["target_percent"] - 50) <= 1
    assert state["rpm"] == ec.mem[driver.OFF_PWM] * 100  # the simulated fan follows the target
    fan.set_max_mode()
    assert ec.mem[driver.OFF_PWM] == driver.MAX_PWM and fan.state()["mode"] == "max"
    fan.set_auto_mode()
    assert ec.mem[driver.OFF_CTRL] == 0b0100_0001 and fan.state()["target_percent"] is None


def test_speed_is_clamped(fan, ec):
    assert fan.set_manual_speed(150) == 100 and ec.mem[driver.OFF_PWM] == driver.MAX_PWM
    assert fan.set_manual_speed(-5) == 0 and ec.mem[driver.OFF_PWM] == 0


def test_writes_are_refused_on_unconfirmed_models(ec):
    other = driver.FanDriver(ec, model="OMEN by HP Laptop 17-ck0xxx")
    with pytest.raises(driver.UnsupportedHardware):
        other.set_max_mode()
    assert ec.mem[driver.OFF_CTRL] == 0  # nothing was written
    other.set_auto_mode()  # returning control to the BIOS is always allowed
    driver.FanDriver(ec, model="OMEN by HP Laptop 17-ck0xxx", force=True).set_max_mode()
    assert ec.mem[driver.OFF_PWM] == driver.MAX_PWM


def test_temperatures_come_from_hwmon_for_amd_and_intel(tmp_path):
    def chip(n, name, sensors):
        d = tmp_path / f"hwmon{n}"
        d.mkdir()
        (d / "name").write_text(name + "\n")
        for i, (label, milli) in enumerate(sensors, 1):
            (d / f"temp{i}_input").write_text(f"{milli}\n")
            if label:
                (d / f"temp{i}_label").write_text(label + "\n")

    chip(0, "nvme", [("Composite", 41000)])
    chip(1, "k10temp", [("Tctl", 67250), ("Tccd1", 60000)])
    chip(2, "amdgpu", [("edge", 52000), ("junction", 58000)])
    assert driver.read_temps(tmp_path) == {"cpu": 67.25, "gpu": 52.0}

    intel = tmp_path / "intel"
    intel.mkdir()
    (intel / "hwmon0").mkdir()
    (intel / "hwmon0" / "name").write_text("coretemp\n")
    (intel / "hwmon0" / "temp1_input").write_text("71000\n")
    (intel / "hwmon0" / "temp1_label").write_text("Package id 0\n")
    assert driver.read_temps(intel) == {"cpu": 71.0, "gpu": None}


def test_confirmed_model_family():
    assert driver.is_confirmed_model("Victus by HP Gaming Laptop 16-s0xxx")
    assert not driver.is_confirmed_model("Victus by HP Laptop 15-fa0xxx")
    assert not driver.is_confirmed_model("")


# --- API ----------------------------------------------------------------------------


def test_status_reports_what_the_ec_is_doing(client, fan):
    fan.set_manual_speed(30)
    data = client.get("/status").json()
    assert data["fan"]["mode"] == "manual" and data["fan"]["target_percent"] == 30
    assert data["temps"] == {"cpu": 55.0, "gpu": 50.0}
    assert data["hardware"]["confirmed_model"] is True and data["safety"]["limit"] == 90


def test_posts_without_the_dashboard_header_are_refused(client, ec):
    """A page on another site can send a plain POST to localhost, but cannot add this header."""
    r = client.post("/fan/mode/max")
    assert r.status_code == 403 and ec.mem[driver.OFF_PWM] == 0
    assert client.post("/fan/speed?percentage=10").status_code == 403
    assert client.post("/fan/mode/max", headers=HEADERS).status_code == 200


def test_requests_for_other_host_names_are_refused(fan, temps):
    """DNS rebinding: an attacker's domain that resolves to 127.0.0.1 still sends its own Host."""
    app = create_app(fan=fan, read_temps=temps, safe_temp=90, idle_exit=0, watchdog_interval=3600)
    with TestClient(app, base_url="http://attacker.example:8000") as c:
        assert c.get("/status").status_code == 403
        assert c.post("/fan/mode/max", headers=HEADERS).status_code == 403
    with TestClient(app, base_url="http://127.0.0.1:8000") as c:
        assert c.get("/status").status_code == 200


def test_mode_and_speed_validation(client):
    assert client.post("/fan/mode/turbo", headers=HEADERS).status_code == 400
    assert client.post("/fan/speed?percentage=101", headers=HEADERS).status_code == 400
    assert client.post("/fan/speed?percentage=40", headers=HEADERS).json() == {"status": "success", "speed": 40}


def test_unconfirmed_model_returns_409(temps):
    fan = driver.FanDriver(driver.FakeEC(), model="Some Other Laptop")
    app = create_app(fan=fan, read_temps=temps, safe_temp=90, idle_exit=0, watchdog_interval=3600)
    with TestClient(app, base_url="http://localhost") as c:
        r = c.post("/fan/mode/max", headers=HEADERS)
        assert r.status_code == 409 and "OMEN_FORCE" in r.json()["detail"]
        assert c.post("/fan/mode/auto", headers=HEADERS).status_code == 200


def test_watchdog_returns_control_to_the_bios_when_hot(client, fan, temps):
    fan.set_manual_speed(20)
    temps.value["cpu"] = 93.0
    event = client.app.state.check_safety()
    assert fan.state()["mode"] == "auto" and "93 C" in event["message"]
    assert client.get("/status").json()["safety"]["last_event"] == event
    # and lower speeds are refused while it is that hot; full speed is still allowed
    assert client.post("/fan/speed?percentage=30", headers=HEADERS).status_code == 409
    assert client.post("/fan/speed?percentage=100", headers=HEADERS).status_code == 200


def test_watchdog_leaves_full_speed_and_bios_control_alone(client, fan, temps):
    temps.value["gpu"] = 95.0
    fan.set_max_mode()
    assert client.app.state.check_safety() is None and fan.state()["mode"] == "max"


def test_shutdown_gives_control_back_to_the_bios(fan, temps):
    app = create_app(fan=fan, read_temps=temps, safe_temp=90, idle_exit=0, watchdog_interval=3600)
    with TestClient(app, base_url="http://localhost") as c:
        c.post("/fan/speed?percentage=10", headers=HEADERS)
        assert fan.state()["mode"] == "manual"
    assert fan.state()["mode"] == "auto"


def test_dashboard_is_served(client):
    page = client.get("/ui/")
    assert page.status_code == 200 and "X-Omen-Linux" in page.text


def test_simulation_mode_needs_no_hardware(monkeypatch):
    monkeypatch.setenv("OMEN_SIMULATE", "1")
    app = create_app(safe_temp=90, idle_exit=0, watchdog_interval=3600)
    with TestClient(app, base_url="http://localhost") as c:
        before = c.get("/status").json()
        assert before["hardware"]["simulated"] and before["fan"]["mode"] == "auto"
        assert c.post("/fan/mode/max", headers=HEADERS).status_code == 200
        after = c.get("/status").json()
        assert after["fan"]["rpm"] == driver.MAX_PWM * 100 and after["temps"]["cpu"] < before["temps"]["cpu"]
