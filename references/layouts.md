# Layout semantics

For a cleaned source frame W x H:

## ByteDance Alpha Player
- RGB: [0, 0, W, H]
- Alpha: [W, 0, W, H]
- Video: 2W x H

## Tencent mask-left
- Alpha: [0, 0, W, H]
- RGB: [W, 0, W, H]
- Video: 2W x H

## Tencent standard
Use official VapTool and validate its `vapc.json`; do not invent fixed coordinates.

If W == H, each half is 1:1 but the final side-by-side video is 2:1.
