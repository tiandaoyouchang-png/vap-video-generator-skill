---
name: "vap-generator"
description: "生成符合腾讯 VAP 格式的视频，支持指定布局和压缩参数。当用户需要将 PNG 序列转换为 VAP 视频时调用。"
---

# VAP 视频生成器

## 功能

- 将 PNG 序列转换为符合腾讯 VAP 格式的 MP4 视频
- 支持指定 VAP 布局参数（rgbFrame 和 aFrame）
- 自动生成 MD5 和 VAPC JSON 元数据文件
- 优化文件大小，确保视频在 1M 以内

## 为什么需要这个技能

VAP（Video Animation Player）是腾讯的高性能视频动画解决方案，支持透明通道和动态融合效果。生成符合规范的 VAP 视频需要注意以下几点：

1. **布局规范**：VAP 不是简单的左右拼接视频，而是有特定的布局规范，包括 RGB 区域和 Alpha 区域在画布上的位置和尺寸。

2. **压缩参数**：VAP 视频尺寸较大（如 1680×1680），需要使用适当的压缩参数（低码率、高 CRF）来控制文件大小。

3. **元数据**：需要生成 VAPC JSON 文件和 MD5 哈希文件，用于播放器配置和文件验证。

## 布局参数

VAP 视频的布局由以下参数定义：

```json
{
  "info": {
    "v": 2,          // 版本
    "f": 45,         // 帧数
    "w": 1668,       // 输入帧宽度
    "h": 1112,       // 输入帧高度
    "fps": 25,       // 帧率
    "videoW": 1680,  // 输出视频宽度
    "videoH": 1680,  // 输出视频高度
    "aFrame": [0, 1116, 834, 556],   // Alpha 区域：[x, y, width, height]
    "rgbFrame": [0, 0, 1668, 1112],  // RGB 区域：[x, y, width, height]
    "isVapx": 0,     // 是否为 VAPX 格式
    "orien": 0       // 方向
  }
}
```

## 使用方法

### 命令行参数

```bash
python3 vap_master.py --input <输入目录> --output <输出文件> --fps <帧率> --mode <模式> --bitrate <码率>
```

- `--input`：PNG 序列所在目录
- `--output`：输出 VAP 视频文件路径
- `--fps`：帧率（默认 25）
- `--mode`：布局模式（standard 或 mask-left，默认 standard）
- `--bitrate`：码率（默认 100，建议 80-100 以控制文件大小）

### 示例

```bash
python3 vap_master.py --input "/path/to/png/frames" --output "/path/to/output/video.mp4" --fps 25 --mode standard --bitrate 100
```

## 常见问题及解决方案

### 1. 视频无法打开

**原因**：布局参数不正确，RGB 和 Alpha 区域的位置或尺寸不符合 VAP 规范。

**解决方案**：确保使用正确的布局参数，特别是 `aFrame` 和 `rgbFrame` 的值。

### 2. 文件大小过大

**原因**：码率设置过高，或者压缩参数不够优化。

**解决方案**：
- 降低码率到 80-100 kbps
- 使用较高的 CRF 值（30-35）
- 使用 `ultrafast` 预设加快编码速度

### 3. FFmpeg 命令执行失败

**原因**：命令参数中的引号或特殊字符被 shell 错误解析。

**解决方案**：确保 `filter_complex` 参数被正确引号包裹，避免分号和方括号被 shell 解析为多个命令。

### 4. FFmpeg 无限循环

**原因**：使用 `-vf` 时，`color` 滤镜生成了无限长度的背景流。

**解决方案**：使用 `-frames:v` 参数限制处理的帧数，或者使用 `-filter_complex` 替代 `-vf`。

## 技术原理

1. **帧处理**：使用 FFmpeg 读取 PNG 序列，提取 RGB 和 Alpha 通道。

2. **布局合成**：根据指定的布局参数，将 RGB 和 Alpha 区域合成到指定尺寸的画布上。

3. **视频编码**：使用 H.264 编码器，设置适当的码率和 CRF 值，确保文件大小在 1M 以内。

4. **元数据生成**：计算视频文件的 MD5 哈希，并生成包含布局参数的 VAPC JSON 文件。

## 输出文件

- `video.mp4`：生成的 VAP 视频文件
- `md5.txt`：视频文件的 MD5 哈希值
- `vapc.json`：VAP 播放器配置文件

## 最佳实践

1. **使用官方工具**：优先使用腾讯官方的 VapTool（animtool.jar + mp4edit）来生成 VAP 视频，它会自动处理布局和 vapc atom 的写入。

2. **正确命名帧文件**：确保 PNG 帧文件按顺序命名（如 000.png, 001.png, 002.png...）。

3. **验证布局参数**：根据实际需求调整 `aFrame` 和 `rgbFrame` 参数，确保符合 VAP 规范。

4. **优化压缩参数**：使用低码率和高 CRF 值，确保视频文件大小在 1M 以内。

5. **生成元数据**：确保生成 MD5 和 VAPC JSON 文件，以便播放器正确解析和验证视频。