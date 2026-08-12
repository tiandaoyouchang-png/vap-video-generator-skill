---
name: vap-video-generator
description: Generate transparent-video assets from PNG frame sequences for Tencent VAP or ByteDance Alpha Player. Use when the user needs to convert PNG/alpha frame sequences to VAP MP4, Alpha Player MP4, Tencent standard VAP layout, mask-left/alpha-left layout, generate vapc.json or MD5 sidecars, validate VAP output, or troubleshoot FFmpeg/VapTool generation.
---

# VAP Video Generator

Use the bundled `scripts/vap_video.py` as the single execution entrypoint. Do not reimplement the FFmpeg/VapTool pipeline ad hoc unless the script itself must be repaired.

## Route the request

1. Choose `--target tencent-vap` for Tencent VAP, VAP, vapc, or Tencent transparent-animation requests.
2. Choose `--target bytedance-alpha` for ByteDance Alpha Player / AlphaVideo requests.
3. For Tencent VAP, use `--layout standard` unless the user explicitly asks for alpha/mask on the left, RGB on the right, or `mask-left`.
4. Treat `--platform` as a backward-compatible alias for `--target`, and `--mode` as an alias for `--layout`.

Read `references/layouts.md` when layout semantics, output sidecars, or compatibility details matter.

## Execute

Prefer an output directory dedicated to one asset because Tencent outputs include fixed sidecar names (`vapc.json`, `md5.txt`).

Tencent standard:

```bash
python3 scripts/vap_video.py \
  --input /path/to/frames \
  --output /path/to/output/video.mp4 \
  --target tencent-vap \
  --layout standard \
  --fps 25
```

Tencent mask-left:

```bash
python3 scripts/vap_video.py \
  --input /path/to/frames \
  --output /path/to/output/video.mp4 \
  --target tencent-vap \
  --layout mask-left \
  --fps 25
```

ByteDance Alpha Player:

```bash
python3 scripts/vap_video.py \
  --input /path/to/frames \
  --output /path/to/output/video.mp4 \
  --target bytedance-alpha \
  --fps 25
```

## Dependency rules

- Require `ffmpeg` and `ffprobe` for all targets.
- Require Java, `javac`, and a VapTool home containing `animtool.jar`, VapTool `ffmpeg`, and `mp4edit` only for Tencent VAP.
- Resolve Java from `--java`, then `JAVA_HOME`, then `PATH`.
- Resolve VapTool from `--vaptool-home` or `VAPTOOL_HOME`; never assume a user-specific absolute path.
- Compile `VapBatch.java` into the temporary work directory. Never write generated `.class` files into the Skill directory.

## Input handling

- Accept PNG names with a numeric suffix, not only exactly `000.png`.
- Sort by numeric suffix and normalize to a contiguous temporary sequence before encoding.
- Require consistent frame width and height after optional cropping.
- Preserve the compatibility normalization from 1344 px height to 1334 px by default. Override explicitly with `--crop-height`; use `--no-auto-crop` to disable the compatibility crop.
- Warn if the first PNG does not expose an alpha channel; do not silently pretend an opaque sequence is transparent.

## Output and validation

- Always generate `md5.txt` from the final MP4.
- For Tencent VAP, also emit `vapc.json` beside the final MP4.
- For Tencent `mask-left`, regenerate both the embedded top-level `vapc` atom and the sidecar `vapc.json` after region swapping.
- Validate final Tencent MP4 structure and playback with `ffprobe`; validate that a top-level `vapc` atom exists after `mask-left` post-processing.
- Preserve the temporary work directory on failure and report its path for diagnosis.

## Quality defaults

- Default to 25 fps unless the user specifies otherwise.
- Use 2000 kbps for Tencent VapTool encoding and 3000 kbps for `mask-left` re-encoding.
- Use 2000 kbps for ByteDance Alpha Player unless the user provides a delivery bitrate or file-size constraint.
- Do not claim a guaranteed file size such as “under 1 MB” without measuring the generated output; bitrate, duration, frame size, and content complexity determine size.
