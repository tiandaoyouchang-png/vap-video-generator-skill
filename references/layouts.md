# Layout and output reference

## Target matrix

| Target | Layout | RGB region | Alpha region | Engine | Sidecars |
| --- | --- | --- | --- | --- | --- |
| Tencent VAP | `standard` | VapTool-defined | VapTool-defined, scaled by `--standard-scale` | Official VapTool | `vapc.json`, `md5.txt` |
| Tencent VAP | `mask-left` | Right, full frame | Left, full frame | VapTool + FFmpeg + mp4edit | updated `vapc.json`, `md5.txt` |
| ByteDance Alpha Player | n/a | Left, full frame | Right, full frame | FFmpeg | `md5.txt` |

## Why Tencent uses VapTool

Tencent VAP playback depends on metadata stored in a top-level `vapc` MP4 atom. An external JSON file alone is not equivalent to a correctly authored VAP MP4. Prefer the official VapTool path for Tencent output.

## `mask-left` post-processing

1. Generate a normal VAP file with alpha scale `1.0` so the RGB and alpha sources both retain full-frame resolution.
2. Crop the RGB and alpha regions described by VapTool's generated `vapc.json`.
3. Scale each crop to the source frame size and compose a new canvas with alpha on the left and RGB on the right.
4. Rewrite `videoW`, `videoH`, `aFrame`, and `rgbFrame` in the VAP metadata.
5. Remove the old top-level `vapc` atom and insert the updated atom with `mp4edit`.
6. Validate the MP4 with `ffprobe` and confirm the top-level `vapc` atom exists.

## ByteDance Alpha Player layout

The generated canvas width is `frame_width * 2` and height is `frame_height`:

- left half: RGB
- right half: grayscale alpha mask

The output is H.264 `yuv420p` for broad mobile decoding compatibility.

## Sidecar naming

The script intentionally preserves the conventional fixed names used by existing pipelines:

- `video.mp4` (or the requested output filename)
- `vapc.json` for Tencent VAP
- `md5.txt` for all targets

Use one output directory per asset to avoid sidecar collisions.
