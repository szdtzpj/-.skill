# -*- coding: utf-8 -*-
"""Create and append immersive xianqin dialogue benji logs."""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
from pathlib import Path


DEFAULT_RECORD_NAME = "新元记"
DEFAULT_LOG_ROOT = "xianqin-dialogue-logs"
PROFILE_NAME = "royal-profile.json"
INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def now_iso() -> str:
    return _dt.datetime.now().astimezone().isoformat(timespec="seconds")


def sanitize_part(value: str) -> str:
    value = INVALID_FILENAME_CHARS.sub("_", value.strip())
    value = re.sub(r"\s+", "", value)
    return value or "无名王"


def log_root(path: str | None) -> Path:
    return Path(path or DEFAULT_LOG_ROOT)


def profile_path(root: Path) -> Path:
    return root / PROFILE_NAME


def log_path(root: Path, record_name: str, king_title: str) -> Path:
    record_name = sanitize_part(record_name or DEFAULT_RECORD_NAME)
    king_title = sanitize_part(king_title)
    return root / f"《{record_name}·{king_title}本纪》.txt"


def load_profile(root: Path) -> dict:
    path = profile_path(root)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_profile(root: Path, data: dict) -> None:
    root.mkdir(parents=True, exist_ok=True)
    profile_path(root).write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def ensure_log_header(path: Path, profile: dict) -> None:
    if path.exists():
        return
    title = profile.get("king_title", "无名王")
    record = profile.get("record_name", DEFAULT_RECORD_NAME)
    basis = profile.get("basis", "")
    lines = [
        f"《{record}·{title}本纪》",
        "",
        f"王号：{title}",
        f"纪名：{record}",
        f"建档：{profile.get('created_at', now_iso())}",
    ]
    if profile.get("region"):
        lines.append(f"地域：{profile['region']}")
    if profile.get("virtue"):
        lines.append(f"取号：{profile['virtue']}")
    if basis:
        lines.append(f"缘由：{basis}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def command_init(args: argparse.Namespace) -> int:
    root = log_root(args.log_root)
    record_name = args.record_name or DEFAULT_RECORD_NAME
    profile = {
        "king_title": args.king_title,
        "record_name": record_name,
        "region": args.region or "",
        "virtue": args.virtue or "",
        "story": args.story or "",
        "basis": args.basis or "",
        "created_at": now_iso(),
    }
    write_profile(root, profile)
    path = log_path(root, record_name, args.king_title)
    root.mkdir(parents=True, exist_ok=True)
    ensure_log_header(path, profile)
    print(json.dumps({"profile_path": str(profile_path(root)), "log_path": str(path)}, ensure_ascii=False))
    return 0


def read_entry(args: argparse.Namespace) -> str:
    if args.input:
        if args.input == "-":
            return sys.stdin.read()
        return Path(args.input).read_text(encoding="utf-8")
    if args.entry:
        return args.entry
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise SystemExit("append requires --entry, --input, or stdin")


def command_append(args: argparse.Namespace) -> int:
    root = log_root(args.log_root)
    profile = load_profile(root)
    king_title = args.king_title or profile.get("king_title")
    if not king_title:
        raise SystemExit("missing king title; run init first or pass --king-title")
    record_name = args.record_name or profile.get("record_name") or DEFAULT_RECORD_NAME
    path = log_path(root, record_name, king_title)
    root.mkdir(parents=True, exist_ok=True)
    if not profile:
        profile = {
            "king_title": king_title,
            "record_name": record_name,
            "created_at": now_iso(),
        }
    ensure_log_header(path, profile)

    entry = read_entry(args).strip()
    if not entry:
        raise SystemExit("empty entry")

    stamp = now_iso()
    block = [f"\n## {stamp}"]
    if args.user_prompt:
        block.extend(["", f"原问：{args.user_prompt.strip()}"])
    block.extend(["", entry, ""])
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(block))
    print(json.dumps({"log_path": str(path), "appended_at": stamp}, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="create or replace the royal profile and log header")
    init.add_argument("--king-title", required=True)
    init.add_argument("--record-name", default=DEFAULT_RECORD_NAME)
    init.add_argument("--region")
    init.add_argument("--virtue")
    init.add_argument("--story")
    init.add_argument("--basis")
    init.add_argument("--log-root")
    init.set_defaults(func=command_init)

    append = sub.add_parser("append", help="append one dialogue response to the benji log")
    append.add_argument("--king-title")
    append.add_argument("--record-name")
    append.add_argument("--user-prompt")
    append.add_argument("--entry")
    append.add_argument("--input")
    append.add_argument("--log-root")
    append.set_defaults(func=command_append)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
