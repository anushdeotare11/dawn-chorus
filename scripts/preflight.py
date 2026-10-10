import sys
import shutil
import urllib.request
from pathlib import Path
import json
import argparse
import tempfile

# Preflight checks for Dawn Chorus
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

def check_python():
    v = sys.version_info
    if v.major >= 3 and v.minor >= 9:
        return True, f"PASS: Python {v.major}.{v.minor}.{v.micro}"
    return False, f"FAIL: Python {v.major}.{v.minor} is unsupported. Fix: Install Python 3.9+"

def check_ffmpeg():
    from detect import check_ffmpeg
    if check_ffmpeg():
        return True, "PASS: ffmpeg found on PATH"
    return False, "FAIL: ffmpeg missing. Fix: Install ffmpeg and add to PATH"

def check_ollama():
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags")
        with urllib.request.urlopen(req, timeout=2) as resp:
            data = json.loads(resp.read().decode())
        models = [m.get("model", "") for m in data.get("models", [])]
        from config import OLLAMA_MODEL
        if any(m.startswith(OLLAMA_MODEL) for m in models):
            return True, f"PASS: Ollama running and {OLLAMA_MODEL} found"
        return False, f"FAIL: Model missing. Fix: run `ollama pull {OLLAMA_MODEL}`"
    except Exception:
        return False, "FAIL: Ollama not reachable. Fix: Start Ollama app or run `ollama serve`"

def check_disk_space():
    total, used, free = shutil.disk_usage("/")
    free_gb = free / (1024**3)
    if free_gb > 2.0:
        return True, f"PASS: {free_gb:.1f} GB free disk space"
    return False, f"FAIL: Only {free_gb:.1f} GB free. Fix: Free up at least 2 GB"

def check_samples():
    samples_dir = Path("samples")
    if samples_dir.exists() and any(f.suffix in [".wav", ".mp3", ".m4a"] for f in samples_dir.iterdir()):
        return True, "PASS: samples/ directory has audio files"
    return True, "WARN: samples/ directory has no audio files (optional)"

def check_streamlit_telemetry():
    toml_path = Path(".streamlit") / "config.toml"
    if toml_path.exists():
        content = toml_path.read_text(encoding="utf-8")
        if "gatherUsageStats = false" in content or "gatherUsageStats=false" in content.replace(" ", ""):
            return True, "PASS: Streamlit telemetry disabled"
    return False, "FAIL: Streamlit telemetry not explicitly disabled. Fix: Add browser.gatherUsageStats=false to .streamlit/config.toml"

def check_birdnet_models_and_inference(offline_mode=False):
    import socket
    original_create_connection = socket.create_connection
    if offline_mode:
        def block_network(address, timeout=None, source_address=None, *args, **kwargs):
            host, port = address
            if not (host == "127.0.0.1" or host == "localhost" or host == "::1"):
                raise OSError(f"Network blocked in offline mode: {host}:{port}")
            return original_create_connection(address, timeout=timeout, source_address=source_address, *args, **kwargs)
        socket.create_connection = block_network
    
    try:
        # Find a sample
        samples = list(Path("samples").glob("*.*"))
        if not samples:
            return False, "FAIL: No samples found to run detection"
        
        sample = next((s for s in samples if s.suffix in [".wav", ".mp3", ".m4a"]), None)
        if not sample:
            return True, "WARN: No valid audio samples found to test inference (optional)"
            
        from detect import run_detection, convert_audio_to_wav
        with tempfile.TemporaryDirectory() as tmp_dir:
            wav_path = Path(tmp_dir) / "test.wav"
            convert_audio_to_wav(sample, wav_path)
            raw, _ = run_detection(wav_path, min_confidence=0.01)
        
        if offline_mode:
            socket.create_connection = original_create_connection
            return True, "PASS: BirdNET models cached and inference ran (offline mode confirmed)"
        else:
            return True, "PASS: BirdNET models cached and inference ran successfully"
    except Exception as e:
        if offline_mode:
            socket.create_connection = original_create_connection
        return False, f"FAIL: BirdNET inference error. Fix: Ensure models are cached and code is correct. Error: {e}"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true", help="Block outbound network to test offline capability")
    args = parser.parse_args()
    
    checks = [
        check_python,
        check_ffmpeg,
        check_ollama,
        check_disk_space,
        check_samples,
        check_streamlit_telemetry,
        lambda: check_birdnet_models_and_inference(args.offline)
    ]
    
    all_passed = True
    print("Dawn Chorus Preflight Checks:")
    print("-" * 40)
    for check in checks:
        passed, msg = check()
        print(msg)
        if not passed:
            all_passed = False
            
    print("-" * 40)
    if all_passed:
        print("All critical checks passed. Ready for walk!")
        sys.exit(0)
    else:
        print("Some checks failed. Please fix the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
