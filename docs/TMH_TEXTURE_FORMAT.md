# TMH Texture Format Specification

## Overview

TMH (Texture Material Handler) is the texture package format used in Monster Hunter PSP games. It contains one or more textures with various pixel formats.

## File Structure

```
+----------------------+
| Signature (8 bytes)  |  ".TMH0.14"
+----------------------+
| File Metadata (8)    |
+----------------------+
| Image Entry 1        |
|   - Image Header     |
|   - Pixel Header     |
|   - Pixel Data       |
|   - CLUT (optional)  |
+----------------------+
| Image Entry 2        |
+----------------------+
| ...                  |
+----------------------+
```

## Signature

```
Offset 0x00: ".TMH0.14" (8 bytes ASCII)
```

## File Metadata

| Offset | Size | Type   | Description |
|--------|------|--------|-------------|
| 0x08   | 4    | uint32 | Unknown/flags |
| 0x0C   | 4    | uint32 | Image count or total size |

## Image Entry

### Image Header (16 bytes)

| Offset | Size | Type   | Description |
|--------|------|--------|-------------|
| 0x00   | 4    | uint32 | Image width |
| 0x04   | 4    | uint32 | Image height |
| 0x08   | 4    | uint32 | Unknown |
| 0x0C   | 4    | uint32 | Unknown |

### Pixel Header (16 bytes)

| Offset | Size | Type   | Description |
|--------|------|--------|-------------|
| 0x00   | 4    | uint32 | Pixel format mode |
| 0x04   | 4    | uint32 | Data size |
| 0x08   | 2    | uint16 | Block width |
| 0x0A   | 2    | uint16 | Block height |
| 0x0C   | 4    | uint32 | CLUT offset (if indexed) |

## Pixel Format Modes

| Mode | Format | Bits/Pixel | Description |
|------|--------|------------|-------------|
| 0    | RGB565 | 16 | 5-6-5 bit RGB |
| 1    | RGBA5551 | 16 | 5-5-5-1 bit RGBA |
| 2    | RGBA4444 | 16 | 4-4-4-4 bit RGBA |
| 3    | RGBA8888 | 32 | Full 8-bit RGBA |
| 4    | Indexed4 | 4 | 4-bit palette index |
| 5    | Indexed8 | 8 | 8-bit palette index |
| 6    | Grayscale4 | 4 | 4-bit grayscale |
| 7    | Grayscale8 | 8 | 8-bit grayscale |
| 8    | DXT1 | 4 | S3TC DXT1 compression |
| 9    | DXT3 | 8 | S3TC DXT3 (NOT IMPLEMENTED) |
| 10   | DXT5 | 8 | S3TC DXT5 (NOT IMPLEMENTED) |

## Pixel Block Storage

Textures are stored in **swizzled block format** for PSP GPU efficiency:

- **Standard formats (0-7)**: 8x8 pixel blocks
- **DXT formats (8-10)**: 4x4 pixel blocks

### Deswizzling Algorithm

```python
def deswizzle(data, width, height, block_size=8):
    output = bytearray(len(data))
    blocks_x = width // block_size
    blocks_y = height // block_size

    src_idx = 0
    for by in range(blocks_y):
        for bx in range(blocks_x):
            for py in range(block_size):
                for px in range(block_size):
                    dst_x = bx * block_size + px
                    dst_y = by * block_size + py
                    dst_idx = (dst_y * width + dst_x)
                    output[dst_idx] = data[src_idx]
                    src_idx += 1

    return output
```

## Color Lookup Table (CLUT)

For indexed color modes (4, 5), a CLUT follows the pixel data:

| Mode | Palette Size | Entry Format |
|------|--------------|--------------|
| Indexed4 | 16 entries | RGBA8888 (4 bytes each) |
| Indexed8 | 256 entries | RGBA8888 (4 bytes each) |

## DXT1 Compression

DXT1 blocks are 4x4 pixels, 8 bytes per block:
- 2 bytes: Color 0 (RGB565)
- 2 bytes: Color 1 (RGB565)
- 4 bytes: 2-bit indices for 16 pixels

```python
def decode_dxt1_block(block):
    c0 = struct.unpack('<H', block[0:2])[0]
    c1 = struct.unpack('<H', block[2:4])[0]
    indices = struct.unpack('<I', block[4:8])[0]

    # Decode RGB565 colors
    colors = [decode_rgb565(c0), decode_rgb565(c1)]

    # Generate interpolated colors
    if c0 > c1:
        colors.append(lerp_color(colors[0], colors[1], 1/3))
        colors.append(lerp_color(colors[0], colors[1], 2/3))
    else:
        colors.append(lerp_color(colors[0], colors[1], 1/2))
        colors.append((0, 0, 0, 0))  # Transparent

    # Apply indices to pixels
    pixels = []
    for i in range(16):
        idx = (indices >> (i * 2)) & 0x3
        pixels.append(colors[idx])

    return pixels
```

## Output Format

The mhff TMH parser outputs:
- RGBA format (4 bytes per pixel)
- Optional BGRA byte order for compatibility
- Standard image dimensions (deswizzled)

## Extraction Command

```bash
python -m mhff.psp.tmh extract input.tmh output_dir/
```

## Known Limitations

1. DXT3 and DXT5 decompression not implemented
2. Some edge cases with non-power-of-2 textures
3. Only tested extensively on MHP3rd textures

## References

- mhff TMH parser: https://github.com/svanheulen/mhff/blob/master/psp/tmh.py
- PSP GE texture formats: https://www.psdevwiki.com/psp/GE
