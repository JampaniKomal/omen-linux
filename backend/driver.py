import mmap
import os
import struct
import time

class FanDriver:
    def __init__(self):
        self.EC_BASE = 0xFC7E0000
        self.EC_SIZE = 4096
        
        # Offsets relative to EC_BASE
        self.OFF_CTRL = 0x80F  # FNSW is Bit 3
        self.OFF_PWM  = 0x814  # FWPM Speed (Write)
        self.OFF_RPM  = 0x811  # FRPM RPM (Read)
        
        # Constants
        self.MAX_RPM_VAL = 0x35 # ~5300 RPM
        
        self.fd = None
        self.mm = None

    def _open_mem(self):
        if self.mm is not None: return
        try:
            self.fd = os.open("/dev/mem", os.O_RDWR | os.O_SYNC)
            self.mm = mmap.mmap(self.fd, self.EC_SIZE, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE, offset=self.EC_BASE)
        except Exception as e:
            print(f"Error accessing /dev/mem: {e}")
            raise

    def _close_mem(self):
        pass

    def _read_u8(self, offset):
        self._open_mem()
        self.mm.seek(offset)
        return struct.unpack('B', self.mm.read(1))[0]

    def _write_u8(self, offset, val):
        self._open_mem()
        self.mm.seek(offset)
        self.mm.write(struct.pack('B', val))

    def get_temps(self):
        import subprocess
        try:
            output = subprocess.check_output(["sensors", "-j"]).decode()
            import json
            data = json.loads(output)
            
            cpu = 0
            if "k10temp-pci-00c3" in data:
                cpu = data["k10temp-pci-00c3"].get("Tctl", {}).get("temp1_input", 0)
            
            gpu = 0
            if "amdgpu-pci-0500" in data:
                gpu = data["amdgpu-pci-0500"].get("edge", {}).get("temp1_input", 0)
                
            return {"cpu": cpu, "gpu": gpu}
        except:
            return {"cpu": 0, "gpu": 0}

    def get_rpm(self):
        try:
            val = self._read_u8(self.OFF_RPM)
            return val * 100
        except:
            return 0

    def set_max_mode(self):
        print("Driver: Setting MAX Mode")
        ctrl = self._read_u8(self.OFF_CTRL)
        self._write_u8(self.OFF_CTRL, ctrl | 0x08)
        self._write_u8(self.OFF_PWM, self.MAX_RPM_VAL)
        return True

    def set_auto_mode(self):
        print("Driver: Setting AUTO Mode")
        ctrl = self._read_u8(self.OFF_CTRL)
        self._write_u8(self.OFF_CTRL, ctrl & ~0x08)
        return True

    def set_manual_speed(self, percentage: int):
        if percentage < 0: percentage = 0
        if percentage > 100: percentage = 100
        
        target_val = int(percentage * 0x35 / 100)
        
        print(f"Driver: Setting Speed {percentage}% (Reg: 0x{target_val:02X})")
        
        ctrl = self._read_u8(self.OFF_CTRL)
        self._write_u8(self.OFF_CTRL, ctrl | 0x08)
        self._write_u8(self.OFF_PWM, target_val)
        return True
