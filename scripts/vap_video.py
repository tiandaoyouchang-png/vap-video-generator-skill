#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

Target = Literal["tencent-vap", "bytedance-alpha"]
Layout = Literal["standard", "mask-left"]


def die(message: str, code: int = 2) -> None:
    print(message, file=sys.stderr, flush=True)
    raise SystemExit(code)


def run_cmd(cmd: list[str], desc: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"{desc} failed with exit {result.returncode}\n"
            f"cmd: {' '.join(cmd)}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
    return result


def ensure_executable(path: Path) -> None:
    if os.name == "nt":
        return
    try:
        path.chmod(path.stat().st_mode | 0o100)
    except OSError:
        pass


def numeric_suffix(filename: str) -> int | None:
    match = re.search(r"(\d+)\.png$", filename, re.IGNORECASE)
    return int(match.group(1)) if match else None


def list_png_frames(folder: Path) -> list[Path]:
    frames: list[tuple[int, str, Path]] = []
    for path in folder.iterdir():
        if not path.is_file() or path.suffix.lower() != ".png":
            continue
        suffix = numeric_suffix(path.name)
        if suffix is not None:
            frames.append((suffix, path.name.lower(), path))
    frames.sort(key=lambda item: (item[0], item[1]))
    return [item[2] for item in frames]


def read_png_header(file_path: Path) -> tuple[int, int, int]:
    with file_path.open("rb") as handle:
        if handle.read(8) != b"\x89PNG\r\n\x1a\n":
            raise RuntimeError(f"Not a PNG file: {file_path}")
        ihdr_len = int.from_bytes(handle.read(4), "big", signed=False)
        if handle.read(4) != b"IHDR" or ihdr_len != 13:
            raise RuntimeError(f"Invalid PNG IHDR: {file_path}")
        width = int.from_bytes(handle.read(4), "big", signed=False)
        height = int.from_bytes(handle.read(4), "big", signed=False)
        handle.read(1)
        color_type_raw = handle.read(1)
        if len(color_type_raw) != 1:
            raise RuntimeError(f"Invalid PNG color type: {file_path}")
        color_type = color_type_raw[0]
    return width, height, color_type


def png_has_alpha(file_path: Path, color_type: int) -> bool:
    if color_type in (4, 6):
        return True
    if color_type != 3:
        return False
    return b"tRNS" in file_path.read_bytes()


def calculate_md5(file_path: Path) -> str:
    digest = hashlib.md5()
    with file_path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_md5(file_path: Path, output_dir: Path) -> Path:
    out = output_dir / "md5.txt"
    out.write_text(calculate_md5(file_path), encoding="utf-8")
    return out


def normalize_frames(source_frames: list[Path], normalized_dir: Path, ffmpeg: str, target_width: int, target_height: int) -> None:
    normalized_dir.mkdir(parents=True, exist_ok=True)
    for index, src in enumerate(source_frames):
        width, height, _ = read_png_header(src)
        if width != target_width:
            raise RuntimeError(f"Frame width mismatch: expected {target_width}, got {width} for {src.name}")
        if height < target_height:
            raise RuntimeError(f"Frame height too small: need at least {target_height}, got {height} for {src.name}")
        dst = normalized_dir / f"{index:06d}.png"
        if height == target_height:
            try:
                os.symlink(src, dst)
            except OSError:
                shutil.copy2(src, dst)
            continue
        run_cmd([ffmpeg, "-y", "-v", "error", "-i", str(src), "-vf", f"crop={target_width}:{target_height}:0:0", "-frames:v", "1", str(dst)], f"crop frame {src.name}")


def list_top_level_atoms(mp4_path: Path) -> list[str]:
    atoms: list[str] = []
    data = mp4_path.read_bytes()
    total = len(data)
    pos = 0
    while pos + 8 <= total:
        atom_size = int.from_bytes(data[pos:pos + 4], "big", signed=False)
        atom_type = data[pos + 4:pos + 8].decode("latin1")
        header_size = 8
        if atom_size == 1:
            if pos + 16 > total:
                break
            atom_size = int.from_bytes(data[pos + 8:pos + 16], "big", signed=False)
            header_size = 16
        elif atom_size == 0:
            atom_size = total - pos
        if atom_size < header_size or pos + atom_size > total:
            break
        atoms.append(atom_type)
        pos += atom_size
    return atoms


def has_top_level_vapc(mp4_path: Path) -> bool:
    return "vapc" in list_top_level_atoms(mp4_path)


def is_valid_mp4(mp4_path: Path, min_size_bytes: int = 512) -> bool:
    if not mp4_path.exists() or mp4_path.stat().st_size < min_size_bytes:
        return False
    atoms = list_top_level_atoms(mp4_path)
    return bool(atoms) and "moov" in atoms and "mdat" in atoms


def is_playable_mp4(mp4_path: Path, ffprobe: str) -> bool:
    if not is_valid_mp4(mp4_path):
        return False
    result = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(mp4_path)], capture_output=True, text=True)
    return result.returncode == 0 and bool(result.stdout.strip())


def require_dict(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise RuntimeError(f"Expected object for {context}")
    return cast(dict[str, object], value)


def require_list(value: object, context: str) -> list[object]:
    if not isinstance(value, list):
        raise RuntimeError(f"Expected list for {context}")
    return cast(list[object], value)


def require_int(value: object, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise RuntimeError(f"Expected integer for {context}")
    return value


def require_float(value: object, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(f"Expected number for {context}")
    return float(value)


@dataclass(frozen=True)
class VapcParsed:
    vapc_json: dict[str, object]
    frame_count: int
    fps: float
    a_frame: tuple[int, int, int, int]
    rgb_frame: tuple[int, int, int, int]


def parse_vapc_json(vapc_path: Path) -> VapcParsed:
    payload = cast(object, json.loads(vapc_path.read_text(encoding="utf-8")))
    root = require_dict(payload, "vapc.json")
    info = require_dict(root.get("info"), "vapc.json.info")
    a_raw = require_list(info.get("aFrame"), "vapc.json.info.aFrame")
    rgb_raw = require_list(info.get("rgbFrame"), "vapc.json.info.rgbFrame")
    if len(a_raw) != 4 or len(rgb_raw) != 4:
        raise RuntimeError(f"Invalid aFrame/rgbFrame in {vapc_path}")
    return VapcParsed(
        vapc_json=root,
        frame_count=require_int(info.get("f"), "vapc.json.info.f"),
        fps=require_float(info.get("fps"), "vapc.json.info.fps"),
        a_frame=tuple(require_int(v, "aFrame") for v in a_raw),
        rgb_frame=tuple(require_int(v, "rgbFrame") for v in rgb_raw),
    )


def create_vapc_atom_file(vapc_json: dict[str, object], out_path: Path) -> None:
    payload = json.dumps(vapc_json, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    size = len(payload) + 8
    out_path.write_bytes(size.to_bytes(4, "big", signed=False) + b"vapc" + payload)


def updated_mask_left_vapc(vapc: VapcParsed, frame_w: int, frame_h: int) -> dict[str, object]:
    root = dict(vapc.vapc_json)
    info = dict(require_dict(root.get("info"), "vapc.json.info"))
    info["videoW"] = frame_w * 2
    info["videoH"] = frame_h
    info["aFrame"] = [0, 0, frame_w, frame_h]
    info["rgbFrame"] = [frame_w, 0, frame_w, frame_h]
    root["info"] = info
    return root


def swap_video_regions(
    orig_mp4: Path,
    vapc: VapcParsed,
    swapped_mp4: Path,
    ffmpeg: str,
    out_bitrate_k: int,
    frame_w: int,
    frame_h: int,
    pixel_format: str,
) -> None:
    if vapc.frame_count <= 0 or vapc.fps <= 0:
        raise RuntimeError(f"Invalid frame metadata: f={vapc.frame_count}, fps={vapc.fps}")
    duration = vapc.frame_count / vapc.fps
    ax, ay, aw, ah = vapc.a_frame
    rx, ry, rw, rh = vapc.rgb_frame
    filter_str = (
        f"color=s={frame_w * 2}x{frame_h}:c=black:d={duration:.6f}[base];"
        f"[0:v]crop={aw}:{ah}:{ax}:{ay},scale={frame_w}:{frame_h}[alpha];"
        f"[0:v]crop={rw}:{rh}:{rx}:{ry},scale={frame_w}:{frame_h}[rgb];"
        f"[base][alpha]overlay=0:0[tmp];"
        f"[tmp][rgb]overlay={frame_w}:0:shortest=1[out]"
    )
    cmd = [ffmpeg, "-y", "-v", "error", "-i", str(orig_mp4), "-filter_complex", filter_str, "-map", "[out]", "-an", "-c:v", "libx264"]
    if pixel_format == "yuv444p":
        cmd += ["-profile:v", "high444"]
    cmd += ["-pix_fmt", pixel_format, "-r", str(int(round(vapc.fps))), "-b:v", f"{out_bitrate_k}k", "-maxrate", f"{out_bitrate_k}k", "-bufsize", f"{out_bitrate_k * 2}k", "-movflags", "+faststart", str(swapped_mp4)]
    run_cmd(cmd, "swap VAP video regions")


def write_final_with_vapc(swapped_mp4: Path, updated_json: dict[str, object], mp4edit: Path, ffprobe: str, work_dir: Path, final_output: Path) -> None:
    atom_path = work_dir / "vapc.atom"
    create_vapc_atom_file(updated_json, atom_path)
    no_vapc = work_dir / "no_vapc.mp4"
    remove_result = subprocess.run([str(mp4edit), "--remove", "vapc", str(swapped_mp4), str(no_vapc)], capture_output=True, text=True)
    if remove_result.returncode != 0 or not is_valid_mp4(no_vapc):
        shutil.copy2(swapped_mp4, no_vapc)
    final_tmp = work_dir / "final.mp4"
    run_cmd([str(mp4edit), "--insert", f":{atom_path}", str(no_vapc), str(final_tmp)], "insert updated vapc atom")
    if not is_playable_mp4(final_tmp, ffprobe):
        raise RuntimeError(f"Final VAP MP4 is not playable: {final_tmp}")
    if not has_top_level_vapc(final_tmp):
        raise RuntimeError(f"Final VAP MP4 is missing a top-level vapc atom: {final_tmp}")
    final_output.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(final_tmp, final_output)


def resolve_path_executable(explicit: str | None, name: str) -> str:
    if explicit:
        candidate = Path(explicit).expanduser()
        if candidate.exists():
            return str(candidate.resolve())
        found = shutil.which(explicit)
        if found:
            return found
        raise RuntimeError(f"{name} not found: {explicit}")
    found = shutil.which(name)
    if not found:
        raise RuntimeError(f"{name} not found in PATH")
    return found


def resolve_java(explicit: str | None, name: str) -> str:
    if explicit:
        return resolve_path_executable(explicit, name)
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        candidate = Path(java_home) / "bin" / (f"{name}.exe" if os.name == "nt" else name)
        if candidate.exists():
            return str(candidate)
    return resolve_path_executable(None, name)


def resolve_vaptool_home(explicit: str | None) -> Path:
    raw = explicit or os.environ.get("VAPTOOL_HOME") or os.environ.get("VAP_TOOL_HOME")
    if not raw:
        raise RuntimeError("VapTool home is required for Tencent VAP. Pass --vaptool-home or set VAPTOOL_HOME.")
    home = Path(raw).expanduser().resolve()
    if not home.is_dir():
        raise RuntimeError(f"VapTool home is not a directory: {home}")
    return home


def find_vaptool_file(home: Path, name: str, executable: bool = False) -> Path:
    names = [name]
    if os.name == "nt" and not name.lower().endswith(".exe"):
        names.insert(0, f"{name}.exe")
    roots = [home, home / "mac", home / "linux", home / "bin", home / "windows", home / "win"]
    for root in roots:
        for filename in names:
            candidate = root / filename
            if candidate.exists():
                if executable:
                    ensure_executable(candidate)
                return candidate
    raise RuntimeError(f"Could not find {name} under VapTool home: {home}")


def compile_vapbatch(java_src: Path, classes_dir: Path, javac: str, animtool_jar: Path) -> None:
    classes_dir.mkdir(parents=True, exist_ok=True)
    run_cmd([javac, "-cp", str(animtool_jar), "-d", str(classes_dir), str(java_src)], "compile VapBatch.java")
    if not (classes_dir / "VapBatch.class").exists():
        raise RuntimeError("javac completed but VapBatch.class was not produced")


def run_vap_batch(java: str, animtool_jar: Path, classes_dir: Path, frames_dir: Path, vap_out_dir: Path, vap_ffmpeg: Path, mp4edit: Path, fps: int, bitrate: int, scale: float, timeout_minutes: int) -> None:
    vap_out_dir.mkdir(parents=True, exist_ok=True)
    classpath = os.pathsep.join([str(animtool_jar), str(classes_dir)])
    cmd = [java, "-cp", classpath, "VapBatch", str(frames_dir), str(vap_out_dir), str(fps), str(bitrate), str(scale), str(vap_ffmpeg), str(mp4edit), str(timeout_minutes)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return
    fallback = frames_dir / "output"
    if (fallback / "video.mp4").exists() and (fallback / "vapc.json").exists():
        for filename in ("video.mp4", "vapc.json", "md5.txt"):
            src = fallback / filename
            if src.exists():
                shutil.copy2(src, vap_out_dir / filename)
        return
    raise RuntimeError(f"VapTool generation failed with exit {result.returncode}\ncmd: {' '.join(cmd)}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")


def generate_bytedance_alpha(frames_dir: Path, output: Path, ffmpeg: str, ffprobe: str, fps: int, bitrate: int, frame_count: int, pixel_format: str) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    pattern = str(frames_dir / "%06d.png")
    filter_str = "[0:v]split=2[rgb][alpha];[alpha]alphaextract,format=gray[alpha_only];[rgb]format=rgb24[rgb_only];[rgb_only][alpha_only]hstack=inputs=2[out]"
    cmd = [ffmpeg, "-y", "-v", "error", "-framerate", str(fps), "-i", pattern, "-filter_complex", filter_str, "-map", "[out]", "-an", "-c:v", "libx264"]
    if pixel_format == "yuv444p":
        cmd += ["-profile:v", "high444"]
    cmd += ["-pix_fmt", pixel_format, "-r", str(fps), "-b:v", f"{bitrate}k", "-frames:v", str(frame_count), "-movflags", "+faststart", str(output)]
    run_cmd(cmd, "generate ByteDance Alpha Player video")
    if not is_playable_mp4(output, ffprobe):
        raise RuntimeError(f"Generated ByteDance MP4 is not playable: {output}")


@dataclass(frozen=True)
class Args:
    input: str
    output: str
    target: Target
    layout: Layout
    fps: int
    bitrate: int
    swap_bitrate: int
    standard_scale: float
    pixel_format: str
    ffmpeg: str | None
    ffprobe: str | None
    java: str | None
    javac: str | None
    vaptool_home: str | None
    crop_height: int | None
    no_auto_crop: bool
    keep_work: bool
    timeout_minutes: int


def parse_args() -> Args:
    parser = argparse.ArgumentParser(description="Generate Tencent VAP or ByteDance Alpha Player MP4 from a PNG sequence")
    parser.add_argument("--input", required=True, help="Directory containing PNG frames")
    parser.add_argument("--output", required=True, help="Final MP4 path")
    parser.add_argument("--target", "--platform", dest="target", choices=["tencent-vap", "bytedance-alpha"], default="tencent-vap", help="Output target (legacy alias: --platform)")
    parser.add_argument("--layout", "--mode", dest="layout", choices=["standard", "mask-left"], default="standard", help="Tencent VAP layout (legacy alias: --mode)")
    parser.add_argument("--fps", type=int, default=25, help="Frames per second")
    parser.add_argument("--bitrate", type=int, default=2000, help="Primary encoding bitrate in kbps")
    parser.add_argument("--swap-bitrate", type=int, default=3000, help="mask-left re-encoding bitrate in kbps")
    parser.add_argument("--standard-scale", type=float, default=0.5, help="VapTool alpha scale for standard layout")
    parser.add_argument("--pixel-format", choices=["yuv420p", "yuv444p"], default="yuv420p", help="Pixel format for side-by-side re-encoding")
    parser.add_argument("--ffmpeg", help="Path/name for FFmpeg")
    parser.add_argument("--ffprobe", help="Path/name for ffprobe")
    parser.add_argument("--java", help="Path/name for java; otherwise JAVA_HOME/PATH")
    parser.add_argument("--javac", help="Path/name for javac; otherwise JAVA_HOME/PATH")
    parser.add_argument("--vaptool-home", help="VapTool directory; otherwise VAPTOOL_HOME")
    parser.add_argument("--crop-height", type=int, help="Crop all frames from top to this height")
    parser.add_argument("--no-auto-crop", action="store_true", help="Disable 1344 -> 1334 compatibility crop")
    parser.add_argument("--keep-work", action="store_true", help="Keep temporary work directory after success")
    parser.add_argument("--timeout-minutes", type=int, default=60, help="VapTool generation timeout")
    ns = parser.parse_args()
    return Args(input=ns.input, output=ns.output, target=cast(Target, ns.target), layout=cast(Layout, ns.layout), fps=ns.fps, bitrate=ns.bitrate, swap_bitrate=ns.swap_bitrate, standard_scale=ns.standard_scale, pixel_format=ns.pixel_format, ffmpeg=ns.ffmpeg, ffprobe=ns.ffprobe, java=ns.java, javac=ns.javac, vaptool_home=ns.vaptool_home, crop_height=ns.crop_height, no_auto_crop=ns.no_auto_crop, keep_work=ns.keep_work, timeout_minutes=ns.timeout_minutes)


def validate_args(args: Args) -> None:
    if args.fps <= 0:
        die(f"--fps must be > 0, got {args.fps}")
    if args.bitrate <= 0 or args.swap_bitrate <= 0:
        die("--bitrate and --swap-bitrate must be > 0")
    if not (0 < args.standard_scale <= 1.0):
        die("--standard-scale must be > 0 and <= 1.0")
    if args.crop_height is not None and args.crop_height <= 0:
        die("--crop-height must be > 0")
    if args.timeout_minutes <= 0:
        die("--timeout-minutes must be > 0")
    if args.target == "bytedance-alpha" and args.layout != "standard":
        print("Warning: --layout is ignored for bytedance-alpha", file=sys.stderr)


def main() -> None:
    args = parse_args()
    validate_args(args)
    src_dir = Path(args.input).expanduser().resolve()
    out_mp4 = Path(args.output).expanduser().resolve()
    if not src_dir.is_dir():
        die(f"--input is not a directory: {src_dir}")

    try:
        ffmpeg = resolve_path_executable(args.ffmpeg, "ffmpeg")
        ffprobe = resolve_path_executable(args.ffprobe, "ffprobe")
    except RuntimeError as exc:
        die(str(exc))

    source_frames = list_png_frames(src_dir)
    if not source_frames:
        die(f"No PNG frames with numeric suffixes found in {src_dir}")

    raw_w, raw_h, color_type = read_png_header(source_frames[0])
    if not png_has_alpha(source_frames[0], color_type):
        print(f"Warning: first frame does not appear to contain alpha: {source_frames[0].name}", file=sys.stderr, flush=True)

    target_h = raw_h
    if args.crop_height is not None:
        if args.crop_height > raw_h:
            die(f"--crop-height {args.crop_height} exceeds input height {raw_h}")
        target_h = args.crop_height
    elif not args.no_auto_crop and raw_h == 1344:
        target_h = 1334

    work_dir = Path(tempfile.mkdtemp(prefix="vap_video_"))
    success = False
    try:
        frames_dir = work_dir / "frames"
        normalize_frames(source_frames, frames_dir, ffmpeg, raw_w, target_h)

        if args.target == "bytedance-alpha":
            if args.pixel_format == "yuv420p" and target_h % 2:
                raise RuntimeError(f"yuv420p requires an even frame height, got {target_h}")
            generate_bytedance_alpha(frames_dir, out_mp4, ffmpeg, ffprobe, args.fps, args.bitrate, len(source_frames), args.pixel_format)
            md5_path = write_md5(out_mp4, out_mp4.parent)
            print(f"Generated ByteDance Alpha Player video: {out_mp4}")
            print(f"MD5: {md5_path}")
            success = True
            return

        try:
            vap_home = resolve_vaptool_home(args.vaptool_home)
            java = resolve_java(args.java, "java")
            javac = resolve_java(args.javac, "javac")
            animtool_jar = find_vaptool_file(vap_home, "animtool.jar")
            vap_ffmpeg = find_vaptool_file(vap_home, "ffmpeg", executable=True)
            mp4edit = find_vaptool_file(vap_home, "mp4edit", executable=True)
        except RuntimeError as exc:
            raise RuntimeError(f"Tencent VAP dependency error: {exc}") from exc

        skill_dir = Path(__file__).resolve().parent
        java_src = skill_dir / "VapBatch.java"
        if not java_src.exists():
            raise RuntimeError(f"Missing bundled Java wrapper: {java_src}")
        classes_dir = work_dir / "classes"
        compile_vapbatch(java_src, classes_dir, javac, animtool_jar)

        vap_out = work_dir / "vap_out"
        scale = args.standard_scale if args.layout == "standard" else 1.0
        run_vap_batch(java, animtool_jar, classes_dir, frames_dir, vap_out, vap_ffmpeg, mp4edit, args.fps, args.bitrate, scale, args.timeout_minutes)

        orig_mp4 = vap_out / "video.mp4"
        vapc_path = vap_out / "vapc.json"
        if not orig_mp4.exists() or not vapc_path.exists():
            raise RuntimeError("VapTool did not produce both video.mp4 and vapc.json")

        out_mp4.parent.mkdir(parents=True, exist_ok=True)
        if args.layout == "standard":
            if not is_playable_mp4(orig_mp4, ffprobe):
                raise RuntimeError(f"Generated Tencent VAP MP4 is not playable: {orig_mp4}")
            shutil.copy2(orig_mp4, out_mp4)
            shutil.copy2(vapc_path, out_mp4.parent / "vapc.json")
        else:
            vapc = parse_vapc_json(vapc_path)
            swapped_mp4 = work_dir / "swapped.mp4"
            if args.pixel_format == "yuv420p" and target_h % 2:
                raise RuntimeError(f"yuv420p requires an even frame height, got {target_h}")
            swap_video_regions(orig_mp4, vapc, swapped_mp4, ffmpeg, args.swap_bitrate, raw_w, target_h, args.pixel_format)
            if not is_playable_mp4(swapped_mp4, ffprobe):
                raise RuntimeError(f"Swapped Tencent VAP MP4 is not playable: {swapped_mp4}")
            updated_json = updated_mask_left_vapc(vapc, raw_w, target_h)
            write_final_with_vapc(swapped_mp4, updated_json, mp4edit, ffprobe, work_dir, out_mp4)
            (out_mp4.parent / "vapc.json").write_text(json.dumps(updated_json, ensure_ascii=False, indent=2), encoding="utf-8")

        md5_path = write_md5(out_mp4, out_mp4.parent)
        print(f"Generated Tencent VAP video: {out_mp4}")
        print(f"VAPC: {out_mp4.parent / 'vapc.json'}")
        print(f"MD5: {md5_path}")
        success = True
    except Exception as exc:
        print(f"Generation failed: {exc}", file=sys.stderr, flush=True)
        print(f"Work dir preserved for debugging: {work_dir}", file=sys.stderr, flush=True)
        raise SystemExit(1) from exc
    finally:
        if success and not args.keep_work and work_dir.exists():
            shutil.rmtree(work_dir)
        elif success and args.keep_work:
            print(f"Work dir kept: {work_dir}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
