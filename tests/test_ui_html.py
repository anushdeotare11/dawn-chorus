import ui

def test_no_raw_html_markdown_bug():
    """Verify that ui.py functions do not return HTML that Streamlit could parse as Markdown code blocks.
    Streamlit parses lines starting with 4+ spaces, or blank lines, as markdown."""
    
    # Generate some dummy data
    html_outputs = [
        ui.ambient_particles("Day"),
        ui.listening_loader("Test"),
        ui.bingo_grid([("Robin", "Turdus migratorius", 0.5)], set(["Robin"]), [], True),
        ui.waveform_svg([0.1, 0.5, 1.0], True),
        ui.score_ring(1, 12, True),
        ui.walk_timeline([], 60, [], True),
        ui.field_card("A test sentence.", False, True),
        ui.grass_ratio(1200, 60, True),
        ui.section_divider()
    ]
    
    for idx, html_str in enumerate(html_outputs):
        lines = html_str.splitlines()
        for line_idx, line in enumerate(lines):
            # 1. No blank lines
            assert line.strip() != "", f"Blank line found in output {idx} at line {line_idx}"
            # 2. No lines starting with 4+ spaces
            assert not line.startswith("    "), f"Line starts with 4+ spaces in output {idx} at line {line_idx}: {line!r}"
