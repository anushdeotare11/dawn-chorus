import urllib.parse
from ui import minify
import math

def make_data_uri(svg_str: str) -> str:
    # Minimal SVG wrapper to ensure valid XML
    if not svg_str.startswith("<svg"):
        svg_str = f'<svg xmlns="http://www.w3.org/2000/svg" width="800" height="400" viewBox="0 0 800 400">{svg_str}</svg>'
    encoded = urllib.parse.quote(svg_str)
    return f"url('data:image/svg+xml;utf8,{encoded}')"

def smooth_peaks(peaks: list[float], window_size: int = 5) -> list[float]:
    if not peaks: return []
    # Compress dynamic range (square root)
    compressed = [math.sqrt(p) for p in peaks]
    # Moving average
    smoothed = []
    for i in range(len(compressed)):
        start = max(0, i - window_size // 2)
        end = min(len(compressed), i + window_size // 2 + 1)
        window = compressed[start:end]
        smoothed.append(sum(window) / len(window))
    return smoothed

def build_hero(time_of_day: str, play_once: bool = True, peaks: list[float] = None) -> str:
    # Gradients
    gradients = {
        "Dawn": "linear-gradient(180deg, #1B2A4A 0%, #5B4B7A 40%, #E88A5B 80%, #F6C177 100%)",
        "Day": "linear-gradient(180deg, #2F7FB5 0%, #8FD0E8 60%, #EAF6E8 100%)",
        "Dusk": "linear-gradient(180deg, #1E1B4B 0%, #6B3F7A 50%, #E0703F 85%, #F2B05E 100%)"
    }
    sky_bg = gradients.get(time_of_day, gradients["Day"])
    
    # Layers
    layers = []
    
    # Stars (only for Dawn and Dusk)
    if time_of_day in ["Dawn", "Dusk"]:
        stars_svg = ""
        import random
        random.seed(42) # Deterministic
        for _ in range(15):
            x = random.randint(10, 790)
            y = random.randint(10, 150)
            r = random.uniform(0.5, 1.5)
            stars_svg += f'<circle cx="{x}" cy="{y}" r="{r}" fill="white" opacity="{random.uniform(0.4, 1.0)}" />'
        layers.append(f'<div class="hero-layer hero-stars" style="background-image: {make_data_uri(stars_svg)};"></div>')
        
    # Sun - place low, right of center (75%), behind hills
    sun_x = 600
    sun_y = 230
    sun_fill = "#FFF7D6" if time_of_day == "Day" else "#FFEBB5"
    sun_svg = f'<circle cx="{sun_x}" cy="{sun_y}" r="35" fill="{sun_fill}" filter="blur(6px)" opacity="0.6" /><circle cx="{sun_x}" cy="{sun_y}" r="20" fill="{sun_fill}" />'
    sun_class = "hero-layer hero-sun"
    if play_once: sun_class += " play-once-sun"
    layers.append(f'<div class="{sun_class}" style="background-image: {make_data_uri(sun_svg)};"></div>')
    
    # Far hills
    far_hills_svg = '<path d="M -50 400 L -50 250 Q 150 180 400 240 T 900 200 L 900 400 Z" fill="#2E4A59" opacity="0.7" />'
    layers.append(f'<div class="hero-layer" style="background-image: {make_data_uri(far_hills_svg)};"></div>')
    
    # Clouds - keep in upper corners
    cloud1_svg = '<path d="M 50 100 Q 70 80 100 100 Q 120 90 140 110 Q 100 130 50 110 Z" fill="rgba(255,255,255,0.15)" /><path d="M 650 60 Q 680 40 720 70 Q 750 50 780 80 Q 720 100 650 70 Z" fill="rgba(255,255,255,0.15)" />'
    cloud2_svg = '<path d="M 200 70 Q 230 50 280 80 Q 300 70 330 90 Q 280 100 200 80 Z" fill="rgba(255,255,255,0.1)" />'
    layers.append(f'<div class="hero-layer hero-cloud1" style="background-image: {make_data_uri(cloud1_svg)};"></div>')
    layers.append(f'<div class="hero-layer hero-cloud2" style="background-image: {make_data_uri(cloud2_svg)};"></div>')
    
    # Mid hills
    mid_hills_svg = '<path d="M -50 400 L -50 280 Q 250 220 500 280 T 950 260 L 950 400 Z" fill="#3F6B4F" />'
    layers.append(f'<div class="hero-layer" style="background-image: {make_data_uri(mid_hills_svg)};"></div>')

    # Waveform Ridge (Front)
    if not peaks:
        # Deterministic default wave (gentle birdsong)
        peaks = [0.05, 0.1, 0.2, 0.15, 0.05, 0.2, 0.4, 0.3, 0.1, 0.05, 0.1, 0.2, 0.3, 0.15, 0.05] * 7
        is_real = False
    else:
        is_real = True

    # Smooth the peaks
    smoothed = smooth_peaks(peaks, window_size=5)
    num_peaks = len(smoothed)
    step = 820 / max(1, num_peaks - 1)
    
    # Clamp height to about 22% of hero (hero is 360, so roughly 80px variance)
    # Base is 320, max peak goes up to 240
    ridge_path = "M -10 400 L -10 320"
    for i, p in enumerate(smoothed):
        x = i * step
        h = 320 - (p * 80)
        
        if i == 0:
            ridge_path += f" L {x} {h}"
            continue
            
        prev_x = (i - 1) * step
        prev_p = smoothed[i-1]
        prev_h = 320 - (prev_p * 80)
        cx1 = prev_x + step/2
        cx2 = x - step/2
        ridge_path += f" C {cx1} {prev_h}, {cx2} {h}, {x} {h}"
        
    ridge_path += " L 810 400 Z"
    
    grass_svg = ""
    for i in range(0, 800, 40):
        idx = int((i / 800) * num_peaks)
        if idx < num_peaks:
            gh = 320 - (smoothed[idx] * 80)
            grass_svg += f'<path d="M {i} {gh} L {i-2} {gh-4} M {i+2} {gh} L {i+4} {gh-3}" stroke="#12382A" stroke-width="1" fill="none" />'

    front_ridge_svg = f'<path d="{ridge_path}" fill="#0C2419" />{grass_svg}'
    layers.append(f'<div class="hero-layer" style="background-image: {make_data_uri(front_ridge_svg)};"></div>')
    
    # Mist
    mist_svg = '<rect x="0" y="250" width="800" height="150" fill="url(#mistGrad)" /><defs><linearGradient id="mistGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="rgba(255,255,255,0.0)"/><stop offset="100%" stop-color="rgba(255,255,255,0.15)"/></linearGradient></defs>'
    layers.append(f'<div class="hero-layer hero-mist" style="background-image: {make_data_uri(mist_svg)};"></div>')
    
    # Birds
    bird_svg = '<path d="M0,20 Q10,10 20,20 Q10,15 0,20 Z" fill="#1B2A22" opacity="0.6"/>'
    bird2_svg = '<path d="M0,30 Q15,20 30,30 Q15,25 0,30 Z" fill="#1B2A22" opacity="0.4"/>'
    layers.append(f'<div class="hero-layer hero-bird1" style="background-image: {make_data_uri(bird_svg)};"></div>')
    layers.append(f'<div class="hero-layer hero-bird2" style="background-image: {make_data_uri(bird2_svg)};"></div>')
    layers.append(f'<div class="hero-layer hero-bird3" style="background-image: {make_data_uri(bird_svg)};"></div>')

    layers_html = "".join(layers)
    
    caption_html = ""
    if is_real:
        caption_html = '<div class="hero-waveform-caption">This ridge is the sound of your walk.</div>'
        
    html_out = f"""
    <div class="hero-wrapper" style="background: {sky_bg};">
        {layers_html}
        <div class="hero-content">
            <h1 class="hero-title">Dawn Chorus</h1>
            <div class="hero-tagline">Put your phone away. Listen to the morning.</div>
            <div class="hero-subline">A cinematic, offline bird-listening experience.</div>
            <a href="#quest-section" class="primary-btn">Start today's walk</a>
        </div>
        {caption_html}
    </div>
    """
    return minify(html_out)
