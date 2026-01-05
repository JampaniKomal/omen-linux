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

## License

[MIT License](LICENSE)
