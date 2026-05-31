"""Debug script — run this to diagnose the claude CLI issue."""
import subprocess, shutil, os, sys, tempfile

print(f"Python: {sys.executable}")
print(f"Platform: {sys.platform}")
print()

# Find claude
claude = shutil.which("claude") or shutil.which("claude.cmd")
print(f"shutil.which('claude'):     {shutil.which('claude')}")
print(f"shutil.which('claude.cmd'): {shutil.which('claude.cmd')}")
print(f"Resolved path: {claude}")
print()

# Check common npm locations
appdata = os.environ.get("APPDATA", "")
npm_claude = os.path.join(appdata, "npm", "claude.cmd")
npm_claude2 = os.path.join(appdata, "npm", "claude")
print(f"npm claude.cmd exists: {os.path.exists(npm_claude)} → {npm_claude}")
print(f"npm claude exists:     {os.path.exists(npm_claude2)} → {npm_claude2}")
print()

# Try running claude --version via shell=True
print("Testing: subprocess shell=True...")
try:
    r = subprocess.run("claude --version", shell=True, capture_output=True, text=True, timeout=15)
    print(f"  returncode: {r.returncode}")
    print(f"  stdout: {r.stdout.strip()}")
    print(f"  stderr: {r.stderr.strip()[:200]}")
except Exception as e:
    print(f"  FAILED: {e}")
print()

# Try writing a simple prompt to temp file and running
print("Testing: pipe prompt via temp file + shell=True...")
try:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("Say exactly: TRADING AGENT ONLINE")
        tmpfile = f.name
    print(f"  Temp file: {tmpfile}")

    cmd = f'claude --print --dangerously-skip-permissions < "{tmpfile}"'
    print(f"  Command: {cmd}")
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    print(f"  returncode: {r.returncode}")
    print(f"  stdout: {r.stdout.strip()[:200]}")
    print(f"  stderr: {r.stderr.strip()[:200]}")
    os.unlink(tmpfile)
except Exception as e:
    print(f"  FAILED: {e}")
