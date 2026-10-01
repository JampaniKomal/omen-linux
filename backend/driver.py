"""Fan control for HP Victus / Omen laptops through Embedded Controller memory.

The EC's registers are memory-mapped at EC_BASE. Three of them matter:

- OFF_CTRL (FNSW): bit 3 set = the OS controls the fan; clear = the BIOS does;
- OFF_PWM  (FWPM): the fan target the OS writes, 0x00-0x35 (0x35 ~ 5300 RPM);
- OFF_RPM  (FRPM): the current fan speed in units of 100 RPM.

These offsets were found on an HP Victus 16 (Ryzen 7 7840HS). Other models may
put different things at the same addresses, so writes are refused unless the
laptop is a Victus 16 (by its DMI product name) or OMEN_FORCE=1 is set.
"""

import mmap
import os
import struct
from pathlib import Path

EC_BASE = 0xFC7E0000
EC_SIZE = 4096
OFF_CTRL = 0x80F
OFF_PWM = 0x814
OFF_RPM = 0x811
OS_CONTROL_BIT = 0x08
MAX_PWM = 0x35  # ~5300 RPM


def is_confirmed_model(name):
    """The register layout has been confirmed on the Victus 16 family only."""
    return "victus" in name.lower() and "16" in name


CPU_SENSORS = ("k10temp", "coretemp", "zenpower")  # AMD, Intel, AMD (out-of-tree)
GPU_SENSORS = ("amdgpu", "nouveau", "radeon")


class UnsupportedHardware(RuntimeError):
    pass


class DevMemEC:
    """The real EC, mapped from /dev/mem (needs root)."""

    def __init__(self, base=EC_BASE, size=EC_SIZE):
        self.base, self.size = base, size
        self.mm = None

    def _map(self):
        if self.mm is None:
            fd = os.open("/dev/mem", os.O_RDWR | os.O_SYNC)
            try:
                self.mm = mmap.mmap(fd, self.size, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE, offset=self.base)
            finally:
                os.close(fd)  # the mapping stays valid after the descriptor is closed
        return self.mm

    def read(self, offset):
        return struct.unpack_from("B", self._map(), offset)[0]

    def write(self, offset, value):
        struct.pack_into("B", self._map(), offset, value & 0xFF)


class FakeEC:
    """In-memory EC for simulation (OMEN_SIMULATE=1) and tests. The fan follows the target."""

    def __init__(self):
        self.mem = bytearray(EC_SIZE)
        self.mem[OFF_RPM] = 0x1E  # 3000 RPM under BIOS control

    def read(self, offset):
        if offset == OFF_RPM and self.mem[OFF_CTRL] & OS_CONTROL_BIT:
            return self.mem[OFF_PWM]
        return self.mem[offset]

    def write(self, offset, value):
        self.mem[offset] = value & 0xFF


def product_name(dmi=Path("/sys/class/dmi/id/product_name")):
    try:
        return dmi.read_text().strip()
    except OSError:
        return ""


def read_temps(hwmon=Path("/sys/class/hwmon")):
    """CPU and GPU temperatures in degrees C from the kernel's hwmon interface (no lm-sensors needed)."""
    temps = {"cpu": None, "gpu": None}
    for device in sorted(hwmon.glob("hwmon*")):
        try:
            name = (device / "name").read_text().strip()
        except OSError:
            continue
        kind = "cpu" if name in CPU_SENSORS else "gpu" if name in GPU_SENSORS else None
        if kind is None or temps[kind] is not None:
            continue
        readings = {}
        for sensor in sorted(device.glob("temp*_input")):
            label_file = device / sensor.name.replace("_input", "_label")
            label = label_file.read_text().strip() if label_file.exists() else sensor.name
            try:
                readings[label] = int(sensor.read_text().strip()) / 1000
            except (OSError, ValueError):
                continue
        # prefer the package/control temperature over per-core or edge readings
        for preferred in ("Tctl", "Tdie", "Package id 0", "edge", "temp1_input"):
            if preferred in readings:
                temps[kind] = readings[preferred]
                break
        else:
            if readings:
                temps[kind] = max(readings.values())
    return temps


class FanDriver:
    def __init__(self, ec=None, model=None, force=False):
        self.ec = ec or DevMemEC()
        self.model = product_name() if model is None else model
        self.force = force

    @property
    def supported(self):
        return is_confirmed_model(self.model)

    def _check(self):
        if not (self.supported or self.force):
            raise UnsupportedHardware(
                f"'{self.model or 'unknown model'}' is not a confirmed model (Victus 16); "
                "its EC may use other registers. Set OMEN_FORCE=1 to write anyway."
            )

    def get_rpm(self):
        return self.ec.read(OFF_RPM) * 100

    def state(self):
        """What the EC is doing now: who controls the fan, and the OS target as a percentage."""
        os_control = bool(self.ec.read(OFF_CTRL) & OS_CONTROL_BIT)
        target = round(self.ec.read(OFF_PWM) * 100 / MAX_PWM) if os_control else None
        if not os_control:
            mode = "auto"
        elif target is not None and target >= 100:
            mode = "max"
        else:
            mode = "manual"
        return {"mode": mode, "target_percent": target, "rpm": self.get_rpm()}

    def _take_control(self, pwm):
        self._check()
        ctrl = self.ec.read(OFF_CTRL)
        self.ec.write(OFF_PWM, pwm)  # set the target first, so the fan never briefly runs at a stale value
        self.ec.write(OFF_CTRL, ctrl | OS_CONTROL_BIT)

    def set_max_mode(self):
        self._take_control(MAX_PWM)

    def set_manual_speed(self, percentage):
        percentage = max(0, min(100, int(percentage)))
        self._take_control(round(percentage * MAX_PWM / 100))
        return percentage

    def set_auto_mode(self):
        # Handing control back to the BIOS is always allowed: it is the safe state.
        ctrl = self.ec.read(OFF_CTRL)
        self.ec.write(OFF_CTRL, ctrl & ~OS_CONTROL_BIT)
