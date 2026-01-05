# OMEN LINUX

**Experimental Fan Control & Dashboard for HP Victus / Omen Laptops on Linux.**

> **WARNING**: This software writes directly to your laptop's Embedded Controller (EC) memory (`/dev/mem`). While tested on HP Victus (Ryzen 7 7840HS), incorrect usage on unsupported hardware could cause system instability. Use at your own risk.

## Features

-   **Brutalist Dashboard**: High-contrast, keyboard-friendly Web UI.
-   **Direct Memory Access (DMA)**: Bypasses limited ACPI tables to talk directly to the hardware.
-   **Modes**:
    -   **AUTO**: DEFAULT. Hands control back to the BIOS.
    -   **MAX**: Forces 100% Fan Speed (~5300 RPM).
    -   **MANUAL**: Slider control (0-100%).
-   **Real-Time Monitoring**: CPU Temp, GPU Temp, and **True Fan RPM**.

## Requirements

-   Linux Kernel (Tested on 6.x+)
-   Python 3.10+
-   `lm-sensors` (for temperature readings)
-   Root privileges (for physical memory access)

## Installation

1.  **Clone this repository**:
    ```bash
    git clone https://github.com/your-username/omen-linux.git
    cd omen-linux
    ```

2.  **Run the launcher**:
    ```bash
    chmod +x start.sh
    ./start.sh
    ```
    *Note: The script will automatically create a virtual environment (`venv`) and install dependencies on the first run.*

3.  **Access the Dashboard**:
    Open [http://localhost:8000/ui/](http://localhost:8000/ui/) in your browser.

## Troubleshooting

-   **"Operation not permitted"**: Ensure you run the script with `sudo` (or enter password when prompted).
-   **Zero Temperatures**: Install `lm-sensors` (`sudo apt install lm-sensors && sudo sensors-detect`).
-   **Fans stuck?**: Click "AUTO" in the dashboard. If that fails, a full reboot resets the EC state.

## Hardware Details

Fan control is achieved by mapping the EC memory region (`0xFC7E0000`).
-   **Manual Mode Switch**: Offset `0x80F` (Bit 3)
-   **Fan Speed Write**: Offset `0x814`
-   **Fan RPM Read**: Offset `0x811`

## License

MIT License.
