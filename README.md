# OMEN LINUX

**Native Fan Control & Dashboard for HP Victus / Omen Laptops on Linux.**

> **WARNING**: This software writes directly to your laptop's Embedded Controller (EC) memory (`/dev/mem`). Use at your own risk.

![Omen Linux Icon](resources/icon.png)

## Features

-   **Desktop App**: Installs as a native application in your system menu.
-   **Brutalist Dashboard**: High-contrast, keyboard-friendly Web UI.
-   **Direct Memory Access (DMA)**: Bypasses ACPI to talk directly to hardware.
-   **Modes**:
    -   **AUTO**: Hands control back to BIOS default curves.
    -   **MAX**: Forces 100% Fan Speed (~5300 RPM).
    -   **MANUAL**: Granular slider control (0-100%).

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
    Search for **Omen Linux** in your application menu.

## Manual Usage (Dev Mode)

If you prefer running from source without installing:
```bash
cd scripts
./start.sh
```

## Hardware Compatibility

Confirmed working on:
-   **HP Victus 16 (Ryzen 7 7840HS)**

*Note: Requires `lm-sensors` for temperature monitoring.*

## Security Note

The backend runs as root (required for `/dev/mem` access) and is bound to
`127.0.0.1` only — the dashboard is only ever reached at
`http://localhost:8000/ui/`, and there is no legitimate reason for this API
to be reachable from the network. An earlier version bound to `0.0.0.0`
with permissive CORS enabled, which would have let any device on the same
network send unauthenticated requests to write directly to this laptop's
Embedded Controller memory. If you're running an older checkout, update to
get this fix.

## Known Limitations

-   No authentication on the API - acceptable only because it's bound to
    localhost; do not change the bind address without adding auth first.
-   Hardware failures (not running as root, wrong EC register layout on an
    unconfirmed laptop model) return a clean `500` with a message rather
    than crashing, but there's no retry or reconnect logic.
-   `driver.py`'s EC offsets (`OFF_CTRL`, `OFF_PWM`, `OFF_RPM`, `EC_BASE`)
    are specific to the confirmed hardware above; a different Victus/Omen
    model may use different offsets and could behave unpredictably.
-   No automated test suite for the hardware-access layer itself (Linux
    `/dev/mem` access can't be tested outside real target hardware); the
    FastAPI routing/validation logic was tested with FastAPI's `TestClient`.

## Testing & Verification

The FastAPI app's routing and validation logic was tested directly with
`TestClient` (hardware access itself needs real Linux + real EC hardware
to test, which isn't available in every environment): confirmed the status
endpoint degrades gracefully when hardware access fails, invalid mode/speed
values return `400`, and a hardware-access failure on `/fan/mode/*` and
`/fan/speed` now returns a clean `500` with a helpful message instead of an
unhandled crash.

## License

[MIT License](LICENSE)
