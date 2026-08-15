import json
import os
import subprocess
import sys
from pathlib import Path

from brazen_pattern_engine.cli import main


def test_cli_hash_and_svg(tmp_path, capsys):
    pattern = {
        "compilerVersion": "compiler-v0.1",
        "pieces": [{"pieceId": "left", "blockVersion": "Block-v1.0", "contours": [{"name": "outer", "closed": True, "points": [{"xMm": 0, "yMm": 0}, {"xMm": 10, "yMm": 0}, {"xMm": 10, "yMm": 20}, {"xMm": 0, "yMm": 20}]}]}],
    }
    source = tmp_path / "pattern.json"
    output = tmp_path / "pattern.svg"
    source.write_text(json.dumps(pattern), encoding="utf-8")
    assert main(["hash", str(source)]) == 0
    assert "patternHash" in capsys.readouterr().out
    assert main(["svg", str(source), "-o", str(output)]) == 0
    assert output.exists()
    assert "not Phase 5 manufacturing approval" in output.read_text(encoding="utf-8")


def test_module_entrypoint_executes_cli(tmp_path):
    source = tmp_path / "pattern.json"
    source.write_text(json.dumps({"compilerVersion": "compiler-v0.1", "pieces": [{"pieceId": "left", "blockVersion": "Block-v1.0", "contours": [{"name": "outer", "points": [{"xMm": 0, "yMm": 0}, {"xMm": 10, "yMm": 0}, {"xMm": 10, "yMm": 20}]}]}]}), encoding="utf-8")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).parents[1] / "src")
    result = subprocess.run([sys.executable, "-m", "brazen_pattern_engine.cli", "hash", str(source)], capture_output=True, text=True, check=False, env=env)
    assert result.returncode == 0
    assert "patternHash" in result.stdout


def test_cli_rejects_string_closed_flag(tmp_path):
    source = tmp_path / "open.json"
    source.write_text(json.dumps({"compilerVersion": "compiler-v0.1", "pieces": [{"pieceId": "left", "blockVersion": "Block-v1.0", "contours": [{"name": "outer", "closed": "false", "points": [{"xMm": 0, "yMm": 0}, {"xMm": 10, "yMm": 0}, {"xMm": 10, "yMm": 20}]}]}]}), encoding="utf-8")
    assert main(["hash", str(source)]) == 2
