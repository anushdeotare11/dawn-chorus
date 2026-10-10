"""Dawn Chorus — Streamlit UI for bird-listening walk analysis."""

from __future__ import annotations

import json
import tempfile
import time
import random
import wave
import html
from datetime import date, datetime
from pathlib import Path
import numpy as np

import streamlit as st

import config
from card import build_walk_data, generate_field_card
from detect import (
    check_ffmpeg,
    convert_audio_to_wav,
    get_likely_species,
    cached_species_filter,
    week_of_year,
    run_detection,
    aggregate_detections,
    RawDetection,
)
import ui
import hero
from icons import get_icon

# ── Page config ──────────────────────────────────────────────────

st.set_page_config(
    page_title="Dawn Chorus",
    page_icon="🌅",
    layout="centered",
    initial_sidebar_state="expanded"
)

# ── Custom CSS ───────────────────────────────────────────────────

css_path = Path(__file__).parent / "styles.css"
if css_path.exists():
    st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)

# ── State and Caching ────────────────────────────────────────────

if "screen_time_start" not in st.session_state:
    st.session_state.screen_time_start = time.time()
if "card_text" not in st.session_state:
    st.session_state.card_text = None
if "card_warning" not in st.session_state:
    st.session_state.card_warning = None
if "card_badge" not in st.session_state:
    st.session_state.card_badge = None
if "last_results_hash" not in st.session_state:
    st.session_state.last_results_hash = None
if "played_animations" not in st.session_state:
    st.session_state.played_animations = set()
if "sample_clip_loaded" not in st.session_state:
    st.session_state.sample_clip_loaded = False
if "sample_clip_path" not in st.session_state:
    st.session_state.sample_clip_path = None

from card import get_gemma_status
@st.cache_data(show_spinner=False, ttl=10)
def cached_gemma_status() -> tuple[str, str, str]:
    return get_gemma_status()

@st.cache_data(show_spinner="Loading species list…", ttl=3600)
def cached_species_list(lat: float, lon: float, week: int, top_n: int) -> list[tuple[str, str, float]]:
    return get_likely_species(lat, lon, week, top_n)

def extract_waveform_and_duration(wav_path: Path, num_bars: int = 100) -> tuple[list[float], float]:
    try:
        with wave.open(str(wav_path), 'rb') as wf:
            frames_count = wf.getnframes()
            rate = wf.getframerate()
            duration = frames_count / float(rate) if rate > 0 else 0.0
            
            frames = wf.readframes(frames_count)
            audio = np.frombuffer(frames, dtype=np.int16)
            if len(audio) == 0: return [], duration
            chunk_size = max(1, len(audio) // num_bars)
            peaks = []
            for i in range(num_bars):
                chunk = audio[i*chunk_size : (i+1)*chunk_size]
                if len(chunk) > 0:
                    peaks.append(float(np.max(np.abs(chunk))))
                else:
                    peaks.append(0.0)
            max_val = max(peaks) if max(peaks) > 0 else 1.0
            return [p/max_val for p in peaks], duration
    except Exception:
        return [], 0.0

import hashlib

_manual_run_cache = {}

def cached_run_detection(file_bytes: bytes, suffix: str, species_filter: set[str] | None, _progress_cb=None) -> tuple[list[RawDetection], float, float, list[float], str, bool]:
    """Manually cache the heavy ffmpeg and BirdNET run."""
    h = hashlib.sha256()
    h.update(file_bytes)
    h.update(suffix.encode('utf-8'))
    if species_filter is not None:
        h.update(",".join(sorted(species_filter)).encode('utf-8'))
    else:
        h.update(b"none")
    cache_key = h.hexdigest()
    
    if cache_key in _manual_run_cache:
        cached_res = _manual_run_cache[cache_key]
        return (*cached_res, True)

    t0 = time.time()
    try:
        if _progress_cb:
            _progress_cb("preparing", {})
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_path = Path(tmp_dir) / f"upload.{suffix}"
            input_path.write_bytes(file_bytes)
            
            wav_path = Path(tmp_dir) / "audio.wav"
            convert_audio_to_wav(input_path, wav_path)
            
            if wav_path.stat().st_size < 1000:
                res = ([], 0.0, time.time() - t0, [], "Audio file appears to be empty or too short.")
                _manual_run_cache[cache_key] = res
                return (*res, False)
                
            waveform, duration = extract_waveform_and_duration(wav_path, num_bars=120)
            
            if _progress_cb:
                _progress_cb("listening", {"duration": duration})
            raw_list, _ = run_detection(wav_path, min_confidence=0.01, species_filter=species_filter, _progress_cb=_progress_cb)
            
        res = (raw_list, duration, time.time() - t0, waveform, "")
        _manual_run_cache[cache_key] = res
        if len(_manual_run_cache) > 5:
            _manual_run_cache.pop(next(iter(_manual_run_cache)))
        return (*res, False)
    except Exception as e:
        return ([], 0.0, time.time() - t0, [], str(e), False)

def has_played(key: str) -> bool:
    if key in st.session_state.played_animations:
        return True
    st.session_state.played_animations.add(key)
    return False

# ── Sidebar ──────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(f"### {get_icon('map-pin', 20)} Walk Settings", unsafe_allow_html=True)

    latitude = st.number_input("Latitude", value=config.DEFAULT_LATITUDE, format="%.4f")
    longitude = st.number_input("Longitude", value=config.DEFAULT_LONGITUDE, format="%.4f")
    walk_date = st.date_input("Walk date", value=date.today())
    birdnet_week = week_of_year(walk_date)
    st.caption(f"BirdNET week: {birdnet_week}")
    
    time_of_day = st.selectbox("Time of day", options=["Dawn", "Day", "Dusk"])
    
    st.markdown(f"### {get_icon('sliders', 20)} Analysis", unsafe_allow_html=True)
    confidence = st.slider(
        "Confidence threshold",
        min_value=config.CONFIDENCE_MIN,
        max_value=config.CONFIDENCE_MAX,
        value=config.CONFIDENCE_THRESHOLD,
        step=config.CONFIDENCE_STEP,
    )
    st.caption("Adjusts results instantly.")
    
    # Gemma Status Pill
    gemma_state, gemma_color, gemma_msg = cached_gemma_status()
    st.markdown(
        f'<div style="padding: 4px 8px; border-radius: 12px; background: rgba(0,0,0,0.05); font-size: 0.8rem; display: inline-flex; align-items: center; gap: 6px; margin-top: 10px;">'
        f'<div style="width: 8px; height: 8px; border-radius: 50%; background-color: {gemma_color};"></div>'
        f'Gemma: {gemma_state}'
        f'</div>',
        unsafe_allow_html=True
    )
    if gemma_state != "ready":
        st.caption(gemma_msg)
    
    with st.expander("Advanced"):
        test_mode = st.checkbox("Test mode (skip location filter)", value=False)
        st.markdown("Load a sample clip to test the UI.")
        if st.button("Load a sample walk"):
            samples = list(Path("samples").glob("*.mp3")) + list(Path("samples").glob("*.wav"))
            if samples:
                st.session_state.sample_clip_loaded = True
                st.session_state.sample_clip_path = random.choice([s for s in samples if not s.name.startswith("concat")])
                st.session_state.played_animations.clear() # reset animations for demo
                st.rerun()
            else:
                st.warning("No sample audio files found. To test with sample audio, please download CC-licensed clips from sources like Xeno-canto (e.g. CC BY-NC-SA 4.0, crediting the recordist) and place them in the `samples/` folder. See `samples/README.md` for details. Alternatively, you can view the sample data in `examples/example_walk.json` directly.")
        if st.session_state.sample_clip_loaded:
            if st.button("Clear sample"):
                st.session_state.sample_clip_loaded = False
                st.session_state.sample_clip_path = None
                st.rerun()

    st.markdown("---")
    st.markdown('<div style="font-size:0.8em; padding:8px; opacity:0.8;">🔒 Completely offline. No tracking.</div>', unsafe_allow_html=True)


# Check ffmpeg
if not check_ffmpeg():
    st.error("⚠️ **ffmpeg not found.** Please install it and ensure it's on your PATH.")
    st.stop()


# ── Scene Background & Hero ──────────────────────────────────────

st.markdown(ui.ambient_particles(time_of_day), unsafe_allow_html=True)

hero_played = has_played("hero_animation")
hero_placeholder = st.empty()


# ── Step 1: Quest & Bingo ──────────────────────────────────────────

try:
    bingo_species = cached_species_list(latitude, longitude, birdnet_week, config.BINGO_CARD_SIZE)
except Exception as e:
    st.error(f"Could not load species list: {e}")
    bingo_species = []

bingo_names = [name for name, _, _ in bingo_species]

st.markdown(f"<h2>{get_icon('map-pin', 24)} Today's Outdoor Quest</h2>", unsafe_allow_html=True)
st.write(f"Listen for 3 of these {len(bingo_species)} local birds. Go outside and notice what you normally walk past.")

st.markdown(ui.section_divider(), unsafe_allow_html=True)


# ── Step 2: Upload / Audio ───────────────────────────────────────

st.markdown(f"""
<div class="panel upload-panel section-fade">
    <div class="panel-title" style="justify-content:center;">{get_icon('leaf', 24)} Your mission is ready. Put your phone away.</div>
    <p>Go outside for 20 minutes. Leave the screen off. Come back when you're done.</p>
</div>
""", unsafe_allow_html=True)

st.markdown(f"<h2>{get_icon('upload', 24)} When you're back</h2>", unsafe_allow_html=True)
st.write("Upload your recording here. Analyze later.")

st.caption("Wait until the file shows a check mark, then the analysis starts automatically.")
uploaded_file = st.file_uploader("Upload audio recording", type=config.SUPPORTED_EXTENSIONS, label_visibility="collapsed")

file_bytes = None
suffix = ""
is_sample = False
file_size_mb = 0
file_name = ""

if st.session_state.sample_clip_loaded and st.session_state.sample_clip_path:
    st.info(f"Using demo sample: {st.session_state.sample_clip_path.name}")
    file_bytes = st.session_state.sample_clip_path.read_bytes()
    suffix = st.session_state.sample_clip_path.suffix.lower().lstrip(".")
    is_sample = True
    file_size_mb = len(file_bytes) / (1024 * 1024)
    file_name = st.session_state.sample_clip_path.name
elif uploaded_file is not None:
    file_bytes = uploaded_file.getvalue()
    suffix = Path(uploaded_file.name).suffix.lower().lstrip(".")
    file_size_mb = len(file_bytes) / (1024 * 1024)
    file_name = uploaded_file.name

if file_bytes:
    if test_mode:
        species_filter_set = None
    else:
        species_filter_set = cached_species_filter(latitude, longitude, birdnet_week, min_conf=0.01)

    panel_placeholder = st.empty()
    # To detect cache miss, we can track time inside the callback
    cb_start_time = time.time()
    prog_state = {"last_update": 0.0, "duration_s": 0.0, "detections": []}

    def progress_callback(state, info):
        now = time.time()
        # Throttle UI updates
        if now - prog_state["last_update"] < 0.3 and state != "error" and not (state == "listening" and info.get("duration", 0) > 0):
            return
            
        elapsed = now - cb_start_time
        remaining = -1.0
        pct = 0.0
        
        if state == "listening":
            if "duration" in info:
                prog_state["duration_s"] = info["duration"]
            if "waveform" in info:
                prog_state["waveform"] = info["waveform"]
            
            if "new_windows" in info:
                for window in info["new_windows"]:
                    for det in window:
                        prog_state["detections"].append(det)

            if "end_s" in info and prog_state["duration_s"] > 0:
                pct = min(1.0, info["end_s"] / prog_state["duration_s"])
                if pct > 0.05:
                    est_total = elapsed / pct
                    remaining = max(0.0, est_total - elapsed)
        
        panel_placeholder.html(ui.processing_panel(
            state=state, 
            file_name=file_name, 
            file_size_mb=file_size_mb, 
            duration_s=prog_state["duration_s"], 
            progress_pct=pct, 
            elapsed_s=elapsed, 
            remaining_s=remaining, 
            error_msg=info.get("msg", ""),
            waveform=prog_state.get("waveform", []),
            detections=prog_state.get("detections", []),
            bingo_names=bingo_names
        ))
        prog_state["last_update"] = now

    raw_list, duration, process_time, waveform, error_msg, is_cache_hit = cached_run_detection(file_bytes, suffix, species_filter_set, _progress_cb=progress_callback)
    
    if error_msg:
        progress_callback("error", {"msg": error_msg})
        st.stop()
        
    if not is_cache_hit:
        progress_callback("writing", {})
        # Note: writing state will stay until card is generated, but card is generated below
    
    if not is_cache_hit:
        panel_placeholder.empty()
        agged_detections = aggregate_detections(raw_list, min_confidence=confidence)
        st.markdown(ui.processing_panel(
            state="done",
            file_name=file_name,
            file_size_mb=file_size_mb,
            duration_s=duration,
            progress_pct=1.0,
            elapsed_s=process_time,
            remaining_s=0,
            error_msg="",
            waveform=waveform,
            detections=raw_list,
            bingo_names=bingo_names,
            is_complete=True
        ), unsafe_allow_html=True)
        st.toast("Analysis complete")
    else:
        panel_placeholder.empty()
        agged_detections = aggregate_detections(raw_list, min_confidence=confidence)
    
    # Update Hero with waveform
    hero_placeholder.markdown(hero.build_hero(time_of_day, not hero_played, waveform), unsafe_allow_html=True)
    
    agged_detections = aggregate_detections(raw_list, min_confidence=confidence)
    duration_min = max(1, int(duration / 60))
    duration_mmss = f"{int(duration // 60)}:{int(duration % 60):02d}"
    
    res_hash = f"{len(agged_detections)}_{confidence}_{duration_mmss}_{walk_date}_{time_of_day}_{test_mode}"
    
    played_wave = has_played(f"wave_{res_hash}")
    
    st.markdown(f"""
    <div class="panel">
        <div class="panel-title">{get_icon('mic', 20)} File Analysis</div>
        <div style="display:flex; gap: 20px; opacity: 0.8; font-size: 0.9rem;">
            <div><strong>File:</strong> {html.escape(file_name)}</div>
            <div><strong>Size:</strong> {file_size_mb:.1f} MB</div>
            <div><strong>Duration:</strong> {duration_mmss}</div>
        </div>
        {ui.waveform_svg(waveform, not played_wave)}
    </div>
    """, unsafe_allow_html=True)

    st.markdown(ui.section_divider(), unsafe_allow_html=True)
    st.markdown(f"<h2>{get_icon('bird', 24)} What you discovered</h2>", unsafe_allow_html=True)
    
    found_names = {d.common_name for d in agged_detections}
    missed_names = [n for n in bingo_names if n not in found_names]
    
    # Score
    if bingo_names:
        found_count = len(found_names & set(bingo_names))
        played_score = has_played(f"score_{res_hash}")
        st.markdown(ui.score_ring(found_count, len(bingo_names), not played_score), unsafe_allow_html=True)

    # Top Species Featured Card
    if agged_detections:
        top_bird = agged_detections[0]
        st.markdown(f"""
        <div class="featured-card section-fade">
            <div class="featured-icon">{get_icon('bird', 28, 'var(--darker-forest)')}</div>
            <div class="featured-details">
                <h4>{html.escape(top_bird.common_name)}</h4>
                <p>{(top_bird.max_confidence*100):.0f}% Match • First heard at {html.escape(top_bird.first_heard_mmss)}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Bingo grid with results
    if bingo_species:
        played_grid = has_played(f"grid_{res_hash}")
        st.markdown(f"<h3>{get_icon('check', 20)} Today's Quest Tiles</h3>", unsafe_allow_html=True)
        st.markdown(ui.bingo_grid(bingo_species, found_names, agged_detections, not played_grid), unsafe_allow_html=True)

    # Walk Timeline
    if raw_list:
        played_timeline = has_played(f"timeline_{res_hash}")
        st.markdown(f"<h3 style='margin-top: 2rem;'>{get_icon('clock', 20)} Timeline</h3>", unsafe_allow_html=True)
        st.markdown(ui.walk_timeline(raw_list, duration, bingo_names, not played_timeline), unsafe_allow_html=True)

    # Field Card
    if st.session_state.last_results_hash != res_hash:
        st.session_state.card_text = None  # reset
        st.session_state.last_results_hash = res_hash
        
    st.markdown(f"<h2 style='margin-top: 2rem;'>{get_icon('calendar', 24)} Field Journal</h2>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 3])
    
    # Generate / Regenerate
    should_generate = False
    if st.session_state.card_text is None:
        should_generate = True
    
    if st.session_state.card_warning:
        with st.container():
            st.warning(st.session_state.card_warning)
            if "Gemma isn't running" in st.session_state.card_warning or "model not found" in st.session_state.card_warning:
                if st.button("Retry Gemma"):
                    should_generate = True
    elif st.session_state.card_text is not None:
        if col1.button("Regenerate Card"):
            should_generate = True
            
    if should_generate:
        loader_placeholder = st.empty()
        loader_placeholder.html(ui.listening_loader("Writing your field card..."))
        
        card_text, card_warn, card_badge = generate_field_card(
            detections=agged_detections,
            missed_species=missed_names,
            walk_date=str(walk_date),
            time_of_day=time_of_day,
            duration_mmss=duration_mmss,
        )
        st.session_state.card_text = card_text
        st.session_state.card_warning = card_warn
        st.session_state.card_badge = card_badge
        
        st.session_state.played_animations.discard(f"card_{res_hash}")
        
        loader_placeholder.empty()
        st.rerun()

    played_card = has_played(f"card_{res_hash}")
    st.markdown(ui.field_card(st.session_state.card_text, st.session_state.card_badge, not played_card), unsafe_allow_html=True)

    # Grass Ratio
    screen_time_s = time.time() - st.session_state.screen_time_start
    played_grass = has_played(f"grass_{res_hash}")
    st.markdown(ui.grass_ratio(duration, screen_time_s, not played_grass), unsafe_allow_html=True)
    
    st.markdown(ui.section_divider(), unsafe_allow_html=True)
    with st.expander("Show detailed detections & save data"):
        if agged_detections:
            st.dataframe([{
                "Species": d.common_name,
                "Scientific Name": d.scientific_name,
                "Detections": d.count,
                "Max Conf": f"{d.max_confidence:.0%}",
                "First Heard": d.first_heard_mmss,
            } for d in agged_detections], use_container_width=True)
            
        walks_dir = Path(config.WALKS_DIR)
        walks_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = "sample_" if is_sample else "walk_"
        walk_file = walks_dir / f"{prefix}{timestamp}.json"

        walk_data = build_walk_data(
            detections=agged_detections,
            missed_species=missed_names,
            bingo_species=bingo_names,
            walk_date=str(walk_date),
            time_of_day=time_of_day,
            duration_mmss=duration_mmss,
            latitude=latitude,
            longitude=longitude,
            week=birdnet_week,
            threshold=confidence,
            processing_time_s=process_time,
            model_name=config.OLLAMA_MODEL,
            card_text=st.session_state.card_text,
            card_warning=st.session_state.card_warning,
        )
        if is_sample:
            walk_data["is_sample"] = True
            
        if not is_sample:
            if st.button("Save Walk Data"):
                walk_file.write_text(json.dumps(walk_data, indent=2), encoding="utf-8")
                st.success(f"Walk saved to `{walk_file}`")
        else:
            st.caption("Sample data (not saved to walk logs).")
else:
    # Default Hero with no custom waveform
    hero_placeholder.markdown(hero.build_hero(time_of_day, not hero_played, None), unsafe_allow_html=True)
    
    st.markdown("""
    <div class="panel section-fade" style="text-align: center; padding: 40px 20px;">
        <h3 style="margin-bottom: 10px; color: var(--muted-sky);">Your results will appear here</h3>
        <p style="opacity: 0.8; max-width: 400px; margin: 0 auto;">Upload your walk recording above and we'll listen for the birds.</p>
    </div>
    """, unsafe_allow_html=True)
