import pytest
from streamlit.testing.v1 import AppTest
import xml.etree.ElementTree as ET
import urllib.parse
import re

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from hero import build_hero

def test_hero_xml_validity():
    for tod in ["Dawn", "Day", "Dusk"]:
        for peaks in [None, [0.1, 0.5, 1.0]]:
            html_out = build_hero(tod, True, peaks)
            uris = re.findall(r"url\('data:image/svg\+xml;utf8,(.*?)'\)", html_out)
            for uri in uris:
                svg_str = urllib.parse.unquote(uri)
                try:
                    ET.fromstring(svg_str)
                except ET.ParseError as e:
                    pytest.fail(f"Invalid XML generated for {tod}, peaks={peaks}: {e}\nSVG: {svg_str}")
            
            assert "hero-sun" in html_out
            assert "hero-cloud1" in html_out
            assert "hero-layer" in html_out

def test_app_smoke():
    at = AppTest.from_file("app.py").run(timeout=60)
    assert not at.exception, f"App crashed on load: {at.exception[0]}"
    
    # Find the 'Load a sample walk' button and click it
    button_clicked = False
    for btn in at.button:
        if btn.label == "Load a sample walk":
            btn.click().run(timeout=180)
            button_clicked = True
            break
            
    assert button_clicked, "Could not find 'Load a sample walk' button"
    assert not at.exception, f"App crashed after loading sample walk: {at.exception[0]}"
