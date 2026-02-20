"""CoreLink - GPU discovery via nvidia-smi."""

import subprocess


def get_local_gpu_info():
    """Query nvidia-smi for locally installed NVIDIA GPUs.

    Returns a list of dicts:
      [{"id": 0, "model": "RTX A6000", "limit": "4.0 x 16"}, ...]
    """
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=index,name,pcie.link.gen.max,pcie.link.width.max",
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
                pcie_gen = parts[2] if len(parts) > 2 else "0"
                pcie_width = parts[3] if len(parts) > 3 else "0"
                limit = "%s.0 x %s" % (int(pcie_gen), int(pcie_width))
            except (ValueError, IndexError):
                limit = "0.0 x 0"
            gpus.append({
                "id": int(parts[0]),
                "model": parts[1].replace("NVIDIA ", "", 1) if len(parts) > 1 else "Unknown",
                "limit": limit,
            })
        return gpus

    except Exception:
        return []
