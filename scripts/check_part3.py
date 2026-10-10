import sys
import logging
import os
from pathlib import Path

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
logging.getLogger('tensorflow').setLevel(logging.ERROR)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import tempfile
from detect import run_detection, aggregate_detections, get_species_filter, convert_audio_to_wav

print("=== PART 3: PROVE DETECTION WORKS ===")

clips = [p for p in sorted(Path("samples").iterdir()) if p.suffix.lower() in [".mp3", ".wav"] and not p.name.startswith("concat") and not p.name.startswith("long_walk")]

lat, lon, week = 15.46, 75.01, 38
species_filter_set = get_species_filter(lat, lon, week, min_confidence=0.01)

print(f"{'Filename':<45} | {'Filter Mode':<15} | {'Top 3 Detections (Conf)':<45} | {'Target Found?'}")
print("-" * 125)

for clip in clips:
    parts = clip.stem.split(" - ")
    expected = parts[1].strip() if len(parts) >= 2 else clip.stem

    for mode in ["With Filter", "No Filter"]:
        filt = species_filter_set if mode == "With Filter" else None
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            wav_path = Path(tmp_dir) / "audio.wav"
            convert_audio_to_wav(clip, wav_path)
            raw, dur = run_detection(wav_path, min_confidence=0.1, species_filter=filt)
        agged = aggregate_detections(raw, 0.1)
        
        top3 = agged[:3]
        top3_str = ", ".join(f"{d.common_name} ({d.max_confidence:.2f})" for d in top3) or "None"
        
        found = "No"
        for d in agged:
            if expected.lower() in d.common_name.lower() or d.common_name.lower() in expected.lower():
                found = f"Yes ({d.max_confidence:.2f})"
                break
                
        print(f"{clip.name:<45} | {mode:<15} | {top3_str:<45} | {found}")
