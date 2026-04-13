# VAP Video Generator

A tool to generate Tencent VAP and ByteDance Alpha Player videos from PNG sequences.

## Features

- Generate Tencent VAP videos with MD5 and JSON metadata
- Generate ByteDance Alpha Player videos with 1:1 left-right layout
- Automatic resolution detection
- Optimized for small file size

## Requirements

- Python 3
- FFmpeg
- ffprobe

## Usage

### Generate Tencent VAP video

```bash
python3 vap_master.py --input <input_directory> --output <output_file> --fps 25 --platform tencent-vap --bitrate 100
```

### Generate ByteDance Alpha Player video

```bash
python3 vap_master.py --input <input_directory> --output <output_file> --fps 25 --platform bytedance-alpha --bitrate 100
```

## Parameters

- `--input`: Path to directory containing PNG sequence
- `--output`: Path where final MP4 will be saved
- `--fps`: Frames per second (default: 25)
- `--platform`: Platform (tencent-vap or bytedance-alpha, default: tencent-vap)
- `--bitrate`: Encoding bitrate in kbps (default: 100)

## Output

### Tencent VAP

- `video.mp4`: VAP video file
- `md5.txt`: MD5 hash of the video
- `vapc.json`: VAP configuration file

### ByteDance Alpha Player

- `video.mp4`: Alpha Player video file
- `md5.txt`: MD5 hash of the video

## Example

```bash
# Generate Tencent VAP video
python3 vap_master.py --input "./frames" --output "./output/tencent_vap/video.mp4" --fps 25 --platform tencent-vap --bitrate 100

# Generate ByteDance Alpha Player video
python3 vap_master.py --input "./frames" --output "./output/bytedance_alpha/video.mp4" --fps 25 --platform bytedance-alpha --bitrate 100
```