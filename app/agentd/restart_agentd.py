#!/usr/bin/env python3
"""
AI Agent Service Restart Script

Restarts the agentd service by:
1. Stopping any running python app.py processes
2. Force releasing port 10443 if in use
3. Starting the service using the virtual environment
4. Verifying the service is healthy (health endpoint + process status)
5. Showing detailed service status

Usage:
    python restart_agentd.py              # Normal restart with verification
    python restart_agentd.py --force       # Force kill processes using port 10443
    python restart_agentd.py --no-verify   # Skip verification (faster)
    python restart_agentd.py --status      # Only show current status

Features:
- Automatic port conflict detection and resolution
- Process status verification with health endpoint check
- Detailed logging with timestamps
- Log file output to agentd.log
- Troubleshooting hints on failure
"""

import subprocess
import sys
import time
import signal
import os
import argparse
from pathlib import Path


# Configuration
AGENTD_DIR = Path(__file__).parent.resolve()
VENV_DIR = AGENTD_DIR.parent / ".venv"
VENV_PYTHON = VENV_DIR / "bin" / "python"
APP_FILE = AGENTD_DIR / "app.py"
HEALTH_URL = "https://10.103.2.128:10443/health"
MAX_WAIT_SECONDS = 30


def log(msg: str) -> None:
    """Print log message with timestamp."""
    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {msg}")


def release_port(port: int = 10443) -> bool:
    """Force release the specified port by killing processes using it."""
    try:
        # Try to find processes using the port
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            log(f"Found {len(pids)} process(es) using port {port}")
            for pid in pids:
                if pid:
                    try:
                        os.kill(int(pid), signal.SIGKILL)
                        log(f"Killed process {pid} using port {port}")
                    except Exception:
                        pass
            time.sleep(1)
            return True
    except Exception:
        pass
    
    # Fallback: use fuser
    try:
        subprocess.run(["fuser", "-k", f"{port}/tcp"], check=False, capture_output=True)
        time.sleep(1)
        return True
    except Exception:
        pass
    
    return False


def is_port_free(port: int = 10443) -> bool:
    """Check if the port is free."""
    try:
        result = subprocess.run(
            ["lsof", "-i", f":{port}"],
            capture_output=True,
            text=True
        )
        return result.returncode != 0 or not result.stdout.strip()
    except Exception:
        return True


def stop_service() -> bool:
    """Stop any running agentd service processes and ensure port is released."""
    log("Stopping agentd service...")
    
    try:
        # Find and kill python app.py processes
        result = subprocess.run(
            ["pgrep", "-f", "python app.py"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            log(f"Found {len(pids)} process(es) to stop")
            
            for pid in pids:
                if pid:
                    try:
                        os.kill(int(pid), signal.SIGTERM)
                        log(f"Sent SIGTERM to process {pid}")
                    except ProcessLookupError:
                        log(f"Process {pid} already terminated")
                    except Exception as e:
                        log(f"Error stopping process {pid}: {e}")
            
            # Wait for processes to terminate
            time.sleep(2)
            
            # Check if any processes are still running
            result = subprocess.run(
                ["pgrep", "-f", "python app.py"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0 and result.stdout.strip():
                log("Force killing remaining processes...")
                subprocess.run(["pkill", "-9", "-f", "python app.py"], check=False)
                time.sleep(1)
        else:
            log("No running agentd service found")
        
        # Ensure port 10443 is released
        log("Ensuring port 10443 is released...")
        release_port(10443)
        
        # Verify port is free
        for _ in range(5):
            if is_port_free(10443):
                log("Port 10443 is free")
                break
            time.sleep(1)
        else:
            log("WARNING: Port 10443 may still be in use")
        
        log("Service stopped")
        return True
        
    except Exception as e:
        log(f"Error during stop: {e}")
        return False


def start_service() -> bool:
    """Start the agentd service."""
    log("Starting agentd service...")
    
    # Check virtual environment exists
    if not VENV_PYTHON.exists():
        log(f"ERROR: Virtual environment not found at {VENV_DIR}")
        log("Please create the virtual environment first:")
        log(f"  python -m venv {VENV_DIR}")
        return False
    
    # Check app.py exists
    if not APP_FILE.exists():
        log(f"ERROR: app.py not found at {APP_FILE}")
        return False
    
    # Ensure port is free before starting
    if not is_port_free(10443):
        log("WARNING: Port 10443 is still in use, attempting to release...")
        release_port(10443)
        time.sleep(2)
        if not is_port_free(10443):
            log("ERROR: Port 10443 is still in use, cannot start service")
            return False
    
    try:
        # Start the service in background
        env = os.environ.copy()
        env["PATH"] = str(VENV_DIR / "bin") + ":" + env.get("PATH", "")
        
        # Load environment variables from .env file
        env_file = AGENTD_DIR / ".env"
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env[key] = value
        
        # Use nohup to ensure process continues after script exits
        log_file = AGENTD_DIR / "agentd.log"
        with open(log_file, 'w') as lf:
            lf.write(f"# Agentd started at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        process = subprocess.Popen(
            ["nohup", str(VENV_PYTHON), str(APP_FILE)],
            cwd=str(AGENTD_DIR),
            env=env,
            stdout=open(log_file, 'a'),
            stderr=subprocess.STDOUT,
            start_new_session=True
        )
        
        log(f"Service started with PID {process.pid}")
        
        # Wait a moment for process to start and check if it's still running
        time.sleep(2)
        result = subprocess.run(
            ["pgrep", "-f", "python app.py"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0 or not result.stdout.strip():
            log("WARNING: Process may have exited immediately")
            # Check log for errors
            if log_file.exists():
                log_content = log_file.read_text()
                if "address already in use" in log_content:
                    log("ERROR: Port 10443 is already in use")
                elif "error" in log_content.lower():
                    log(f"ERROR: Check {log_file} for details")
        
        return True
        
    except Exception as e:
        log(f"Error starting service: {e}")
        return False


def verify_service(max_wait: int = MAX_WAIT_SECONDS) -> bool:
    """Verify the service is healthy by checking the health endpoint."""
    log(f"Waiting for service to be ready (max {max_wait}s)...")
    
    import urllib.request
    import ssl
    
    # Create SSL context that ignores certificate verification
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            req = urllib.request.Request(HEALTH_URL)
            with urllib.request.urlopen(req, context=ssl_context, timeout=2) as response:
                if response.status == 200:
                    data = response.read().decode('utf-8')
                    log(f"Service is healthy! Response: {data}")
                    return True
        except urllib.error.URLError:
            pass
        except Exception as e:
            pass
        
        time.sleep(1)
    
    log(f"WARNING: Service health check timed out after {max_wait} seconds")
    log("Service may still be starting...")
    return False


def check_health_endpoint() -> tuple[bool, str]:
    """Check health endpoint and return (is_healthy, response_data)."""
    import urllib.request
    import ssl
    
    # Create SSL context that ignores certificate verification
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    try:
        req = urllib.request.Request(HEALTH_URL, method="GET")
        with urllib.request.urlopen(req, context=ssl_context, timeout=5) as response:
            if response.status == 200:
                data = response.read().decode('utf-8')
                return True, data
            else:
                return False, f"HTTP {response.status}"
    except urllib.error.URLError as e:
        return False, f"Connection error: {e.reason}"
    except Exception as e:
        return False, str(e)


def show_status() -> None:
    """Show current service status including process and health check."""
    log("Checking service status...")
    
    # Check process status
    try:
        result = subprocess.run(
            ["pgrep", "-f", "python app.py"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            log(f"Process status: Running with PID(s): {', '.join(pids)}")
        else:
            log("Process status: Not running")
            
    except Exception as e:
        log(f"Process status: Error checking - {e}")
    
    # Check health endpoint
    is_healthy, response = check_health_endpoint()
    if is_healthy:
        log(f"Health check: OK - {response}")
    else:
        log(f"Health check: FAILED - {response}")


def verify_service_status(max_wait: int = 15) -> bool:
    """Verify service is fully operational (process + health check)."""
    log(f"Verifying service status (max {max_wait}s)...")
    
    start_time = time.time()
    last_status = ""
    
    while time.time() - start_time < max_wait:
        # Check process exists
        result = subprocess.run(
            ["pgrep", "-f", "python app.py"],
            capture_output=True,
            text=True
        )
        process_running = result.returncode == 0 and result.stdout.strip()
        if process_running:
            pids = result.stdout.strip().split('\n')
            process_info = f"PID: {', '.join(pids[:2])}"
        else:
            process_info = "No process"
        
        # Check health endpoint
        is_healthy, response = check_health_endpoint()
        
        if process_running and is_healthy:
            log(f"Service verification PASSED - {process_info}, Health: {response}")
            return True
        
        current_status = f"Process: {'OK' if process_running else 'waiting'}, Health: {'OK' if is_healthy else 'waiting'}"
        if current_status != last_status:
            log(f"Status: {current_status}")
            last_status = current_status
        
        time.sleep(1)
    
    log("Service verification FAILED - Timeout waiting for service to be ready")
    # Show final diagnostics
    show_status()
    return False


def main() -> int:
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Restart the AI Agent service"
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip health check and status verification after restart"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Only show current service status (process + health check) without restarting"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force kill any processes using port 10443 before starting"
    )
    
    args = parser.parse_args()
    
    if args.status:
        log("=" * 50)
        log("AI Agent Service Status")
        log("=" * 50)
        show_status()
        log("=" * 50)
        return 0
    
    log("=" * 50)
    log("AI Agent Service Restart")
    log("=" * 50)
    
    # Force kill if requested
    if args.force:
        log("Force mode: Killing all processes using port 10443...")
        release_port(10443)
        time.sleep(2)
    
    # Stop existing service
    if not stop_service():
        log("WARNING: Failed to stop service cleanly, continuing...")
    
    # Ensure clean shutdown
    time.sleep(2)
    
    # Verify port is free
    if not is_port_free(10443):
        log("ERROR: Port 10443 is still in use after stop")
        log("Try: python restart_agentd.py --force")
        return 1
    
    # Start service
    if not start_service():
        log("ERROR: Failed to start service")
        return 1
    
    # Verify service is healthy and show status
    if not args.no_verify:
        success = verify_service_status()
        log("")
        log("Final status:")
        show_status()
        
        if not success:
            log("")
            log("TROUBLESHOOTING:")
            log("1. Check logs: cat /opt/vlab/flasky/app/agentd/agentd.log")
            log("2. Check port: lsof -i :10443")
            log("3. Force restart: python restart_agentd.py --force")
            return 1
    else:
        log("Skipping verification (--no-verify)")
        log("Service may still be starting...")
    
    log("=" * 50)
    log("Restart complete!")
    log("=" * 50)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
