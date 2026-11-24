import subprocess
import time
import urllib.request
import json
import sys
import os

print("Starting Uvicorn HTTP server against Neon PostgreSQL...")
env = os.environ.copy()
env["PYTHONPATH"] = "D:\\D\\rise"

proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "hireloop.apps.api.app.main:app", "--host", "127.0.0.1", "--port", "8000"],
    cwd="D:/D/rise/hireloop",
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    env=env,
    text=True
)

try:
    # Wait for server to be responsive
    connected = False
    for attempt in range(20):
        time.sleep(1)
        if proc.poll() is not None:
            stdout, stderr = proc.communicate()
            print("Server exited prematurely:")
            print("STDOUT:", stdout)
            print("STDERR:", stderr)
            sys.exit(1)
        try:
            with urllib.request.urlopen("http://127.0.0.1:8000/healthz", timeout=2) as resp:
                if resp.status == 200:
                    connected = True
                    break
        except Exception:
            continue

    if not connected:
        stdout, stderr = proc.communicate()
        print("Failed to connect to server:")
        print("STDOUT:", stdout)
        print("STDERR:", stderr)
        sys.exit(1)

    # 1. Probe healthz
    with urllib.request.urlopen("http://127.0.0.1:8000/healthz", timeout=5) as resp:
        health_data = json.loads(resp.read().decode("utf-8"))
        print("HTTP GET /healthz response:", health_data)
        assert resp.status == 200

    # 2. Probe readyz
    with urllib.request.urlopen("http://127.0.0.1:8000/readyz", timeout=5) as resp:
        ready_data = json.loads(resp.read().decode("utf-8"))
        print("HTTP GET /readyz response:", ready_data)
        assert resp.status == 200

    # 3. Probe jobs stored in Neon PostgreSQL
    with urllib.request.urlopen("http://127.0.0.1:8000/v1/jobs/?limit=3", timeout=5) as resp:
        jobs_data = json.loads(resp.read().decode("utf-8"))
        print(f"HTTP GET /v1/jobs/ returned {len(jobs_data)} jobs directly from Neon:")
        for j in jobs_data:
            print(f"  - [{j['id'][:8]}] {j['title']} ({j['location']})")
        assert len(jobs_data) > 0

    print("\nLive Uvicorn server verification completed successfully!")
finally:
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
