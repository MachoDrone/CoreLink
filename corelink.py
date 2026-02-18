#!/usr/bin/env python3
"""
CoreLink - GPU Cluster Communication Framework

Usage:
  python3 corelink.py [options]
  python3 <(curl -sL https://raw.githubusercontent.com/MachoDrone/CoreLink/claude/add-usage-examples-fh9kU/corelink.py) [options]
  python3 <(wget -qO- https://raw.githubusercontent.com/MachoDrone/CoreLink/claude/add-usage-examples-fh9kU/corelink.py) [options]
"""

import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import urllib.error

VERSION = "0.00.3"
CONTAINER_NAME = "corelink"
IMAGE_NAME = "corelink:latest"
REPO_RAW_URL = "https://raw.githubusercontent.com/MachoDrone/CoreLink/claude/add-usage-examples-fh9kU"

CONTAINER_FILES = [
    "container/Dockerfile",
    "container/requirements.txt",
    "container/entrypoint.sh",
    "container/app/server.py",
    "container/app/auth.py",
    "container/app/gossip.py",
    "container/app/gpu.py",
    "container/app/templates/base.html",
    "container/app/templates/login.html",
    "container/app/templates/console.html",
    "container/app/static/css/style.css",
    "container/app/static/js/app.js",
]


def print_banner():
    green = "\033[32m"
    reset = "\033[0m"
    print("")
    print("  %sCoreLink v%s%s" % (green, VERSION, reset))
    print("  GPU Cluster Communication Framework")
    print("  " + "=" * 40)
    sys.stdout.flush()
    time.sleep(3)
    print("")


def run_cmd(cmd, check=True, capture=True, timeout=60):
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=capture,
            text=True, timeout=timeout
        )
        if check and result.returncode != 0:
            return None
        return result
    except subprocess.TimeoutExpired:
        return None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Prerequisite checks
# ---------------------------------------------------------------------------

def check_ubuntu():
    """Verify running Ubuntu 20-24."""
    sys.stdout.write("[*] Checking Ubuntu version... ")
    sys.stdout.flush()

    osrel = "/etc/os-release"
    if not os.path.isfile(osrel):
        print("FAIL - /etc/os-release not found")
        return False

    with open(osrel) as fh:
        content = fh.read()

    if "ubuntu" not in content.lower():
        print("FAIL - Not Ubuntu")
        return False

    match = re.search(r'VERSION_ID="(\d+)', content)
    if not match:
        print("FAIL - Cannot determine version")
        return False

    major = int(match.group(1))
    if major < 20 or major > 24:
        print("FAIL - Ubuntu %d not supported (need 20-24)" % major)
        return False

    print("OK (Ubuntu %d)" % major)
    return True


def check_nvidia_gpu():
    """Check for one or more NVIDIA GPUs via nvidia-smi."""
    sys.stdout.write("[*] Checking NVIDIA GPU... ")
    sys.stdout.flush()

    result = run_cmd("nvidia-smi --query-gpu=name --format=csv,noheader")
    if result is None or result.returncode != 0:
        print("FAIL - nvidia-smi not found or no GPU detected")
        return False

    gpus = [g.strip() for g in result.stdout.strip().split("\n") if g.strip()]
    if not gpus:
        print("FAIL - No NVIDIA GPUs found")
        return False

    print("OK (%d GPU(s): %s)" % (len(gpus), ", ".join(gpus)))
    return True


def check_nvidia_container_toolkit():
    """Check for NVIDIA Container Toolkit."""
    sys.stdout.write("[*] Checking NVIDIA Container Toolkit... ")
    sys.stdout.flush()

    if shutil.which("nvidia-ctk"):
        print("OK (nvidia-ctk found)")
        return True

    if shutil.which("nvidia-container-runtime"):
        print("OK (nvidia-container-runtime found)")
        return True

    # Check Docker daemon config for nvidia runtime
    daemon_cfg = "/etc/docker/daemon.json"
    if os.path.isfile(daemon_cfg):
        with open(daemon_cfg) as fh:
            if "nvidia" in fh.read():
                print("OK (nvidia runtime in daemon.json)")
                return True

    print("FAIL - NVIDIA Container Toolkit not found")
    return False


def check_docker():
    """Check Docker is installed and accessible."""
    sys.stdout.write("[*] Checking Docker... ")
    sys.stdout.flush()

    result = run_cmd("docker --version")
    if result is None or result.returncode != 0:
        print("FAIL - Docker not found")
        return False

    version_str = result.stdout.strip()
    print("OK (%s)" % version_str)

    result = run_cmd("docker info", check=False)
    if result is None or result.returncode != 0:
        print("  [!] Cannot connect to Docker daemon.")
        print("      Try: sudo usermod -aG docker $USER  (then re-login)")
        print("      Or run this script with sudo.")
        return False

    return True


def check_prerequisites():
    """Run all prerequisite checks. Return True if all pass."""
    print("Checking prerequisites...\n")

    results = [
        check_ubuntu(),
        check_nvidia_gpu(),
        check_nvidia_container_toolkit(),
        check_docker(),
    ]

    if all(results):
        print("\n[OK] All prerequisites met.\n")
        return True
    else:
        print("\n[FAIL] Some prerequisites are missing. Install them and retry.\n")
        return False


# ---------------------------------------------------------------------------
# Container file management
# ---------------------------------------------------------------------------

def find_container_dir():
    """Locate the container/ build directory locally."""
    candidates = [
        os.path.join(os.getcwd(), "container"),
    ]

    try:
        script_path = os.path.realpath(__file__)
        if not script_path.startswith("/dev/") and not script_path.startswith("/proc/"):
            script_dir = os.path.dirname(script_path)
            candidates.append(os.path.join(script_dir, "container"))
    except Exception:
        pass

    for path in candidates:
        dockerfile = os.path.join(path, "Dockerfile")
        if os.path.isdir(path) and os.path.isfile(dockerfile):
            return path

    return None


def download_container_files():
    """Download container build files from GitHub into a temp directory."""
    print("[*] Downloading container files from GitHub...")

    build_dir = tempfile.mkdtemp(prefix="corelink-build-")

    for rel_path in CONTAINER_FILES:
        url = "%s/%s" % (REPO_RAW_URL, rel_path)
        dest = os.path.join(build_dir, rel_path)
        os.makedirs(os.path.dirname(dest), exist_ok=True)

        try:
            urllib.request.urlretrieve(url, dest)
        except urllib.error.URLError as exc:
            print("  [!] Failed to download %s: %s" % (rel_path, exc))
            shutil.rmtree(build_dir, ignore_errors=True)
            return None

    # Make entrypoint executable
    entrypoint = os.path.join(build_dir, "container", "entrypoint.sh")
    if os.path.isfile(entrypoint):
        os.chmod(entrypoint, 0o755)

    print("  Downloaded %d files to %s" % (len(CONTAINER_FILES), build_dir))
    return os.path.join(build_dir, "container")


# ---------------------------------------------------------------------------
# Docker operations
# ---------------------------------------------------------------------------

def build_image(container_dir):
    """Build the Docker image from the container directory."""
    print("[*] Building Docker image '%s' ..." % IMAGE_NAME)

    result = subprocess.run(
        ["docker", "build", "-t", IMAGE_NAME, container_dir],
        timeout=600,
    )

    if result.returncode != 0:
        print("[FAIL] Docker build failed.")
        return False

    print("[OK] Image '%s' built successfully.\n" % IMAGE_NAME)
    return True


def image_exists():
    """Return True if the corelink Docker image already exists."""
    result = run_cmd("docker images -q %s" % IMAGE_NAME)
    return result is not None and result.stdout.strip() != ""


def start_container(port=443):
    """Start the CoreLink container."""
    # Already running?
    result = run_cmd("docker ps -q -f name=^/%s$" % CONTAINER_NAME)
    if result and result.stdout.strip():
        print("[!] Container '%s' is already running." % CONTAINER_NAME)
        print("    Use --stop first, or --restart.")
        return False

    # Remove stopped container with the same name
    run_cmd("docker rm %s" % CONTAINER_NAME, check=False)

    hostname = platform.node()

    cmd = [
        "docker", "run", "-d",
        "--name", CONTAINER_NAME,
        "--gpus", "all",
        "--network", "host",
        "-v", "/etc/passwd:/etc/passwd:ro",
        "-v", "/etc/shadow:/etc/shadow:ro",
        "-v", "/etc/pam.d:/etc/pam.d:ro",
        "-v", "corelink-data:/data",
        "-e", "CORELINK_PORT=%d" % port,
        "-e", "CORELINK_HOSTNAME=%s" % hostname,
        "--restart", "unless-stopped",
        IMAGE_NAME,
    ]

    print("[*] Starting container '%s' on port %d ..." % (CONTAINER_NAME, port))
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print("[FAIL] %s" % result.stderr.strip())
        return False

    print("[OK] Container '%s' started." % CONTAINER_NAME)
    print("    Web console: https://%s:%d" % (hostname, port))
    print("    (Self-signed certificate - accept the browser warning)")
    return True


def stop_container():
    """Stop and remove the CoreLink container."""
    print("[*] Stopping container '%s' ..." % CONTAINER_NAME)
    result = run_cmd("docker stop %s" % CONTAINER_NAME, timeout=30)
    if result and result.returncode == 0:
        run_cmd("docker rm %s" % CONTAINER_NAME, check=False)
        print("[OK] Container stopped and removed.")
        return True

    print("[!] Container not running or not found.")
    return False


def show_status():
    """Print the container's current status."""
    fmt = "table {{.Names}}\\t{{.Status}}\\t{{.Image}}"
    result = run_cmd(
        "docker ps -a -f name=^/%s$ --format '%s'" % (CONTAINER_NAME, fmt)
    )
    if result and result.stdout.strip():
        print(result.stdout.strip())
    else:
        print("Container '%s' does not exist." % CONTAINER_NAME)


def show_logs(follow=False):
    """Stream or print container logs."""
    cmd = "docker logs %s" % CONTAINER_NAME
    if follow:
        cmd += " -f"
    os.system(cmd)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="CoreLink v%s - GPU Cluster Communication Framework" % VERSION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  %(prog)s --check            Check prerequisites only
  %(prog)s --build            Build the Docker image
  %(prog)s --start            Build (if needed) and start CoreLink
  %(prog)s --stop             Stop CoreLink
  %(prog)s --restart          Restart CoreLink
  %(prog)s --status           Show container status
  %(prog)s --logs             Show container logs
  %(prog)s --start --port 8443  Start on a custom port

Remote one-liner:
  python3 <(curl -sL https://raw.githubusercontent.com/MachoDrone/CoreLink/claude/add-usage-examples-fh9kU/corelink.py) --start
""",
    )

    parser.add_argument("--check", action="store_true",
                        help="Check prerequisites only")
    parser.add_argument("--build", action="store_true",
                        help="Build the Docker image")
    parser.add_argument("--start", action="store_true",
                        help="Build if needed and start CoreLink")
    parser.add_argument("--stop", action="store_true",
                        help="Stop CoreLink")
    parser.add_argument("--restart", action="store_true",
                        help="Restart CoreLink")
    parser.add_argument("--status", action="store_true",
                        help="Show container status")
    parser.add_argument("--logs", action="store_true",
                        help="Show container logs")
    parser.add_argument("--logs-follow", action="store_true",
                        help="Follow container logs (live)")
    parser.add_argument("--port", type=int, default=443,
                        help="HTTPS port (default: 443)")
    parser.add_argument("--version", action="version",
                        version="CoreLink v%s" % VERSION)

    args = parser.parse_args()
    print_banner()

    # If no action flag given, print help
    action_flags = [
        args.check, args.build, args.start, args.stop,
        args.restart, args.status, args.logs, args.logs_follow,
    ]
    if not any(action_flags):
        parser.print_help()
        return 0

    # Quick actions that don't need prereq checks
    if args.status:
        show_status()
        return 0

    if args.logs or args.logs_follow:
        show_logs(follow=args.logs_follow)
        return 0

    if args.stop:
        stop_container()
        return 0

    if args.restart:
        stop_container()
        args.start = True

    # Actions that need prereq checks
    if args.check or args.build or args.start:
        if not check_prerequisites():
            return 1

    if args.check:
        return 0

    # Build image if requested or if image doesn't exist and we're starting
    if args.build or args.start:
        need_build = args.build or not image_exists()

        if need_build:
            container_dir = find_container_dir()
            if container_dir is None:
                container_dir = download_container_files()
                if container_dir is None:
                    print("[FAIL] Cannot find or download container files.")
                    return 1

            if not build_image(container_dir):
                return 1

    if args.start:
        if not start_container(port=args.port):
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
