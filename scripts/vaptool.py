#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import stat
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

VERSION = "2.0.6"
RELEASE_URLS = {
    "Darwin": f"https://github.com/Tencent/vap/releases/download/tool{VERSION}/vaptool_mac_v{VERSION}.zip",
    "Windows": f"https://github.com/Tencent/vap/releases/download/tool{VERSION}/vaptool_win_v{VERSION}.zip",
}


def default_home() -> Path:
    env = os.environ.get("VAPTOOL_HOME") or os.environ.get("VAP_TOOL_HOME")
    if env:
        return Path(env).expanduser()
    legacy = Path.home() / ".opencode" / "tools" / "vaptool" / f"tool{VERSION}"
    if legacy.exists():
        return legacy
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home())))
        return base / "vaptool" / f"tool{VERSION}"
    return Path.home() / ".local" / "share" / "vaptool" / f"tool{VERSION}"


def resolve_cmd(value: str | None, fallback: str) -> str | None:
    if value:
        p = Path(value).expanduser()
        if p.exists():
            return str(p.resolve())
        return shutil.which(value)
    return shutil.which(fallback)


def candidate_binary(home: Path, base: str) -> Path | None:
    names = [base]
    if os.name == "nt" and not base.lower().endswith(".exe"):
        names.insert(0, base + ".exe")
    dirs = [home, home / "mac", home / "linux", home / "bin", home / "windows", home / "win"]
    for d in dirs:
        for name in names:
            p = d / name
            if p.is_file():
                return p
    for p in home.rglob("*") if home.exists() else []:
        if p.is_file() and p.name.lower() in {n.lower() for n in names}:
            return p
    return None


def find_animtool(home: Path) -> Path | None:
    direct = home / "animtool.jar"
    if direct.is_file():
        return direct
    matches = list(home.rglob("animtool.jar")) if home.exists() else []
    return matches[0] if matches else None


def safe_extract(zf: zipfile.ZipFile, dest: Path) -> None:
    root = dest.resolve()
    for member in zf.infolist():
        target = (dest / member.filename).resolve()
        if root != target and root not in target.parents:
            raise RuntimeError(f"Unsafe ZIP member: {member.filename}")
    zf.extractall(dest)


def normalize_install_tree(staging: Path, home: Path) -> None:
    anim = find_animtool(staging)
    source = anim.parent if anim else staging
    if source == staging:
        children = [p for p in staging.iterdir() if p.name != "__MACOSX"]
        if len(children) == 1 and children[0].is_dir():
            source = children[0]
    home.mkdir(parents=True, exist_ok=True)
    for child in source.iterdir():
        dest = home / child.name
        if dest.exists():
            if dest.is_dir():
                shutil.rmtree(dest)
            else:
                dest.unlink()
        shutil.move(str(child), str(dest))


def ensure_executable(path: Path | None) -> None:
    if path is None or os.name == "nt":
        return
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def install(args: argparse.Namespace) -> int:
    system = platform.system()
    home = Path(args.home).expanduser().resolve()
    url = args.url or RELEASE_URLS.get(system)
    if not args.archive and not url:
        raise RuntimeError(
            f"No official automatic VapTool bundle is configured for {system}. "
            "Use --archive with a local VapTool ZIP or --url with an explicit bundle URL."
        )
    if home.exists() and find_animtool(home) and not args.force:
        print(json.dumps({"status": "already-installed", "home": str(home)}, ensure_ascii=False))
        return 0
    if args.force and home.exists():
        shutil.rmtree(home)

    with tempfile.TemporaryDirectory(prefix="vaptool_install_") as td:
        tmp = Path(td)
        archive = Path(args.archive).expanduser().resolve() if args.archive else tmp / "vaptool.zip"
        if not args.archive:
            assert url
            print(f"Downloading VapTool {VERSION} from official release...", file=sys.stderr)
            urllib.request.urlretrieve(url, archive)
        if not archive.is_file():
            raise RuntimeError(f"Archive not found: {archive}")
        staging = tmp / "staging"
        staging.mkdir()
        with zipfile.ZipFile(archive) as zf:
            safe_extract(zf, staging)
        normalize_install_tree(staging, home)

    for base in ("ffmpeg", "ffprobe", "mp4edit"):
        ensure_executable(candidate_binary(home, base))
    for start in (home / "mac_start.sh", home / "start.sh"):
        if start.is_file():
            ensure_executable(start)

    report = verify_namespace(home, args)
    if not report["ok"]:
        raise RuntimeError("VapTool installed but verification failed: " + "; ".join(report["errors"]))
    print(json.dumps({"status": "installed", "home": str(home), "version": VERSION, "verify": report}, ensure_ascii=False, indent=2))
    return 0


def verify_namespace(home: Path, args: argparse.Namespace) -> dict[str, object]:
    java = resolve_cmd(getattr(args, "java", None), "java")
    javac = resolve_cmd(getattr(args, "javac", None), "javac")
    system_ffmpeg = resolve_cmd(getattr(args, "ffmpeg", None), "ffmpeg")
    system_ffprobe = resolve_cmd(getattr(args, "ffprobe", None), "ffprobe")
    anim = find_animtool(home)
    vap_ffmpeg = candidate_binary(home, "ffmpeg")
    mp4edit = candidate_binary(home, "mp4edit")

    checks = {
        "home": str(home),
        "java": java,
        "javac": javac,
        "system_ffmpeg": system_ffmpeg,
        "system_ffprobe": system_ffprobe,
        "animtool_jar": str(anim) if anim else None,
        "vaptool_ffmpeg": str(vap_ffmpeg) if vap_ffmpeg else None,
        "mp4edit": str(mp4edit) if mp4edit else None,
    }
    errors = [f"missing {name}" for name, value in checks.items() if name != "home" and not value]
    if not home.is_dir():
        errors.insert(0, f"VapTool home does not exist: {home}")
    return {"ok": not errors, "checks": checks, "errors": errors}


def verify(args: argparse.Namespace) -> int:
    home = Path(args.home).expanduser().resolve()
    report = verify_namespace(home, args)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


def launch(args: argparse.Namespace) -> int:
    home = Path(args.home).expanduser().resolve()
    if not args.no_verify:
        report = verify_namespace(home, args)
        if not report["ok"]:
            raise RuntimeError("VapTool verification failed: " + "; ".join(report["errors"]))

    system = platform.system()
    if system == "Darwin":
        start = next((p for p in (home / "mac_start.sh", home / "start.sh") if p.is_file()), None)
        if not start:
            raise RuntimeError(f"No macOS start script found under {home}")
        ensure_executable(start)
        return subprocess.call([str(start)], cwd=home)
    if system == "Windows":
        start = next((p for p in (home / "win_start.bat", home / "start.bat") if p.is_file()), None)
        if not start:
            raise RuntimeError(f"No Windows start script found under {home}")
        return subprocess.call(["cmd", "/c", str(start)], cwd=home)
    raise RuntimeError("VapTool GUI launch is supported only on macOS/Windows. Generation can still use a supplied VapTool home if compatible binaries are present.")


def add_common_binary_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--home", default=str(default_home()), help="VapTool home directory (default: VAPTOOL_HOME or platform data directory)")
    p.add_argument("--java", help="java binary/path")
    p.add_argument("--javac", help="javac binary/path")
    p.add_argument("--ffmpeg", help="system ffmpeg binary/path")
    p.add_argument("--ffprobe", help="system ffprobe binary/path")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install, verify, or launch the Tencent VapTool dependency used by png-to-vap-mp4")
    sub = parser.add_subparsers(dest="command", required=True)

    p_install = sub.add_parser("install", help="Install official VapTool bundle")
    add_common_binary_args(p_install)
    p_install.add_argument("--archive", help="Use a local VapTool ZIP instead of downloading")
    p_install.add_argument("--url", help="Override the official release URL")
    p_install.add_argument("--force", action="store_true", help="Replace an existing installation")
    p_install.set_defaults(func=install)

    p_verify = sub.add_parser("verify", help="Verify Java, FFmpeg, VapTool jar, ffmpeg, and mp4edit")
    add_common_binary_args(p_verify)
    p_verify.set_defaults(func=verify)

    p_run = sub.add_parser("run", help="Launch the VapTool GUI on macOS/Windows")
    add_common_binary_args(p_run)
    p_run.add_argument("--no-verify", action="store_true")
    p_run.set_defaults(func=launch)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        raise SystemExit(args.func(args))
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
