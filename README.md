# VAP 视频生成器 / VAP Video Generator

一个用于将 PNG 序列转换为腾讯 VAP 和字节跳动 Alpha Player 视频的工具。

A tool to generate Tencent VAP and ByteDance Alpha Player videos from PNG sequences.

## 功能 / Features

- 生成腾讯 VAP 视频，包含 MD5 和 JSON 元数据
- 生成字节跳动 Alpha Player 视频，使用左右 1:1 布局
- 自动检测输入帧分辨率
- 优化文件大小，确保视频在 1M 以内

- Generate Tencent VAP videos with MD5 and JSON metadata
- Generate ByteDance Alpha Player videos with 1:1 left-right layout
- Automatic resolution detection
- Optimized for small file size

## 依赖 / Requirements

- Python 3
- FFmpeg
- ffprobe

## 使用方法 / Usage

### 生成腾讯 VAP 视频

```bash
python3 vap_master.py --input <输入目录> --output <输出文件> --fps 25 --platform tencent-vap --bitrate 100
```

### 生成字节跳动 Alpha Player 视频

```bash
python3 vap_master.py --input <输入目录> --output <输出文件> --fps 25 --platform bytedance-alpha --bitrate 100
```

## 参数说明 / Parameters

- `--input`：包含 PNG 序列的目录路径 / Path to directory containing PNG sequence
- `--output`：最终 MP4 文件的保存路径 / Path where final MP4 will be saved
- `--fps`：帧率（默认：25） / Frames per second (default: 25)
- `--platform`：平台（tencent-vap 或 bytedance-alpha，默认：tencent-vap） / Platform (tencent-vap or bytedance-alpha, default: tencent-vap)
- `--bitrate`：编码码率（kbps，默认：100） / Encoding bitrate in kbps (default: 100)

## 输出文件 / Output

### 腾讯 VAP

- `video.mp4`：VAP 视频文件
- `md5.txt`：视频的 MD5 哈希值
- `vapc.json`：VAP 配置文件

### 字节跳动 Alpha Player

- `video.mp4`：Alpha Player 视频文件
- `md5.txt`：视频的 MD5 哈希值

## 示例 / Example

```bash
# 生成腾讯 VAP 视频
python3 vap_master.py --input "./frames" --output "./output/tencent_vap/video.mp4" --fps 25 --platform tencent-vap --bitrate 100

# 生成字节跳动 Alpha Player 视频
python3 vap_master.py --input "./frames" --output "./output/bytedance_alpha/video.mp4" --fps 25 --platform bytedance-alpha --bitrate 100
```