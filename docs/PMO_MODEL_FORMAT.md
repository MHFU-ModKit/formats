# PMO Model Format Specification

## Overview

PMO (Portable Model Object) is the 3D model format used in Monster Hunter PSP games. It contains mesh geometry, texture coordinates, and vertex data but **animation and skeleton data are stored separately and not yet fully documented**.

## File Versions

| Version | Game | Characteristics |
|---------|------|-----------------|
| 1.0     | MH2/MHP2G/MHFU | Global scaling |
| 102     | MHP3rd | Per-mesh scaling |

## File Structure

```
+-------------------+
| Header (0x38)     |
+-------------------+
| Mesh Data         |
+-------------------+
| Vertex Groups     |
+-------------------+
| Material Refs     |
+-------------------+
```

### Header (0x38 bytes)

| Offset | Size | Type    | Description |
|--------|------|---------|-------------|
| 0x00   | 4    | char[4] | Magic number |
| 0x04   | 4    | float   | Global scale X |
| 0x08   | 4    | float   | Global scale Y |
| 0x0C   | 4    | float   | Global scale Z |
| 0x10   | 4    | uint32  | Mesh count |
| 0x14   | 4    | uint32  | Offset to mesh data |
| ...    | ...  | ...     | Additional offsets |

## Vertex Format (VTYPE Command)

Vertices are stored with flexible formatting determined by a VTYPE command. Each vertex can include any combination of:

### Position Data
- 3 signed bytes (scaled)
- 3 signed shorts (scaled)
- 3 floats (direct)
- Optional bypass transform flag

### Normal Data
- 3 signed bytes
- 3 signed shorts
- 3 floats

### Texture Coordinates
- 2 bytes (0-255 range, scaled)
- 2 shorts (scaled)
- 2 floats (direct UV)

### Vertex Colors
| Format | Bits | Description |
|--------|------|-------------|
| RGB565 | 16 | 5-6-5 bit RGB |
| RGBA5551 | 16 | 5-5-5-1 bit RGBA |
| RGBA4444 | 16 | 4-4-4-4 bit RGBA |
| RGBA8888 | 32 | 8-8-8-8 bit RGBA |

### Vertex Weights (Partially Documented)

The PMO format DOES contain vertex weight data, but the existing parser ignores it.

From `mhff/psp/pmo.py` line 110-114:
```python
weight = (command >> 9) & 3
if weight != 0:
    count = ((command >> 14) & 7) + 1
    vertex_format += str(count) + (None, 'B', 'H', 'f')[weight]
    weight_trans = (None, 0x80, 0x8000, 1)[weight]
```

**Weight encoding**:
- `weight = 1`: Byte weights (0-127 scaled to 0.0-1.0)
- `weight = 2`: Short weights (0-32767 scaled)
- `weight = 3`: Float weights (direct)

**Bone count**: `((command >> 14) & 7) + 1` gives 1-8 bones per vertex

**Current limitation**: Line 82 has `pass` - weight data is read but discarded:
```python
if weight_trans is not None:
    pass # NOTE: the OBJ format does not support vertex weights
```

This is a key opportunity - the weight data EXISTS, just isn't being used

## Mesh Structure

Each mesh contains:
- Vertex group indices
- Face definitions (triangles or triangle strips)
- Material/texture references
- Per-mesh scale (version 102 only)
- Front-face culling order

## Vertex Transformation

Raw vertex coordinates are transformed using scale factors:

```python
final_position = raw_position / scale_divisor

# Where scale_divisor is derived from header scaling values
```

## Face Primitives

| Type | Description |
|------|-------------|
| Triangles | Direct triangle list |
| Triangle Strip | Connected triangle strip |
| Triangle Fan | Fan from central vertex |

## Known Limitations

1. **No skeleton data** - Bone hierarchy not in PMO file
2. **No animation data** - Keyframes stored separately
3. **No rigging info** - Weight painting undocumented
4. **Export only** - Current tools only export to OBJ (static geometry)

## Blender Import

The mhff library includes a Blender addon (`io_import_scene_pmo.py`) that can import PMO files as static meshes:

```python
# Outputs Wavefront OBJ format
# Loses Monster Hunter-specific data
# No animation/skeleton support
```

## Monster Model Locations

Monster models are stored in PAC container files within DATA.BIN.

### File Index Pattern

| Monster | Overlay (AI) | Model Package | Sound Files |
|---------|--------------|---------------|-------------|
| em01 | 6043 | 6060 | 6149-6151 |
| em02 | 6044 | 6061 | 6152-6154 |
| em03 | - | 6062 | ... |
| ... | ... | ... | ... |
| em32 | - | 6091 | ... |

### PAC Container Structure

Each `emmodel/emXX.pac` file contains 6 sub-files:

| Index | Type | Size (typical) | Description |
|-------|------|----------------|-------------|
| 0 | PMO | 200-400KB | Main body model |
| 1 | TMH | 80-200KB | Diffuse textures |
| 2 | PMO | 5-15KB | Secondary model (shadow/LOD?) |
| 3 | Unknown | 170 bytes | Position/scale data |
| 4 | Unknown | 4KB | Bone indices? |
| 5 | HITS | 50-150KB | Hitbox collision data |

### Extracting Monster Models

```python
# Using mhff package.py
from mhff.psp.package import extract_package

# Extract em01 model package (file 6060)
extract_package('file_06060.bin')
# Creates: file_06060.bin-0000 (PMO), file_06060.bin-0001 (TMH), etc.
```

### Overlay Files Also Contain Models

Some `overlay/emXX.ovl` files are ALSO PAC containers with the same structure as emmodel packages. This appears to be for monsters that need AI code bundled with their assets

## TODO: Undocumented Areas

- [ ] Skeleton/bone hierarchy format
- [ ] Animation file format and linking
- [ ] Weight painting data
- [ ] Hitbox definitions
- [ ] LOD (Level of Detail) data
- [ ] Shader/material properties

## References

- mhff PMO parser: https://github.com/svanheulen/mhff/blob/master/psp/pmo.py
- Blender addon: https://github.com/svanheulen/mhff/blob/master/psp/io_import_scene_pmo.py
