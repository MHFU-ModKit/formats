# Animation Format Research

## Status: UNDOCUMENTED (Critical Blocker)

The animation/skeleton format is the #1 blocker for monster model export with full rigging. This document tracks current research findings.

## What We Know

### Animation-Related Files

| File Type | Magic | Location | Purpose |
|-----------|-------|----------|---------|
| Motion Tables | `Head `/`Prog` | motion/*.bin | Animation lookup/data |
| AHI Files | None (null start) | emmodel/em32/ | Unknown (animation/hitbox?) |
| Unknown | In PAC index 4 | emmodel/*.pac | Possibly bone indices |

### Motion Table Files (513 total)

**Location**: Various indices, pattern `motion/*_tbl.bin`

**Known files**:
- `motion/plcom_tbl.bin` (index 61) - Player common animations
- `motion/w00_tbl.bin` to `w10_tbl.bin` (3377-3387) - Weapon animations
- `motion/em04_tbl.bin` (6323) - Monster em04 animations
- `motion/em10_tbl.bin` (6324) - Monster em10 animations

**IMPORTANT**: Only 2 monster motion tables exist! Most monsters must:
1. Share animation systems
2. Have animations embedded in overlays
3. Use runtime-generated animations

### Head/Prog Format

```
+0x00: "Head " (5 bytes, space-padded)
+0x05: Padding (3 bytes)
+0x08: Unknown uint32
+0x0C: Unknown uint32
+0x10: Data size?
+0x14: More header data...
+0x20: "Prog" section marker
+0x24: Prog size
+0x28: Animation count?
+0x2C: Padding (0xFF bytes)
...
Animation data follows
```

### Weapon Motion Tables (PAC containers)

The weapon motion tables (w00-w10) are actually PAC containers:
```
weapon_motion.pac:
├── [0] PMO - Weapon trail/effect model
└── [1+] Animation keyframe data
```

The animation data after the PMO contains:
- Bone reference indices (0x00-0x0F patterns)
- Compressed keyframe data
- Timing information

### AHI File Format (em32.ahi)

Only found for em32 (Rajang), size 250KB.

Structure:
```
+0x00: 16 null bytes
+0x10: Data begins
      - First byte appears to be entry count or type
      - Variable-length records follow
      - Appears to be compressed/encoded
```

Hypothesis: AHI = Animation/Hitbox Information
- May contain both animation keyframes and per-frame hitbox states
- Format appears to use some form of delta encoding

## What's Missing

### Skeleton/Bone Hierarchy

**Not found in**:
- PMO files (only weight data, no bone definitions)
- TMH files (textures only)
- HITS files (hitbox collision only)

**Possible locations**:
1. Embedded in overlay (.ovl) executable code
2. Hardcoded in main EBOOT.BIN
3. In the unknown PAC sub-file (index 4)
4. Generated at runtime from bone count in PMO

### Animation Keyframe Format

**Unknown**:
- Keyframe encoding (quaternions? euler? matrices?)
- Timing/interpolation method
- Bone-to-vertex mapping

### Animation-to-Model Binding

**Unknown**:
- How animations reference bones
- How bones reference vertices
- Runtime animation blending system

## Research Approaches

### 1. PPSSPP Memory Debugging

Use runtime debugging to:
- Set breakpoints on file loading functions
- Watch memory regions where animations load
- Trace function calls during animation playback
- Compare memory states between different animations

Key addresses:
- File loading: `0x0884E158`, `0x0884E730`
- Entity array: `0x09C122B0`

### 2. Comparative Analysis

Compare:
- Weapon animations (simpler, known structure)
- Player animations vs monster animations
- Different monsters to find common patterns
- Same monster with different animation states

### 3. Disassembly

Analyze overlay code:
- Animation loading routines
- Bone transformation functions
- Vertex skinning code

Tools: Ghidra, IDA Pro, Binary Ninja

### 4. Trial and Error

Modify animation data and observe:
- Change values in motion tables
- Corrupt specific bytes to identify fields
- Replace one animation with another

## Next Steps

1. **Extract bone weights from PMO** - Data exists, parser ignores it
2. **Analyze PAC sub-file 4** - May contain bone indices
3. **Compare em04/em10 motion tables** - Only 2 monster animations documented
4. **Runtime memory analysis** - Watch animation loading in PPSSPP
5. **Disassemble overlay code** - Find animation functions

## References

- mhfu-re PPSSPP scripts: `tools/mhfu-re/tools/ppsspp-py/`
- Rajang vtable trace: Shows runtime entity structure
- FUComplete fileidgen.asm: File loading hooks
