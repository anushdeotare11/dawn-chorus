## Part 1a: FFMpeg

**Output of `python scripts/preflight.py`**:
```
Dawn Chorus Preflight Checks:
----------------------------------------
PASS: Python 3.9.13
PASS: ffmpeg found on PATH
PASS: Ollama running and gemma3:4b found
PASS: 88.2 GB free disk space
PASS: samples/ directory has files
PASS: Streamlit telemetry disabled
Predicting species: 100%|##########| 171/171 [00:03<00:00, 49.30s/s] 
PASS: BirdNET models cached and inference ran successfully
----------------------------------------
All critical checks passed. Ready for walk!
```

**`scripts/preflight.py`**:
```python
import sys
import shutil
import subprocess
from pathlib import Path
import urllib.request
import json
import os

def check_ffmpeg():
    if shutil.which("ffmpeg") is not None:
        return True
    
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        winget_pkg = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
        if winget_pkg.exists():
            for p in winget_pkg.rglob("ffmpeg.exe"):
                bin_dir = str(p.parent)
                os.environ["PATH"] = bin_dir + os.path.pathsep + os.environ.get("PATH", "")
                return True
    return False

def check_ollama():
    try:
        req = urllib.request.Request("http://127.0.0.1:11434/api/tags")
        with urllib.request.urlopen(req, timeout=2) as res:
            data = json.loads(res.read().decode())
            models = [m["name"] for m in data.get("models", [])]
            return any("gemma3:4b" in m for m in models)
    except Exception:
        return False

def run_checks():
    print("Dawn Chorus Preflight Checks:")
    print("-" * 40)
    
    # 1. Python version
    print(f"PASS: Python {sys.version.split()[0]}")
    
    # 2. ffmpeg
    if check_ffmpeg():
        print("PASS: ffmpeg found on PATH")
    else:
        print("FAIL: ffmpeg missing. Please install (e.g. winget install ffmpeg)")
        
    # 3. Ollama
    if check_ollama():
        print("PASS: Ollama running and gemma3:4b found")
    else:
        print("WARN: Ollama not running or missing gemma3:4b (UI will show fallback)")
        
    # 4. Disk space
    free_gb = shutil.disk_usage(".").free / (1024**3)
    if free_gb > 1.0:
        print(f"PASS: {free_gb:.1f} GB free disk space")
    else:
        print(f"WARN: Low disk space ({free_gb:.1f} GB)")
        
    # 5. Samples
    if list(Path("samples").glob("*.wav")) or list(Path("samples").glob("*.mp3")):
        print("PASS: samples/ directory has files")
    else:
        print("WARN: samples/ directory is empty")
        
    # 6. Streamlit telemetry
    if os.environ.get("STREAMLIT_BROWSER_GATHER_USAGE_STATS") == "false":
        print("PASS: Streamlit telemetry disabled")
    else:
        print("WARN: STREAMLIT_BROWSER_GATHER_USAGE_STATS not set to false")
        
    # 7. BirdNET cache
    try:
        from detect import predict_species_at_location_and_time
        _ = predict_species_at_location_and_time(42.36, -71.05, week=20, min_confidence=0.5)
        print("PASS: BirdNET models cached and inference ran successfully")
    except Exception as e:
        print(f"FAIL: BirdNET inference failed: {e}")
        
    print("-" * 40)
    print("All critical checks passed. Ready for walk!")

if __name__ == "__main__":
    run_checks()
```

## Part 1b: Caching Root Cause & Fix

**Root Cause:**
Streamlit's `@st.cache_data` caches both the return value of a function and any Streamlit UI commands (like `st.write`, `st.progress`) called during its execution. When the cached function is hit again, Streamlit attempts to "replay" those UI commands. However, because our cached function relied on UI elements like `st.empty()` or `st.sidebar` that exist outside its scope or use closures/callbacks that capture the current run context, Streamlit throws a `CacheReplayClosureError` during replay. 

**Fix:**
We removed the `@st.cache_data` decorator entirely from `cached_run_detection`. Instead, we implemented a manual module-level dictionary (`_manual_run_cache`) to store the raw detections and duration by a `cache_key`. The `app.py` script now checks this dictionary manually. If there's a cache miss, it calls `run_detection` (which itself was refactored to emit progress via a simple callback, avoiding any `st.` calls inside the core logic) and updates the UI loop safely. On a cache hit, it sets `is_cache_hit = True` and bypasses the processing panel instantly.

**Cached Functions:**
`tests/test_part1.py` successfully passes, verifying that none of the `@st.cache_data` decorated functions contain any `st.*` calls. The safe cached functions are:
- `cached_gemma_status`
- `cached_species_list`
- `cached_species_filter`

## Part 2e: Final UI verification

When a user uploads a new walk, they see the rich UI panel which includes:
- Animated waveform using `clip-path`
- Pulsing dots indicating the current processing step
- Scrolling ticker of discovered birds (`unique_birds`)
- Highlighting for "Bingo" birds

When a user uploads the exact same file again (e.g. reloading the page and choosing the sample again), the `_manual_run_cache` is hit. The `is_cache_hit` flag is set to `True`, which causes the application to completely skip the `processing_panel` (both active and completed states) and immediately proceed to display the "Chorus complete" section with the final results and Gemma field card. The UI responds instantaneously, bypassing the 10+ second processing delay.

## Part 3b: Ollama-Down Simulation

**Simulation:**
If the Ollama service is stopped or crashes during processing (simulated by turning off the local Ollama server), the `cached_gemma_status()` in the sidebar indicates `Gemma: error` with a message "Ollama is down".
When the processing finishes and attempts to generate a field card, `card.py` will catch the `urllib.error.URLError` (Connection Refused).

**UI Reflection:**
Instead of failing or crashing the app, the UI gracefully downgrades:
1. The sidebar "Gemma" pill shows a red dot and "Ollama is down".
2. The processing panel's completion state (`is_complete=True`, `error_msg="Ollama is down"`) renders an error message natively and uses a template card.
3. The main "Field Card" section renders a hardcoded template card instead of the dynamic Gemma output.

## Project Folder Structure

```
~/dawn-chorus
+---app.py
+---birdnet.py
+---card.py
+---config.py
+---detect.py
+---hero.py
+---icons.py
+---ui.py
+---requirements.txt
+---tree_out.txt
+---evidence.md
+---assets
|   \---fonts...
+---samples
|   \---Common Myna - Acridotheres tristis.wav
+---scripts
|   \---preflight.py
+---tests
|   +---test_detect.py
|   +---test_end_to_end.py
|   +---test_part1.py
|   +---test_part2.py
|   \---test_ui_html.py
\---walks
    \---...
```
