"""CoreLink - GPU discovery via nvidia-smi."""

import subprocess


def get_local_gpu_info():
    """Query nvidia-smi for locally installed NVIDIA GPUs.

    Returns a list of dicts:  [{"id": 0, "model": "RTX A6000"}, ...]
    """
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=index,name",
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
            parts = line.split(", ", 1)
            gpus.append({
                "id": int(parts[0].strip()),
                "model": parts[1].strip() if len(parts) > 1 else "Unknown",
            })
        return gpus

    except Exception:
        return []
