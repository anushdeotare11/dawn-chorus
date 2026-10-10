"""Audio conversion, BirdNET detection, and location/week filtering."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from birdnet import predict_species_at_location_and_time, predict_species_within_audio_file

import config


# ── Types ────────────────────────────────────────────────────────

@dataclass
class Detection:
    """A single detected bird species aggregated across the recording."""
    common_name: str
    scientific_name: str
    count: int
    max_confidence: float
    first_heard_s: float  # seconds from start of recording

    @property
    def first_heard_mmss(self) -> str:
        """Format first_heard_s as mm:ss."""
        mins, secs = divmod(int(self.first_heard_s), 60)
        return f"{mins:02d}:{secs:02d}"


@dataclass
class RawDetection:
    """A single raw prediction window from BirdNET."""
    start_s: float
    end_s: float
    species_key: str
    confidence: float


@dataclass
class DetectionResult:
    """Full result of running detection on a recording."""
    detections: list[Detection] = field(default_factory=list)
    duration_s: float = 0.0
    error: Optional[str] = None


# ── Helpers ──────────────────────────────────────────────────────

import os

def check_ffmpeg() -> bool:
    """Return True if ffmpeg is available on PATH, checking common install paths if needed."""
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

    return shutil.which("ffmpeg") is not None


def parse_species_name(raw: str) -> tuple[str, str]:
    """Parse BirdNET species string 'Scientific name_Common name' into (common, scientific)."""
    parts = raw.split("_", 1)
    if len(parts) == 2:
        return parts[1].strip(), parts[0].strip()
    return raw.strip(), ""


def convert_audio_to_wav(input_path: Path, output_path: Path) -> None:
    """Convert any supported audio file to 48 kHz mono WAV using ffmpeg.

    Raises:
        RuntimeError: If ffmpeg is not installed or conversion fails.
    """
    if not check_ffmpeg():
        raise RuntimeError(
            "ffmpeg is not installed or not on PATH. "
            "Install it from https://ffmpeg.org and ensure it is accessible."
        )
    cmd = [
        "ffmpeg", "-y", "-i", str(input_path),
        "-ar", str(config.FFMPEG_SAMPLE_RATE),
        "-ac", str(config.FFMPEG_CHANNELS),
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg conversion failed:\n{result.stderr[:500]}")


def week_of_year(date) -> int:
    """Convert a calendar date to BirdNET's 1-48 week index.

    BirdNET divides each of the 12 months into 4 weeks (days 1-7 = week 1,
    8-14 = week 2, 15-21 = week 3, 22+ = week 4), giving 48 weeks total per year.
    """
    month = date.month
    day = date.day
    week_in_month = min(4, (day - 1) // 7 + 1)
    birdnet_week = (month - 1) * 4 + week_in_month
    return max(1, min(48, birdnet_week))


# ── Core functions ───────────────────────────────────────────────

def get_likely_species(
    latitude: float,
    longitude: float,
    week: int,
    top_n: int = config.BINGO_CARD_SIZE,
) -> list[tuple[str, str, float]]:
    """Get the most likely bird species for a location and week.

    Returns:
        List of (common_name, scientific_name, confidence) tuples,
        sorted by descending confidence, limited to top_n.
    """
    raw: OrderedDict[str, float] = predict_species_at_location_and_time(
        latitude, longitude, week=week, min_confidence=config.BINGO_LOCATION_MIN_CONF,
    )
    results = []
    for species_key, conf in raw.items():
        common, scientific = parse_species_name(species_key)
        results.append((common, scientific, float(conf)))
    return results[:top_n]


def get_species_filter(
    latitude: float,
    longitude: float,
    week: int,
    min_confidence: float = 0.01,
) -> set[str]:
    """Get the set of species keys expected at a location and week above a min confidence threshold.

    Returns:
        Set of BirdNET species strings formatted as 'Scientific_Common'.
    """
    raw: OrderedDict[str, float] = predict_species_at_location_and_time(
        latitude, longitude, week=week, min_confidence=min_confidence,
    )
    return set(raw.keys())

import streamlit as st

@st.cache_data(show_spinner=False)
def cached_species_filter(lat: float, lon: float, week: int, min_conf: float = 0.01) -> set[str]:
    return get_species_filter(lat, lon, week, min_conf)



def run_detection(
    audio_path: Path,
    min_confidence: float = 0.1,
    species_filter: set[str] | None = None,
    _progress_cb=None,
) -> tuple[list[RawDetection], float]:
    """Run BirdNET detection on an audio file and return raw predictions.

    Args:
        audio_path: Path to a WAV file (48 kHz mono recommended).
        min_confidence: Minimum confidence threshold for raw detections.
        species_filter: Optional set of BirdNET species keys to filter by.
        _progress_cb: Optional callback for progress updates.

    Returns:
        Tuple of (list of RawDetections, duration_s).
    """
    import time
    raw_detections = []
    total_end = 0.0

    generator = predict_species_within_audio_file(
        audio_path,
        min_confidence=min_confidence,
        species_filter=species_filter,
    )

    last_update = time.time()
    new_windows = []
    
    # We need total_s, but BirdNET generator doesn't tell us total_s easily.
    # We can pass total_s from app.py via the _progress_cb, or we just pass processed_s.
    # The prompt says: progress_cb(processed_s, total_s, new_windows). 
    # Since total_s is not easily available here, we pass 0 or maybe audio duration if we pass it in.
    # Actually, we can get duration using soundfile or wave, but we don't have it here. Let's pass 0.0 for total_s, app.py has it from earlier.
    for (start_s, end_s), predictions in generator:
        total_end = max(total_end, end_s)
        window_dets = []
        for species_key, conf in predictions.items():
            if conf >= min_confidence:
                det = RawDetection(start_s, end_s, species_key, float(conf))
                raw_detections.append(det)
                window_dets.append(det)
        
        if window_dets:
            new_windows.append(window_dets)
            
        if _progress_cb and time.time() - last_update > 0.3:
            try:
                _progress_cb("listening", {"end_s": end_s, "new_windows": new_windows})
            except Exception as e:
                import logging
                logging.error(f"Progress callback failed: {e}")
            new_windows = []
            last_update = time.time()
            
    # One final call to flush remaining new_windows
    if _progress_cb and new_windows:
        try:
            _progress_cb("listening", {"end_s": total_end, "new_windows": new_windows})
        except Exception:
            pass

    if _progress_cb:
        _progress_cb("listening", {"end_s": total_end})
    return raw_detections, total_end


def aggregate_detections(raw_detections: list[RawDetection], min_confidence: float) -> list[Detection]:
    """Aggregate raw detections into per-species counts and max confidences."""
    agg: dict[str, dict] = {}
    
    for d in raw_detections:
        if d.confidence < min_confidence:
            continue
        if d.species_key not in agg:
            agg[d.species_key] = {
                "count": 0,
                "max_conf": 0.0,
                "first_time": d.start_s,
            }
        entry = agg[d.species_key]
        entry["count"] += 1
        entry["max_conf"] = max(entry["max_conf"], d.confidence)

    detections = []
    for species_key, info in agg.items():
        common, scientific = parse_species_name(species_key)
        detections.append(Detection(
            common_name=common,
            scientific_name=scientific,
            count=info["count"],
            max_confidence=round(info["max_conf"], 3),
            first_heard_s=info["first_time"],
        ))

    detections.sort(key=lambda x: x.max_confidence, reverse=True)
    return detections


def detect_from_upload(
    uploaded_file_path: Path,
    original_filename: str,
    min_confidence: float = config.CONFIDENCE_THRESHOLD,
    species_filter: set[str] | None = None,
) -> DetectionResult:
    """Convert an uploaded audio file if needed and run detection.

    Handles conversion for non-WAV formats, runs BirdNET, and cleans up
    temporary files.

    Args:
        uploaded_file_path: Path to the uploaded file on disk.
        original_filename: Original filename (used to detect format).
        min_confidence: Confidence threshold for detections.
        species_filter: Optional set of BirdNET species keys for filtering.

    Returns:
        DetectionResult with detections or an error message.
    """
    if not check_ffmpeg():
        return DetectionResult(
            error="ffmpeg is not installed. Please install it to process audio files."
        )

    suffix = Path(original_filename).suffix.lower().lstrip(".")
    if suffix not in config.SUPPORTED_EXTENSIONS:
        return DetectionResult(
            error=f"Unsupported audio format '.{suffix}'. "
            f"Supported: {', '.join(config.SUPPORTED_EXTENSIONS)}"
        )

    try:
        # Convert to WAV in a temp directory
        with tempfile.TemporaryDirectory() as tmp_dir:
            wav_path = Path(tmp_dir) / "audio.wav"

            if suffix == "wav":
                # Still convert to ensure correct sample rate/channels
                convert_audio_to_wav(uploaded_file_path, wav_path)
            else:
                convert_audio_to_wav(uploaded_file_path, wav_path)

            if wav_path.stat().st_size < 1000:
                return DetectionResult(error="Audio file appears to be empty or too short.")

            raw_list, duration = run_detection(wav_path, min_confidence, species_filter)
            agged = aggregate_detections(raw_list, min_confidence)
            return DetectionResult(detections=agged, duration_s=duration)

    except RuntimeError as e:
        return DetectionResult(error=str(e))
    except Exception as e:
        return DetectionResult(error=f"Detection failed: {e}")
