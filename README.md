# OMEN LINUX

[![CI](https://github.com/JampaniKomal/omen-linux/actions/workflows/ci.yml/badge.svg)](https://github.com/JampaniKomal/omen-linux/actions/workflows/ci.yml)

**Native Fan Control & Dashboard for HP Victus / Omen Laptops on Linux.**

> **WARNING**: This software writes directly to your laptop's Embedded Controller (EC) memory (`/dev/mem`). Use at your own risk.

![Omen Linux Icon](resources/icon.png)

HP does not ship fan control for its gaming laptops on Linux, and the BIOS
fan curve is often too quiet under load. Omen Linux talks to the Embedded
Controller directly, bypassing the ACPI thermal curves, and gives you a
dashboard with live temperatures and fan speed.

## Features

-   **Desktop App**: Installs as a native application in your system menu.
-   **Brutalist Dashboard**: High-contrast, keyboard-friendly Web UI.
-   **Direct Memory Access**: Bypasses ACPI to talk directly to the EC.
-   **Modes**:
    -   **AUTO**: Hands control back to BIOS default curves.
    -   **MAX**: Forces 100% Fan Speed (~5300 RPM).
    -   **MANUAL**: Granular slider control (0-100%).
-   **Shows what the EC is really doing**: the mode and fan target are read
    back from the EC registers, not remembered by the UI.
-   **Thermal safety**: if the CPU or GPU reaches 90 °C (`OMEN_SAFE_TEMP`)
    while the fan is below full speed, control goes back to the BIOS and the
    dashboard says so; lower speeds are refused while it is that hot.
-   **BIOS control is restored** whenever the backend stops, and the desktop
    launcher stops the backend two minutes after the dashboard is closed.
-   **Simulation mode** (`OMEN_SIMULATE=1`): try the dashboard on any machine
    against an in-memory EC.

## How it works

The EC's registers are memory-mapped at `0xFC7E0000`. Omen Linux maps that
page from `/dev/mem` and uses three registers:

| Offset | Name | Meaning |
|---|---|---|
| `0x80F` | FNSW | bit 3 set: the OS controls the fan; clear: the BIOS does |
| `0x814` | FWPM | fan target written by the OS, `0x00`-`0x35` (`0x35` ≈ 5300 RPM) |
| `0x811` | FRPM | current fan speed, in units of 100 RPM |

Temperatures come from the kernel's hwmon interface (`/sys/class/hwmon`),
which works for AMD (`k10temp`, `amdgpu`) and Intel (`coretemp`) without
`lm-sensors`. A FastAPI backend (running as root, for `/dev/mem`) serves the
API and the dashboard on `http://localhost:8000/ui/`.

## Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/JampaniKomal/omen-linux.git
    cd omen-linux
    ```

2.  **Run the Installer**:
    ```bash
    sudo ./install.sh
    ```

3.  **Launch**:
    Search for **Omen Linux** in your application menu. You are asked for
    your password once (the backend needs root), and the dashboard opens as
    an app window in Chrome/Chromium, or in your default browser.

## Manual Usage (Dev Mode)

If you prefer running from source without installing:
```bash
./scripts/start.sh                      # real hardware (asks for sudo)
OMEN_SIMULATE=1 ./scripts/start.sh      # no hardware: an in-memory EC
```
Then open `http://localhost:8000/ui/`.

| Variable | Default | Effect |
|---|---|---|
| `OMEN_SAFE_TEMP` | `90` | °C at which control returns to the BIOS |
| `OMEN_IDLE_EXIT` | off (launcher: `120`) | seconds without dashboard requests before restoring BIOS control and exiting |
| `OMEN_SIMULATE` | off | use an in-memory EC (and simulated temperatures) |
| `OMEN_FORCE` | off | allow writes on a model that is not confirmed (see below) |

## Hardware Compatibility

Confirmed working on:
-   **HP Victus 16 (Ryzen 7 7840HS)**

Writes are refused unless the DMI product name is a Victus 16, because
another model may keep something else at the same EC addresses. On another
Victus or Omen model, check the registers first, then set `OMEN_FORCE=1`
and report the result. Handing control back to the BIOS (AUTO) is always
allowed.

## Security

The backend runs as root and writes to the EC, so it accepts requests only
from the dashboard on this machine:

-   it listens on `127.0.0.1` only;
-   it rejects any request whose `Host` is not `localhost` or `127.0.0.1`,
    which stops DNS-rebinding attacks (a malicious domain pointed at
    127.0.0.1);
-   every `POST` must carry an `X-Omen-Linux` header. A web page on another
    site can make your browser send a plain POST to localhost, but cannot add
    a custom header without a CORS preflight, which this server never
    approves. Without this, any website you visited while the backend was
    running could have changed your fan speed.

There is still no login: anything already running on this machine as your
user can call the API.

## Tests and CI

15 pytest tests run without root or hardware, against an in-memory EC: the
register writes for each mode (other bits of the control register are
preserved), speed clamping, the model check, hwmon temperature discovery for
AMD and Intel, the API's validation, the `X-Omen-Linux` and `Host` checks, the
thermal watchdog, BIOS control restored on shutdown, and simulation mode. CI
runs ruff, the tests, and ShellCheck on the scripts.

## Known Limitations

-   The EC offsets are confirmed on one model only (see above).
-   `/dev/mem` access to the EC region can be blocked by kernel lockdown
    (Secure Boot with lockdown enabled) or `CONFIG_IO_STRICT_DEVMEM`; the
    dashboard then shows the error.
-   The fan register has 54 steps, so the target you set is rounded (50%
    reads back as 49%).
-   The dashboard loads Vue and Tailwind from public CDNs, so it needs an
    internet connection the first time it opens.

## License

[MIT License](LICENSE)
