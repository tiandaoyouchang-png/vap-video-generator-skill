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
from collections import deque
from pathlib import Path
from typing import Literal

from PIL import Image, ImageFilter

AlphaMode = Literal['straight', 'premultiplied']
BackgroundMode = Literal['alpha', 'white-connected']


def run(cmd: list[str], desc: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    p = subprocess.run(cmd, capture_output=True, text=True)
    if check and p.returncode != 0:
        raise RuntimeError(f'{desc} failed ({p.returncode})\ncmd: {cmd}\nstdout:\n{p.stdout}\nstderr:\n{p.stderr}')
    return p


def natural_key(path: Path) -> list[object]:
    parts = re.split(r'(\d+)', path.name.lower())
    return [int(p) if p.isdigit() else p for p in parts]


def list_pngs(folder: Path) -> list[Path]:
    files = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == '.png']
    return sorted(files, key=natural_key)


def md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def white_connected_alpha(img: Image.Image, threshold: int, chroma_tol: int, softness: int) -> Image.Image:
    rgba = img.convert('RGBA')
    px = rgba.load()
    w, h = rgba.size
    is_white = [[False] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            r, g, b, _ = px[x, y]
            is_white[y][x] = min(r, g, b) >= threshold and (max(r, g, b) - min(r, g, b)) <= chroma_tol
    q: deque[tuple[int, int]] = deque()
    seen = [[False] * w for _ in range(h)]
    for x in range(w):
        for y in (0, h - 1):
            if is_white[y][x] and not seen[y][x]:
                seen[y][x] = True
                q.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if is_white[y][x] and not seen[y][x]:
                seen[y][x] = True
                q.append((x, y))
    while q:
        x, y = q.popleft()
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= nx < w and 0 <= ny < h and is_white[ny][nx] and not seen[ny][nx]:
                seen[ny][nx] = True
                q.append((nx, ny))
    alpha = Image.new('L', (w, h), 255)
    ap = alpha.load()
    for y in range(h):
        for x in range(w):
            if seen[y][x]:
                ap[x, y] = 0
    rgba.putalpha(alpha)
    return rgba


def clean_rgba(
    img: Image.Image,
    threshold: int,
    remap: bool,
    alpha_mode: AlphaMode,
    background_mode: BackgroundMode,
    white_threshold: int,
    white_chroma: int,
    white_softness: int,
) -> Image.Image:
    rgba = (
        white_connected_alpha(img, white_threshold, white_chroma, white_softness)
        if background_mode == 'white-connected'
        else img.convert('RGBA')
    )
    data = bytearray(rgba.tobytes())
    denom = max(1, 255 - threshold)
    for i in range(0, len(data), 4):
        a = data[i + 3]
        if a <= threshold:
            a2 = 0
        elif remap:
            a2 = max(0, min(255, round((a - threshold) * 255 / denom)))
        else:
            a2 = a
        data[i + 3] = a2
        if a2 == 0:
            data[i] = data[i + 1] = data[i + 2] = 0
        elif alpha_mode == 'premultiplied':
            data[i] = round(data[i] * a2 / 255)
            data[i + 1] = round(data[i + 1] * a2 / 255)
            data[i + 2] = round(data[i + 2] * a2 / 255)
    return Image.frombytes('RGBA', rgba.size, bytes(data))


def extract_video_frames(src: Path, out_dir: Path, ffmpeg: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    run([ffmpeg, '-y', '-v', 'error', '-i', str(src), str(out_dir / '%08d.png')], 'extract source video frames')


def preprocess(input_path: Path, frames_dir: Path, ffmpeg: str, args: argparse.Namespace) -> tuple[int, int, int]:
    source_dir = input_path
    if input_path.is_file():
        extracted = frames_dir.parent / 'extracted'
        extract_video_frames(input_path, extracted, ffmpeg)
        source_dir = extracted
    files = list_pngs(source_dir)
    if not files:
        raise RuntimeError(f'No PNG frames found: {source_dir}')
    frames_dir.mkdir(parents=True, exist_ok=True)
    expected: tuple[int, int] | None = None
    any_alpha = False
    for idx, src in enumerate(files):
        with Image.open(src) as raw:
            rgba = clean_rgba(
                raw,
                args.alpha_threshold,
                not args.no_alpha_remap,
                args.alpha_mode,
                args.background_mode,
                args.white_threshold,
                args.white_chroma_tolerance,
                args.white_softness,
            )
            if args.crop_height:
                if rgba.height < args.crop_height:
                    raise RuntimeError(f'{src.name}: height {rgba.height} < crop {args.crop_height}')
                rgba = rgba.crop((0, 0, rgba.width, args.crop_height))
            elif not args.no_auto_crop and rgba.height == 1344:
                rgba = rgba.crop((0, 0, rgba.width, 1334))
            if expected is None:
                expected = rgba.size
            if rgba.size != expected:
                raise RuntimeError(f'Frame dimensions differ: expected {expected}, got {rgba.size} at {src.name}')
            amin, _ = rgba.getchannel('A').getextrema()
            any_alpha = any_alpha or amin < 255
            rgba.save(frames_dir / f'{idx:08d}.png')
    if not any_alpha and args.background_mode == 'alpha' and not args.allow_opaque:
        raise RuntimeError('Input is fully opaque. Use --background-mode white-connected or --allow-opaque.')
    assert expected
    return expected[0], expected[1], len(files)


def encode_side_by_side(frames_dir: Path, temp_mp4: Path, ffmpeg: str, args: argparse.Namespace, alpha_left: bool) -> None:
    pattern = str(frames_dir / '%08d.png')
    if alpha_left:
        filt = '[0:v]split=2[rgb][a];[rgb]format=rgb24[rgb];[a]alphaextract,format=gray[a];[a][rgb]hstack=inputs=2[out]'
    else:
        filt = '[0:v]split=2[rgb][a];[rgb]format=rgb24[rgb];[a]alphaextract,format=gray[a];[rgb][a]hstack=inputs=2[out]'
    cmd = [
        ffmpeg,
        '-y',
        '-v',
        'error',
        '-framerate',
        str(args.fps),
        '-i',
        pattern,
        '-filter_complex',
        filt,
        '-map',
        '[out]',
        '-an',
        '-c:v',
        'libx264',
        '-preset',
        args.preset,
        '-pix_fmt',
        args.pixel_format,
        '-r',
        str(args.fps),
        '-frames:v',
        str(args.frame_count),
    ]
    if args.bitrate:
        cmd += ['-b:v', f'{args.bitrate}k']
    else:
        cmd += ['-crf', str(args.crf)]
    cmd += ['-movflags', '+faststart', str(temp_mp4)]
    run(cmd, 'encode side-by-side transparent MP4')


def probe(path: Path, ffprobe: str) -> dict[str, object]:
    p = run(
        [
            ffprobe,
            '-v',
            'error',
            '-select_streams',
            'v:0',
            '-show_entries',
            'stream=codec_name,width,height,pix_fmt,r_frame_rate,avg_frame_rate,nb_frames,duration',
            '-show_entries',
            'format=duration',
            '-of',
            'json',
            str(path),
        ],
        'probe output',
    )
    return json.loads(p.stdout)


def frac(v: str | None) -> float:
    if not v:
        return 0.0
    if '/' in v:
        a, b = v.split('/', 1)
        return float(a) / float(b) if float(b) else 0.0
    return float(v)


def decode_check(path: Path, ffmpeg: str) -> None:
    run([ffmpeg, '-v', 'error', '-i', str(path), '-f', 'null', '-'], 'full decode validation')


def sample_compare(
    video: Path,
    frames_dir: Path,
    ffmpeg: str,
    indices: list[int],
    w: int,
    h: int,
    alpha_left: bool,
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for idx in indices:
        out = frames_dir.parent / f'qa_decoded_{idx}.png'
        run(
            [
                ffmpeg,
                '-y',
                '-v',
                'error',
                '-i',
                str(video),
                '-vf',
                f'select=eq(n\\,{idx})',
                '-vsync',
                '0',
                '-frames:v',
                '1',
                str(out),
            ],
            f'decode QA frame {idx}',
        )
        with Image.open(out) as decoded, Image.open(frames_dir / f'{idx:08d}.png') as source:
            d = decoded.convert('RGB')
            s = source.convert('RGBA')
            rgb_crop = d.crop((w, 0, 2 * w, h)) if alpha_left else d.crop((0, 0, w, h))
            alpha_crop = d.crop((0, 0, w, h)) if alpha_left else d.crop((w, 0, 2 * w, h))
            src_a = s.getchannel('A')
            ap = list(alpha_crop.convert('L').getdata())
            sp = list(src_a.getdata())
            mae = sum(abs(a - b) for a, b in zip(ap, sp)) / len(ap)
            safe = src_a.point(lambda a: 255 if a == 0 else 0).filter(ImageFilter.MinFilter(5))
            rp = list(rgb_crop.getdata())
            mp = list(safe.getdata())
            safe_px = [p for p, m in zip(rp, mp) if m]
            nonblack = sum(1 for r, g, b in safe_px if max(r, g, b) > 24)
            blue = sum(1 for r, g, b in safe_px if b > r + 20 and b > g + 10 and b > 32)
            results.append(
                {
                    'frame': idx,
                    'alpha_mae': round(mae, 3),
                    'safe_pixels': len(safe_px),
                    'safe_nonblack_ratio': round(nonblack / max(1, len(safe_px)), 6),
                    'safe_blue_ratio': round(blue / max(1, len(safe_px)), 6),
                }
            )
    return results


def validate_side_by_side(
    video: Path,
    frames_dir: Path,
    ffmpeg: str,
    ffprobe: str,
    w: int,
    h: int,
    count: int,
    args: argparse.Namespace,
    alpha_left: bool,
) -> dict[str, object]:
    meta = probe(video, ffprobe)
    stream = meta['streams'][0]
    errors: list[str] = []
    if int(stream['width']) != 2 * w or int(stream['height']) != h:
        errors.append(f'dimensions {stream["width"]}x{stream["height"]} != {2 * w}x{h}')
    fps = frac(stream.get('avg_frame_rate') or stream.get('r_frame_rate'))
    if abs(fps - args.fps) > 0.01:
        errors.append(f'fps {fps} != {args.fps}')
    nb = stream.get('nb_frames')
    if nb not in (None, 'N/A') and int(nb) != count:
        errors.append(f'frame count {nb} != {count}')
    decode_check(video, ffmpeg)
    indices = sorted(set([0, count // 2, count - 1]))
    samples = sample_compare(video, frames_dir, ffmpeg, indices, w, h, alpha_left)
    for sample in samples:
        if sample['alpha_mae'] > args.max_alpha_mae:
            errors.append(f'alpha MAE too high on frame {sample["frame"]}: {sample["alpha_mae"]}')
        if sample['safe_blue_ratio'] > args.max_blue_ratio:
            errors.append(f'blue contamination on frame {sample["frame"]}: {sample["safe_blue_ratio"]}')
    return {
        'ok': not errors,
        'errors': errors,
        'probe': meta,
        'samples': samples,
        'expected': {'width': 2 * w, 'height': h, 'fps': args.fps, 'frames': count},
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='Convert PNG sequence or video into validated VAP/Alpha transparent MP4')
    p.add_argument('--input', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--target', '--platform', dest='target', choices=['tencent-vap', 'bytedance-alpha'], default='bytedance-alpha')
    p.add_argument('--layout', '--mode', dest='layout', choices=['standard', 'mask-left'], default='standard')
    p.add_argument('--fps', type=int, default=25)
    p.add_argument('--crf', type=int, default=18)
    p.add_argument('--bitrate', type=int)
    p.add_argument('--preset', default='medium')
    p.add_argument('--pixel-format', choices=['yuv420p', 'yuv444p'], default='yuv420p')
    p.add_argument('--alpha-threshold', type=int, default=16)
    p.add_argument('--no-alpha-remap', action='store_true')
    p.add_argument('--alpha-mode', choices=['straight', 'premultiplied'], default='straight')
    p.add_argument('--background-mode', choices=['alpha', 'white-connected'], default='alpha')
    p.add_argument('--white-threshold', type=int, default=245)
    p.add_argument('--white-chroma-tolerance', type=int, default=18)
    p.add_argument('--white-softness', type=int, default=12)
    p.add_argument('--allow-opaque', action='store_true')
    p.add_argument('--crop-height', type=int)
    p.add_argument('--no-auto-crop', action='store_true')
    p.add_argument('--ffmpeg')
    p.add_argument('--ffprobe')
    p.add_argument('--keep-work', action='store_true')
    p.add_argument('--max-alpha-mae', type=float, default=16.0)
    p.add_argument('--max-blue-ratio', type=float, default=0.002)
    p.add_argument('--java')
    p.add_argument('--javac')
    p.add_argument('--vaptool-home')
    p.add_argument('--standard-scale', type=float, default=0.5)
    p.add_argument('--swap-bitrate', type=int, default=3000)
    p.add_argument('--timeout-minutes', type=int, default=60)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    if not (0 <= args.alpha_threshold <= 254):
        raise SystemExit('--alpha-threshold must be 0..254')
    src = Path(args.input).expanduser().resolve()
    out = Path(args.output).expanduser().resolve()
    ffmpeg = args.ffmpeg or shutil.which('ffmpeg')
    ffprobe = args.ffprobe or shutil.which('ffprobe')
    if not ffmpeg or not ffprobe:
        raise SystemExit('ffmpeg and ffprobe are required')
    if not src.exists():
        raise SystemExit(f'input not found: {src}')
    work = Path(tempfile.mkdtemp(prefix='png_to_vap_'))
    success = False
    try:
        frames = work / 'frames'
        w, h, count = preprocess(src, frames, ffmpeg, args)
        args.frame_count = count
        temp = work / 'output.mp4'
        if args.target == 'tencent-vap':
            legacy = Path(__file__).with_name('vap_video.py')
            cmd = [
                sys.executable,
                str(legacy),
                '--input',
                str(frames),
                '--output',
                str(temp),
                '--target',
                'tencent-vap',
                '--layout',
                args.layout,
                '--fps',
                str(args.fps),
                '--bitrate',
                str(args.bitrate or 2000),
                '--standard-scale',
                str(args.standard_scale),
                '--swap-bitrate',
                str(args.swap_bitrate),
            ]
            for flag, value in [
                ('--java', args.java),
                ('--javac', args.javac),
                ('--vaptool-home', args.vaptool_home),
                ('--ffmpeg', ffmpeg),
                ('--ffprobe', ffprobe),
            ]:
                if value:
                    cmd += [flag, str(value)]
            run(cmd, 'official Tencent VapTool pipeline')
            decode_check(temp, ffmpeg)
            if args.layout == 'mask-left':
                qa = validate_side_by_side(temp, frames, ffmpeg, ffprobe, w, h, count, args, True)
                if not qa['ok']:
                    raise RuntimeError('QA failed: ' + '; '.join(qa['errors']))
            else:
                qa = {
                    'ok': True,
                    'errors': [],
                    'probe': probe(temp, ffprobe),
                    'note': 'Tencent standard layout generated by official VapTool; full decode checked.',
                }
        else:
            encode_side_by_side(frames, temp, ffmpeg, args, False)
            qa = validate_side_by_side(temp, frames, ffmpeg, ffprobe, w, h, count, args, False)
            if not qa['ok']:
                raise RuntimeError('QA failed: ' + '; '.join(qa['errors']))
        out.parent.mkdir(parents=True, exist_ok=True)
        staged = out.with_name(out.name + '.tmp')
        shutil.copy2(temp, staged)
        os.replace(staged, out)
        (out.parent / 'md5.txt').write_text(md5(out), encoding='utf-8')
        (out.parent / 'qa.json').write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding='utf-8')
        if args.target == 'tencent-vap':
            maybe = temp.parent / 'vapc.json'
            if maybe.exists():
                shutil.copy2(maybe, out.parent / 'vapc.json')
        success = True
        print(json.dumps({'output': str(out), 'md5': md5(out), 'qa': qa}, ensure_ascii=False))
    except Exception as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        print(f'Work directory preserved: {work}', file=sys.stderr)
        raise SystemExit(1)
    finally:
        if success and not args.keep_work:
            shutil.rmtree(work, ignore_errors=True)


if __name__ == '__main__':
    main()
