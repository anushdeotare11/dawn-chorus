import pytest
import ast
from pathlib import Path

def test_no_streamlit_in_cached_functions():
    """Statically scan all files for @st.cache_data decorators and ensure no st. calls inside."""
    root_dir = Path(__file__).resolve().parent.parent
    for py_file in root_dir.glob("*.py"):
        if py_file.name == "venv": continue
        
        with open(py_file, "r", encoding="utf-8") as f:
            code = f.read()
            
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                has_cache = False
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Call) and getattr(dec.func, 'attr', '') == 'cache_data':
                        has_cache = True
                    elif isinstance(dec, ast.Attribute) and dec.attr == 'cache_data':
                        has_cache = True
                
                if has_cache:
                    # Scan for st. calls inside the body
                    for stmt in node.body:
                        for sub_node in ast.walk(stmt):
                            if isinstance(sub_node, ast.Attribute):
                                if isinstance(sub_node.value, ast.Name) and sub_node.value.id == "st":
                                    pytest.fail(f"Found st.{sub_node.attr} call inside cached function '{node.name}' in {py_file.name}")

def test_cache_hit_apptest():
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file("app.py").run(timeout=60)
    assert not at.exception, f"App crashed on load: {at.exception[0]}"
    
    button_clicked = False
    for btn in at.button:
        if btn.label == "Load a sample walk":
            btn.click().run(timeout=180)
            button_clicked = True
            break
            
    assert button_clicked, "Could not find 'Load a sample walk' button"
    assert not at.exception, f"App crashed after loading sample walk: {at.exception[0]}"
    
    # Reload sample to simulate cache hit
    for btn in at.button:
        if btn.label == "Clear sample":
            btn.click().run(timeout=10)
            break
            
    for btn in at.button:
        if btn.label == "Load a sample walk":
            btn.click().run(timeout=10)
            break
            
    assert not at.exception, f"App crashed on cache hit: {at.exception[0]}"
