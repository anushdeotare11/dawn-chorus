import pytest
from unittest.mock import patch, MagicMock
from streamlit.testing.v1 import AppTest

@pytest.mark.slow
def test_render_order_results_before_gemma():
    """Verify that results components are rendered before Gemma is called by inspecting app.py."""
    with open("app.py", "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    score_ring_line = -1
    generate_card_line = -1
    
    for i, line in enumerate(lines):
        if "ui.score_ring(" in line and score_ring_line == -1:
            score_ring_line = i
        if "generate_field_card(" in line and generate_card_line == -1:
            generate_card_line = i
            
    assert score_ring_line != -1, "Could not find score_ring rendering"
    assert generate_card_line != -1, "Could not find generate_field_card call"
    assert score_ring_line < generate_card_line, "Results are rendered after Gemma is called!"
