import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import cached_run_detection
from ui import processing_panel
from detect import RawDetection
import time

def test_processing_panel_html_format():
    # Test all states and assert single-line format
    for state in ["preparing", "listening", "writing", "error"]:
        html = processing_panel(state, "test.wav", 1.5, 60.0, 0.5, 30.0, 30.0, "error" if state == "error" else "")
        # should be a single line HTML string without newlines
        assert "\n" not in html
        assert "<div" in html

def test_progress_percent_calculation():
    html = processing_panel("listening", "test.wav", 1.5, 60.0, 0.75, 45.0, 15.0, "")
    # Check for left: 75.0% for the playhead
    assert "left: 75.0%" in html
    assert "Elapsed 0:45" in html
    assert "About 15 s left" in html

def test_failure_path():
    html = processing_panel("error", "test.wav", 1.0, 0.0, 0.0, 0.0, -1, "ffmpeg failed")
    assert "ffmpeg failed" in html
    assert "Analysis failed" in html
    
    html_ollama = processing_panel("error", "test.wav", 1.0, 0.0, 0.0, 0.0, -1, "Ollama is down")
    assert "Template card" in html_ollama
