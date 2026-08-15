from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .errors import BrazenError
from .fit_corrections import is_trainable_correction, validate_fit_correction
from .geometry import Pattern, PatternPiece, Point, Polyline, pattern_to_svg
from .measurements import MeasurementSession, RepeatabilityStudy, tolerance_budget_from_study


def _load(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BrazenError(f"cannot read JSON {path}: {exc}") from exc


def _pattern(data: dict) -> Pattern:
    pieces = []
    for p in data["pieces"]:
        parsed_contours = []
        for c in p["contours"]:
            closed = c.get("closed", True)
            if not isinstance(closed, bool):
                raise ValueError(f"{c.get('name', '<unnamed>')}: closed must be boolean")
            parsed_contours.append(Polyline(c["name"], tuple(Point(x["xMm"], x["yMm"]) for x in c["points"]), closed))
        contours = tuple(parsed_contours)
        pieces.append(PatternPiece(p["pieceId"], p["blockVersion"], contours, p.get("seamGroups", {})))
    return Pattern(data["compilerVersion"], tuple(pieces), data.get("sourceSpecVersion", "0.1"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bpe")
    sub = parser.add_subparsers(dest="command", required=True)
    repeat = sub.add_parser("repeatability")
    repeat.add_argument("input", type=Path)
    repeat.add_argument("output", type=Path)
    repeat.add_argument("--max-relative-tem-pct", type=float, default=None, help="approved low inter-measurer TEM policy; omit to fail closed")
    fit = sub.add_parser("validate-fit")
    fit.add_argument("input", type=Path)
    fit.add_argument("--tolerance-fit-mm", type=float, required=True)
    hash_cmd = sub.add_parser("hash")
    hash_cmd.add_argument("input", type=Path)
    svg = sub.add_parser("svg")
    svg.add_argument("input", type=Path)
    svg.add_argument("-o", "--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "repeatability":
            data = _load(args.input)
            sessions = tuple(MeasurementSession.from_dict(row) for row in data["sessions"])
            study = RepeatabilityStudy(sessions)
            results = [r.__dict__ for r in study.results(max_relative_tem_pct=args.max_relative_tem_pct)]
            budget = tolerance_budget_from_study(study, max_relative_tem_pct=args.max_relative_tem_pct)
            args.output.write_text(json.dumps({"results": results, "toleranceBudget": budget.__dict__}, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({"status": "PASS", "output": str(args.output), "measurements": len(results)}))
        elif args.command == "validate-fit":
            record = _load(args.input)
            errors = validate_fit_correction(record, tolerance_fit_mm=args.tolerance_fit_mm)
            result = {"status": "PASS" if not errors else "FAIL", "errors": errors, "trainable": is_trainable_correction(record, tolerance_fit_mm=args.tolerance_fit_mm)}
            print(json.dumps(result, indent=2))
            return 0 if not errors else 2
        elif args.command == "hash":
            pattern = _pattern(_load(args.input))
            pattern.validate_closed_contours()
            print(json.dumps({"status": "PASS", "patternHash": pattern.content_hash(), "compilerVersion": pattern.compiler_version}))
        elif args.command == "svg":
            pattern = _pattern(_load(args.input))
            args.output.write_text(pattern_to_svg(pattern), encoding="utf-8")
            print(json.dumps({"status": "PASS", "output": str(args.output), "patternHash": pattern.content_hash()}))
        return 0
    except (BrazenError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
