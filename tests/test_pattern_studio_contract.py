from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_pattern_studio_exposes_real_authoring_surface():
    html = (ROOT / "app/static/index.html").read_text()
    js = (ROOT / "app/static/app.js").read_text()
    assert 'data-view="editor"' in html
    assert 'id="editor-view"' in html
    assert 'id="pattern-canvas"' in html
    assert 'data-editor-action="new-piece"' in html
    assert 'data-editor-action="save-project"' in html
    assert 'pointerdown' in js
    assert 'localStorage' in js
    assert 'download-project' in js
