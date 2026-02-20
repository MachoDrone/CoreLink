"""CoreLink - GPU discovery via nvidia-smi + sysfs PCIe bottleneck detection."""

import os
import subprocess


# Map PCIe link speed (GT/s) to generation number.
_SPEED_TO_GEN = {"2.5": 1, "5": 2, "8": 3, "16": 4, "32": 5, "64": 6}


def _parse_link_speed(text):
    """Extract GT/s number from sysfs string like '16.0 GT/s PCIe'."""
    try:
        gts = text.strip().split()[0]          # "16.0"
        gts_key = gts.rstrip("0").rstrip(".")  # "16"
        return _SPEED_TO_GEN.get(gts_key, 0)
    except (IndexError, ValueError):
        return 0


def _read_sysfs(path):
    """Read a sysfs file, return stripped content or empty string."""
    try:
        with open(path) as f:
            return f.read().strip()
    except (IOError, OSError):
        return ""


def _pcie_bottleneck(bus_id):
    """Return (gen, width) considering both GPU and slot capabilities.

    bus_id: PCI address in sysfs format, e.g. '0000:05:00.0'.
    """
    dev_path = "/sys/bus/pci/devices/%s" % bus_id

    # GPU capability
    gpu_gen = _parse_link_speed(_read_sysfs(dev_path + "/max_link_speed"))
    try:
        gpu_width = int(_read_sysfs(dev_path + "/max_link_width"))
    except (ValueError, TypeError):
        gpu_width = 0

    # Parent (slot) capability
    try:
        real_path = os.path.realpath(dev_path)
        parent_id = os.path.basename(os.path.dirname(real_path))
        parent_path = "/sys/bus/pci/devices/%s" % parent_id
        slot_gen = _parse_link_speed(_read_sysfs(parent_path + "/max_link_speed"))
        try:
            slot_width = int(_read_sysfs(parent_path + "/max_link_width"))
        except (ValueError, TypeError):
            slot_width = 0
    except (OSError, ValueError):
        slot_gen, slot_width = 0, 0

    # Take the minimum (bottleneck)
    eff_gen = min(gpu_gen, slot_gen) if slot_gen > 0 else gpu_gen
    eff_width = min(gpu_width, slot_width) if slot_width > 0 else gpu_width
    return eff_gen, eff_width


def get_local_gpu_info():
    """Query nvidia-smi for locally installed NVIDIA GPUs.

    Returns a list of dicts:
      [{"id": 0, "model": "RTX A6000", "limit": "4.0 x 16"}, ...]

    The 'limit' field reflects the PCIe bottleneck — the minimum of the
    GPU's own capability and the motherboard slot capability.
    """
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=index,name,pci.bus_id",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return []

        gpus = []
        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split(", ")]
            try:
                idx = int(parts[0])
                model = parts[1].replace("NVIDIA ", "", 1) if len(parts) > 1 else "Unknown"
                # nvidia-smi gives "00000000:05:00.0", sysfs uses "0000:05:00.0"
                raw_bus = parts[2] if len(parts) > 2 else ""
                bus_id = raw_bus.replace("00000000:", "0000:", 1) if raw_bus.startswith("00000000:") else raw_bus
                gen, width = _pcie_bottleneck(bus_id)
                limit = "%s.0 x %s" % (gen, width) if gen > 0 else "0.0 x 0"
            except (ValueError, IndexError):
                idx = 0
                model = "Unknown"
                limit = "0.0 x 0"
            gpus.append({"id": idx, "model": model, "limit": limit})
        return gpus

    except Exception:
        return []
