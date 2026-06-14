# VAP Video Generator / VAP 视频生成器

A small CLI tool for turning PNG image sequences into transparent video assets for Tencent VAP and ByteDance Alpha Player workflows.

一个将 PNG 序列转换为腾讯 VAP 和字节跳动 Alpha Player 透明视频素材的命令行工具。

## Why This Project Exists / 项目价值

Mobile apps, live rooms, campaign pages, and marketing tools often need alpha-channel animation assets that can be shipped as compact MP4 files. This project automates the repetitive conversion from exported PNG frames into player-ready video files, metadata, and checksums.

移动端应用、直播间、活动页和营销工具经常需要以 MP4 形式交付的透明动效素材。本项目把设计导出的 PNG 帧序列自动转换为播放器可用的视频、元数据和校验文件，减少手工处理和重复配置。

## Features / 功能

- Generate Tencent VAP-compatible video output with MD5 and `vapc.json` metadata.
- Generate ByteDance Alpha Player-compatible video output using a left-right RGB/alpha layout.
- Detect input frame resolution automatically.
- Configure FPS, platform target, output path, and video bitrate from the CLI.
- Use FFmpeg and ffprobe directly, so the tool can run in local scripts or asset pipelines.

- 生成腾讯 VAP 兼容视频，并输出 MD5 与 `vapc.json` 元数据。
- 生成字节跳动 Alpha Player 兼容视频，使用左右 RGB/Alpha 布局。
- 自动检测输入 PNG 帧分辨率。
- 通过命令行配置帧率、目标平台、输出路径和视频码率。
- 直接调用 FFmpeg / ffprobe，便于集成到本地脚本或素材流水线。

## Requirements / 依赖

- Python 3
- FFmpeg
- ffprobe

Check your local environment:

```bash
python3 --version
ffmpeg -version
ffprobe -version
```

## Installation / 安装

Clone the repository and run the script directly:

```bash
git clone https://github.com/tiandaoyouchang-png/vap-video-generator-skill.git
cd vap-video-generator-skill
python3 vap_master.py --help
```

## Usage / 使用方法

### Tencent VAP / 腾讯 VAP

```bash
python3 vap_master.py \
  --input ./frames \
  --output ./output/tencent_vap/video.mp4 \
  --fps 25 \
  --platform tencent-vap \
  --bitrate 100
```

### ByteDance Alpha Player / 字节跳动 Alpha Player

```bash
python3 vap_master.py \
  --input ./frames \
  --output ./output/bytedance_alpha/video.mp4 \
  --fps 25 \
  --platform bytedance-alpha \
  --bitrate 100
```

## Input Format / 输入格式

The input directory should contain PNG frames named in sequence:

```text
000.png
001.png
002.png
...
```

The tool warns when filenames do not match this pattern. All frames should use the same dimensions.

输入目录应包含按顺序命名的 PNG 帧。文件名不符合顺序时，工具会输出警告。所有帧应保持相同尺寸。

## CLI Options / 参数说明

| Option | Description | Default |
| --- | --- | --- |
| `--input` | Directory containing PNG frames / PNG 序列目录 | Required |
| `--output` | Output MP4 file path / 输出 MP4 路径 | Required |
| `--fps` | Frames per second / 帧率 | `25` |
| `--platform` | `tencent-vap` or `bytedance-alpha` / 目标平台 | `tencent-vap` |
| `--bitrate` | Video bitrate in kbps / 视频码率，单位 kbps | `100` |

## Output / 输出文件

For Tencent VAP:

- `video.mp4`: generated VAP video
- `md5.txt`: MD5 checksum for the generated video
- `vapc.json`: VAP layout metadata

For ByteDance Alpha Player:

- `video.mp4`: generated Alpha Player video
- `md5.txt`: MD5 checksum for the generated video

## Maintenance Roadmap / 维护方向

- Add validation for alpha channels and frame dimensions.
- Add more presets for common delivery sizes and bitrate targets.
- Add sample input frames and expected output metadata.
- Improve compatibility notes for Tencent VAP and ByteDance Alpha Player versions.

## License / 许可证

MIT License. See [LICENSE](LICENSE).
