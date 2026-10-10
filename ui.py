import html
import re
from icons import get_icon

def minify(html_str: str) -> str:
    """Strips leading whitespace and blank lines to prevent Streamlit from rendering as Markdown code blocks."""
    lines = [line.strip() for line in html_str.splitlines() if line.strip()]
    return "".join(lines)

def wrap_play_once(html_str: str, play_once: bool, wrapper_tag="div") -> str:
    """Wraps HTML in a play-once container if true."""
    if play_once:
        return f'<{wrapper_tag} class="play-once">{html_str}</{wrapper_tag}>'
    return html_str

def section_divider() -> str:
    return minify('<div class="divider"></div>')

def ambient_particles(time_of_day: str) -> str:
    particles = '<div class="particles">'
    if time_of_day == "Dawn":
        for i in range(8):
            delay = i * -2.5
            x = (i * 17) % 100
            particles += f'<div class="p-mote" style="left: {x}vw; width: {4+i}px; height: {4+i}px; animation-delay: {delay}s; animation-duration: {10+i}s;"></div>'
    elif time_of_day == "Day":
        for i in range(8):
            delay = i * -3.1
            y = (i * 23) % 100
            particles += f'<div class="p-leaf" style="top: {y}vh; animation-delay: {delay}s; animation-duration: {8+i}s;"></div>'
    else: # Dusk
        for i in range(8):
            delay = i * -1.7
            x = (i * 31) % 100
            y = (i * 19) % 100
            particles += f'<div class="p-firefly" style="left: {x}vw; top: {y}vh; animation-delay: {delay}s; animation-duration: {4+i%3}s;"></div>'
    particles += '</div>'
    return minify(particles)

def listening_loader(text: str) -> str:
    bars = "".join([f'<div class="eq-bar" style="animation-delay: {-0.1 * i}s"></div>' for i in range(7)])
    return minify(f"""
    <div style="padding: 1.5rem 0;">
        <div class="equalizer">{bars}</div>
        <div class="loader-text">{html.escape(text)}</div>
    </div>
    """)

def bingo_grid(bingo_species: list, found_names: set, agged_detections: list, play_once: bool) -> str:
    grid_html = '<div class="bingo-grid" id="quest-section">'
    
    for i, (common, scientific, _) in enumerate(bingo_species):
        delay = i * 0.05
        if common in found_names:
            max_c = next((d.max_confidence for d in agged_detections if d.common_name == common), 0)
            grid_html += f"""
            <div class="bingo-tile found" style="animation-delay: {delay}s">
                <div class="tile-icon">{get_icon('bird', 20, 'var(--success-green)')}</div>
                <div class="tile-name">{html.escape(common)}</div>
                <div class="tile-conf">{(max_c*100):.0f}% Match</div>
                <div class="check-icon">{get_icon('check', 40, 'var(--success-green)', 3)}</div>
            </div>
            """
        else:
            grid_html += f"""
            <div class="bingo-tile missed" style="animation-delay: {delay}s">
                <div class="tile-icon">{get_icon('bird', 20, 'var(--muted-sky)')}</div>
                <div class="tile-name">{html.escape(common)}</div>
                <div class="tile-missed">Pending discovery</div>
            </div>
            """
            
    grid_html += '</div>'
    return minify(wrap_play_once(grid_html, play_once))

def waveform_svg(peaks: list[float], play_once: bool) -> str:
    if not peaks: return ""
    svg = '<svg class="waveform-svg" viewBox="0 0 100 20" preserveAspectRatio="none">'
    bar_width = 100 / len(peaks)
    for i, p in enumerate(peaks):
        h = max(0.5, p * 20)
        y = 20 - h
        delay = (i / len(peaks)) * 0.4
        svg += f'<rect class="wave-bar" x="{i*bar_width}" y="{y}" width="{bar_width*0.8}" height="{h}" style="animation-delay: {delay}s" />'
    svg += '</svg>'
    return minify(wrap_play_once(svg, play_once))

def score_ring(found: int, total: int, play_once: bool) -> str:
    if total == 0: total = 1
    pct = (found / total) * 100
    
    style_str = f'style="--p: {pct};"' if play_once else f'style="--p: {pct}; animation: none;"'
    
    html_out = f"""
    <div class="score-section">
        <div class="score-ring" {style_str}>
            <div class="score-inner">
                <span class="score-number">{found}</span>
                <span class="score-total">of {total}</span>
            </div>
        </div>
        <div class="score-label">
            <h3>bingo birds found</h3>
            <p>Heard on this walk</p>
        </div>
    </div>
    """
    return minify(wrap_play_once(html_out, play_once))

def walk_timeline(raw_detections: list, duration_s: float, bingo_names: list, play_once: bool) -> str:
    if not raw_detections or duration_s <= 0:
        return minify('<div class="timeline-container"><p style="text-align: center; opacity: 0.7;">No detections on this walk. Enjoy the quiet!</p></div>')
        
    counts = {}
    for d in raw_detections:
        counts[d.species_key] = counts.get(d.species_key, 0) + 1
        
    # Sort: bingo birds first by count, then other birds by count
    def sort_key(key):
        common = key.split("_", 1)[1] if "_" in key else key
        is_bingo = common in bingo_names
        return (not is_bingo, -counts[key])
        
    sorted_keys = sorted(counts.keys(), key=sort_key)
    top_keys = sorted_keys[:12]
    extra_count = len(sorted_keys) - 12
    
    html_out = """
    <div class="timeline-container">
        <div class="timeline-header">
            <h3>Your walk, bird by bird</h3>
            <p>Each dot is a moment that bird was heard. Bigger, brighter dot = more confident.</p>
        </div>
        <div class="timeline-legend">
            <div class="legend-item"><div class="legend-dot bingo"></div> Bingo bird</div>
            <div class="legend-item"><div class="legend-dot other"></div> Other bird</div>
        </div>
        <div class="timeline-scroll">
            <div class="timeline-plot-area">
    """
    
    animated_dots = 0
    max_anim_dots = 150
    
    for i, key in enumerate(top_keys):
        common = key.split("_", 1)[1] if "_" in key else key
        is_bingo = common in bingo_names
        dot_class = "bingo" if is_bingo else "other"
        det_count = counts[key]
        
        row_html = f'<div class="timeline-row"><div class="timeline-label" title="{html.escape(common)}">{html.escape(common)}</div><div class="timeline-track">'
        
        species_dets = [d for d in raw_detections if d.species_key == key]
        for d in species_dets:
            pct_x = (d.start_s / duration_s) * 100
            if pct_x > 100: pct_x = 100
            
            size = int(8 + (12 * d.confidence))
            opacity = 0.55 + (0.45 * d.confidence)
            
            delay = 0.0
            if play_once and animated_dots < max_anim_dots:
                delay = (pct_x / 100) * 1.5
                animated_dots += 1
            
            title = f"{html.escape(common)} · {int(d.start_s//60):02d}:{int(d.start_s%60):02d} · {d.confidence:.0%}"
            
            style = f"left: {pct_x}%; width: {size}px; height: {size}px; opacity: {opacity};"
            if delay > 0:
                style += f" animation-delay: {delay}s;"
                
            row_html += f'<div class="timeline-dot {dot_class}" style="{style}" title="{title}"></div>'
            
        row_html += f'</div><div class="timeline-count">×{det_count}</div></div>'
        html_out += row_html
        
    if extra_count > 0:
        html_out += f'<div class="timeline-row"><div class="timeline-label" style="width: 100%;">+{extra_count} more species (see the table)</div></div>'
        
    # Axis
    html_out += '<div class="timeline-axis">'
    intervals = [15, 30, 60, 120, 300, 600]
    tick_interval = 60
    for interval in intervals:
        if (duration_s / interval) <= 6:
            tick_interval = interval
            break
            
    for t in range(0, int(duration_s) + 1, tick_interval):
        pct_x = (t / duration_s) * 100
        html_out += f'<div class="gridline" style="left: {pct_x}%;"></div>'
        html_out += f'<div class="axis-label" style="left: {pct_x}%;">{t//60:02d}:{t%60:02d}</div>'
    
    html_out += '</div></div></div></div>'
    return minify(wrap_play_once(html_out, play_once))

def field_card(text: str, is_fallback: bool, play_once: bool) -> str:
    sentences = re.split(r'(?<=[.!?]) +', text.strip())
    
    content = ""
    for i, sentence in enumerate(sentences):
        delay = i * 0.5
        content += f'<span class="card-sentence" style="animation-delay: {delay}s;">{html.escape(sentence)} </span>'
        
    badge_text = "TEMPLATE CARD" if is_fallback else "VERIFIED AGAINST DETECTIONS"
    
    written_by_html = ""
    if not is_fallback:
        written_by_html = f"""
        <div style="font-family: sans-serif; font-size: 0.75rem; color: rgba(27,42,34,0.6); margin-top: 8px;">
            {get_icon("leaf", 12)} Written by Gemma, on this laptop, offline
        </div>
        """
        
    html_out = f"""
    <div class="field-card-wrapper">
        <div class="field-card journal-page">
            <p>{content}</p>
            <div class="card-badge">{get_icon("check", 14)} {badge_text}</div>
            {written_by_html}
        </div>
    </div>
    """
    return minify(wrap_play_once(html_out, play_once))

def grass_ratio(duration_s: float, screen_s: float, play_once: bool) -> str:
    audio_m = duration_s / 60 if duration_s > 0 else 1
    screen_m = screen_s / 60
    pct_outside = min(100, (audio_m / (audio_m + screen_m)) * 100)
    
    dur_str = f"{int(duration_s//60)}:{int(duration_s%60):02d}"
    scr_str = f"{int(screen_m)}:{int(screen_s%60):02d}"
    
    html_out = f"""
    <div class="panel">
        <div class="panel-title">{get_icon('leaf', 20)} Grass Ratio</div>
        <div class="grass-stats">
            <span>{dur_str} outside</span>
            <span>{scr_str} on screen</span>
        </div>
        <div class="grass-track">
            <div class="grass-fill" style="width: {pct_outside}%;"></div>
        </div>
        <div style="font-size: 0.8rem; opacity: 0.7; margin-top: 10px;">(Screen time measured while this page is open)</div>
    </div>
    """
    return minify(wrap_play_once(html_out, play_once))

def format_time(s: float) -> str:
    if s < 0: return "0:00"
    return f"{int(s//60)}:{int(s%60):02d}"

def processing_panel(state: str, file_name: str, file_size_mb: float, duration_s: float, progress_pct: float, elapsed_s: float, remaining_s: float, error_msg: str, waveform=None, detections=None, bingo_names=None, is_complete=False) -> str:
    if waveform is None or len(waveform) == 0:
        waveform = [0.05] * 100
    if detections is None:
        detections = []
    if bingo_names is None:
        bingo_names = []
        
    bingo_set = set(bingo_names)
    
    if is_complete:
        title_text = "Chorus complete"
        header_icon = get_icon("check", 20, "var(--success-green)")
        pct_text = ""
        sub_text = f"Walk analyzed: {format_time(duration_s)} of audio in {format_time(elapsed_s)}"
    else:
        title_text = "Listening to your walk"
        dot_delay = -(elapsed_s % 1.5) if elapsed_s else 0
        header_icon = f'<div class="pulsing-dot" style="animation-delay: {dot_delay}s"></div>'
        pct_text = f"{int(progress_pct * 100)}%"
        sub_text = "Please wait. Keep this tab open and leave the settings alone until it finishes."
        if state == "error":
            title_text = "Analysis failed"
            header_icon = get_icon("alert-triangle", 20, "var(--warning-amber)")
            pct_text = ""
            sub_text = "Something went wrong."

    header_html = f'<div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 5px;"><div style="display: flex; align-items: center; gap: 10px;">{header_icon}<h3 style="margin: 0; color: var(--cream); font-size: 1.2rem;">{title_text}</h3></div><div style="font-size: 1.5rem; font-weight: bold; color: var(--muted-sky);">{pct_text}</div></div><div style="font-size: 0.85rem; opacity: 0.8; margin-bottom: 20px;">{sub_text}</div>'

    bar_width = 100 / len(waveform)
    
    base_bars = ""
    overlay_bars = ""
    for i, amp in enumerate(waveform):
        h = max(2, int(amp * 100))
        left = i * bar_width
        base_bars += f'<div style="position: absolute; bottom: 0; left: {left}%; width: {bar_width}%; height: {h}%; background: rgba(255,255,255,0.15); border-radius: 2px 2px 0 0;"></div>'
        overlay_bars += f'<div style="position: absolute; bottom: 0; left: {left}%; width: {bar_width}%; height: {h}%; background: linear-gradient(to top, var(--leaf-green), var(--warning-amber)); border-radius: 2px 2px 0 0;"></div>'

    dots_html = ""
    display_dets = detections[-150:] if len(detections) > 150 else detections
    
    unique_birds = set()
    bingo_found = set()
    
    for det in display_dets:
        parts = det.species_key.split("_", 1)
        raw_c = parts[1].strip() if len(parts) == 2 else parts[0].strip()
        c_name = html.escape(raw_c)
        unique_birds.add(c_name)
        if c_name in bingo_set:
            bingo_found.add(c_name)
            dot_color = "var(--leaf-green)"
            ring = "box-shadow: 0 0 0 2px rgba(34, 229, 139, 0.4);"
        else:
            dot_color = "var(--muted-sky)"
            ring = ""
            
        pos_pct = (det.start_s / duration_s * 100) if duration_s > 0 else 0
        title_attr = f"{c_name} &middot; {format_time(det.start_s)} &middot; {int(det.confidence*100)}%"
        dots_html += f'<div title="{title_attr}" style="position: absolute; bottom: 10px; left: {pos_pct}%; width: 6px; height: 6px; background: {dot_color}; border-radius: 50%; {ring} z-index: 2; transform: translateX(-50%);"></div>'

    playhead_pos = progress_pct * 100
    playhead = f'<div style="position: absolute; top: 0; bottom: 0; left: {playhead_pos}%; width: 2px; background: var(--warning-amber); box-shadow: 0 0 6px var(--warning-amber); z-index: 3;"></div>'
    
    if is_complete:
        overlay_clip = "inset(0 0 0 0)"
        playhead = ""
    else:
        overlay_clip = f"inset(0 calc(100% - {playhead_pos}%) 0 0)"
        
    if state == "error":
        overlay_clip = "inset(0 100% 0 0)"
        playhead = ""
        base_bars = base_bars.replace("0.15", "0.05")

    waveform_html = f'<div style="position: relative; height: 90px; margin-bottom: 5px; background: rgba(0,0,0,0.2); border-radius: 4px; overflow: hidden;"><div style="position: absolute; inset: 0;">{base_bars}</div><div style="position: absolute; inset: 0; clip-path: {overlay_clip}; transition: clip-path 0.3s linear;">{overlay_bars}</div>{dots_html}{playhead}</div><div style="display: flex; justify-content: space-between; font-size: 0.7rem; opacity: 0.6; margin-bottom: 20px;"><span>0:00</span><span>{format_time(duration_s/2)}</span><span>{format_time(duration_s)}</span></div>'

    chips_html = ""
    if not unique_birds:
        chips_html = '<div style="font-size: 0.85rem; opacity: 0.6; font-style: italic;">Listening... nothing yet</div>'
    else:
        counts = {}
        first_seen = {}
        for det in detections:
            parts = det.species_key.split("_", 1)
            raw_c = parts[1].strip() if len(parts) == 2 else parts[0].strip()
            c = html.escape(raw_c)
            counts[c] = counts.get(c, 0) + 1
            if c not in first_seen:
                first_seen[c] = det.start_s
                
        sorted_birds = sorted(counts.keys(), key=lambda x: first_seen[x], reverse=True)
        
        visible_birds = sorted_birds[:10]
        for b in visible_birds:
            is_bingo = b in bingo_set
            bg = "rgba(34, 229, 139, 0.2)" if is_bingo else "rgba(127, 178, 201, 0.2)"
            border = "var(--leaf-green)" if is_bingo else "var(--muted-sky)"
            icon = get_icon("check", 12, border) if is_bingo else get_icon("bird", 12, border)
            chips_html += f'<div style="display: inline-flex; align-items: center; gap: 4px; background: {bg}; border: 1px solid {border}; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; margin: 0 4px 4px 0;">{icon} {b} &times;{counts[b]}</div>'
            
        if len(sorted_birds) > 10:
            chips_html += f'<div style="display: inline-flex; align-items: center; font-size: 0.75rem; opacity: 0.7; padding: 2px 4px;">+{len(sorted_birds)-10} more</div>'

    ticker_html = f'<div style="margin-bottom: 15px;"><div style="font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1px; opacity: 0.6; margin-bottom: 6px;">Heard so far</div><div>{chips_html}</div></div>'

    if is_complete:
        stats_text = f"{len(unique_birds)} species &middot; {len(bingo_found)} of {len(bingo_set)} bingo birds"
    else:
        est_text = f"About {int(remaining_s)} s left (estimate)" if remaining_s >= 0 and progress_pct > 0.05 else "Estimating time..."
        stats_text = f"Elapsed {format_time(elapsed_s)} &middot; {est_text} &middot; {len(bingo_found)} of {len(bingo_set)} bingo birds heard so far"
        
    stats_html = f'<div style="font-size: 0.8rem; opacity: 0.8; margin-bottom: 20px; background: rgba(255,255,255,0.05); padding: 8px 12px; border-radius: 6px;">{stats_text}</div>'

    def get_step_state(step_name):
        order = {"preparing": 1, "listening": 2, "writing": 3, "done": 4, "error": -1}
        cur = order.get(state, 0)
        this = order.get(step_name, 0)
        
        if state == "error":
            is_ollama_err = "Ollama" in error_msg or "Gemma" in error_msg
            if is_ollama_err:
                if this < 3: return "done"
                if this == 3: return "error"
                return "pending"
            else:
                if this == 1: return "error"
                return "pending"
                
        if cur > this: return "done"
        if cur == this: return "active"
        return "pending"

    steps = [
        (1, "Upload received", get_step_state("preparing")),
        (2, "Preparing audio", get_step_state("listening")),
        (3, "Listening for birds", get_step_state("writing")),
        (4, "Writing your field card", get_step_state("done"))
    ]
    
    steps_html = '<div style="display: flex; gap: 10px; flex-wrap: wrap; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 15px;">'
    for num, label, s_state in steps:
        color = "var(--cream)" if s_state in ("active", "done") else "rgba(255,255,255,0.3)"
        if s_state == "error": color = "var(--warning-amber)"
        
        icon = get_icon("check", 14, color) if s_state == "done" else (get_icon("loader", 14, color) if s_state == "active" else (get_icon("alert-triangle", 14, color) if s_state == "error" else f'<span style="display:inline-block; width:14px; text-align:center; font-size:10px;">{num}</span>'))
        
        cls = "step-item active" if s_state == "active" else "step-item"
            
        detail = ""
        if s_state == "error":
            if "Ollama" in error_msg or "Gemma" in error_msg:
                detail = '<div style="font-size:0.7rem; margin-top:2px; opacity:0.8;">Template card (Gemma not running)</div>'
            else:
                detail = f'<div style="font-size:0.7rem; margin-top:2px; opacity:0.8;">{error_msg}</div>'
                
        steps_html += f'<div class="{cls}" style="display: flex; align-items: flex-start; gap: 6px; color: {color}; font-size: 0.8rem; flex: 1; min-width: 120px;"><div>{icon}</div><div><div>{label}</div>{detail}</div></div>'
    steps_html += '</div>'

    action_btn = ""
    if is_complete:
        action_btn = '<div style="margin-top: 20px; text-align: center;"><a href="#what-you-discovered" style="display: inline-block; padding: 10px 20px; background: var(--warning-amber); color: #000; text-decoration: none; border-radius: 20px; font-weight: bold; font-size: 0.9rem;">See your results</a></div>'

    anim_cls = " play-once" if is_complete else ""
    panel_html = f'<div class="panel processing-panel section-fade{anim_cls}">{header_html}{waveform_html}{ticker_html}{stats_html}{steps_html}{action_btn}</div>'
    
    return minify(panel_html)

