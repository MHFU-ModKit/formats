# PMO Model Format Specification

## Overview

PMO (Portable Model Object) is the 3D model format used in Monster Hunter PSP games. It
contains mesh geometry, texture coordinates, and vertex data. **Skeleton/bind-pose and
animation are stored separately** — as *sibling sub-resources in the same model PAC*
(big monsters: `[0]=skeleton 0xC0000000`, `[1]=PMO`, `[2]=TMH`, `[3]=animation`). The
skeleton + bind-pose are now decoded (`tools/skeleton.py`,
`docs/ANIMATION_FORMAT.md`); the keyframe stream (sub-resource 3) is in progress.

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

### Header layout (verified on MHFU EU monster PMOs, 2026-06-13)

The first 8 bytes are **two char[4] fields** (magic + version); the numeric
header follows at **0x08**. `pmo.py` reads them separately
(`convert_pmo` reads `4s4s` then the `mh2`/`mh3` body reads `I4f2H8I` from 0x08).
The older "0x04 = scale X" row below was wrong — 0x04 is the version string.

| Offset | Size | Type    | Description |
|--------|------|---------|-------------|
| 0x00   | 4    | char[4] | Magic `"pmo\0"` |
| 0x04   | 4    | char[4] | Version `"1.0\0"` (MH2/MHP2G/MHFU) or `"102\0"` (MHP3rd) |
| 0x08   | 4    | uint32  | File size of this PMO |
| 0x0C   | 4    | float   | (unknown / bounding) |
| 0x10   | 4    | float   | Global scale X |
| 0x14   | 4    | float   | Global scale Y |
| 0x18   | 4    | float   | Global scale Z |
| 0x1C   | 2    | uint16  | Mesh count |
| 0x1E   | 2    | uint16  | Material count (`material_count_`) |
| 0x20   | 4    | uint32  | `mesh_header_offset` (mesh table) |
| 0x24   | 4    | uint32  | `tristrip_header_offset` (vertex-group table) |
| 0x28   | 4    | uint32  | `material_remaps_offset` |
| 0x2C   | 4    | uint32  | **`bone_data_offset`** (skeleton — see note) |
| 0x30   | 4    | uint32  | `material_data_offset` |
| 0x34   | 4    | uint32  | `mesh_data_offset` (GE display-list / vertex-data base) |

(Indices above as read by `struct.unpack('I4f2H8I', ...)` from 0x08:
`[0]`=size, `[2:5]`=scale, `[5]`=mesh count, `[7]`=mesh table, `[8]`=vgroup
table, `[10]`=**bone_data**, `[11]`=material table, `[12]`=GE base. Field names
are the decomp's `pmo_header` — see `tools/mhfu_external/mhp2g-decomp/include/model_base.hpp`.)

**`bone_data_offset` is present in the format but EMPTY for every monster**
(verified 2026-06-13: all **90/90** monster PMOs have
`bone_data_offset == material_data_offset`, i.e. a zero-length bone section). So
monster skeletons are NOT embedded in the PMO — they are built at runtime into the
engine's `Joint`/`Hierarchy` structures (see `docs/ANIMATION_FORMAT.md` → "Skeleton
system structurally decoded"). The field is likely used by player/weapon models.

### Monster mesh table — version "1.0" MONSTER variant (verified 2026-06-13)

MHFU/MHP2G **monster** PMOs share the `"1.0"` magic with MH2/MHF *player*
models but use a **different mesh table**. This is why the stock `convert_mh2_pmo`
(stride 0x20, format `2f2I4H2I`) crashed on monsters — only mesh 0 happened to
parse. The monster layout is:

| Field | Where | Notes |
|-------|-------|-------|
| Mesh record stride | **0x18** | not 0x20 |
| Vertex-group count | u16 @ mesh+0x10 | |
| Vertex-group start index | u16 @ mesh+0x12 | index into the vgroup table |
| Vertex-group record | 16 bytes, `2BH3I` | same as legacy |
| GE list address | `header[12] + vg[3]` | run the GE display list here |
| Material index | `vg[0]` → `material_table[vg[0]]` | (geometry verified; texture mapping unverified) |

`pmo.py` now auto-detects this via `convert_mhfu_monster_meshes()` (it validates
all offsets before emitting, so it is a no-op on non-monster files).
Verified: em01 = 19592 verts / 31 groups, em02 = 17037 verts / 23 groups,
em01 secondary PMO = 682 verts / 7 groups — all clean.

### Skinning: monsters are RIGID-bound (verified 2026-06-13)

**0 of 62** em01 vertex groups set the VTYPE weight bits → **no per-vertex blend
weights**. Each vertex group is bound to a single bone (the engine sets that
bone's matrix before drawing the group). `pmo.py` line ~82 now captures weights
into `vertex['weights']` for the models that *do* use blend skinning.

> **"Rigid" means no per-vertex weights — NOT "no skeleton".** Monsters absolutely
> have a full `Joint`/`Hierarchy` bone skeleton and animate it: the Tigrex overlay
> drives `pmo::drawWeightMesh` + per-`Joint` FK every frame, and the skeleton is built
> at spawn by EBOOT `0x088dc40c` from a `skel_src` blob. See `docs/ANIMATION_FORMAT.md`
> → "Monsters DO have a Joint skeleton". Rigid binding just means each mesh group rides
> one bone's matrix (no weight blending), which is exactly the implicit-positional
> mesh↔bone mapping below.

**Where is the per-group bone index? (investigated 2026-06-13)**
It is **not stored in the PMO PAC**:
- Mesh record (0x18): `+0x08` constant `0x80000006`, `+0x14` duplicates count/start,
  the two floats are per-part scales — no bone index.
- Vertex-group record (`2BH3I`): `vg[0]` is only the local group index within the
  mesh (used for the material lookup); `vg[1]`/`vg[2]` are always 0.
- GE display lists contain **no matrix commands** (`0x3A/0x3B` world, `0x42/0x43`
  bone all absent) — only `01/02/04/10/12/13/14/9b`.
- Sub-file 3 = material/color floats; sub-file 4 = bounding/hitbox floats;
  sub-file 5 = HITS hitbox data. No `0xC0000000` skeleton blob in a *small-monster*
  PAC (em01 = `file_06060`). **But BIG-monster PACs DO** — see next note.

> **Correction (2026-06-13): big monsters carry a real skeleton.** The proper monster
> model PAC is `file_0{em_id+0x17AB}.bin` (em01 = `file_06060`; the `file_06043` scanned
> earlier was a different/secondary asset PAC). **Big-monster PACs** (`file_06111`–
> `file_06159`, the ones with `em*.ovl` overlays) have a `0xC0000000` **skeleton + bind-
> pose blob as sub-resource 0** — `{[0]=skeleton, [1]=PMO, [2]=TMH, [3]=animation}`.
> Parse with `tools/skeleton.py`; format in `docs/ANIMATION_FORMAT.md`
> ("✅ SKELETON + BIND-POSE SOLVED"). Small monsters (em01) have no skeleton sub-resource
> (sub-0 = PMO) and use the implicit-positional mapping below.

**Conclusion — binding is IMPLICIT positional.** Strong evidence: em01 has **31**
mesh groups; the P3rd Blender repo's `skipped_bones.md` lists em01 (monster id 01)
geometry-less bones `{8,15,25}`. `31 meshes + 3 skipped = 34 bones (0..33)` — an
exact match. So mesh/group draw order maps 1:1 to skeleton bone index, **skipping
the geometry-less bones** in that monster's skip list. (The P3rd anim addon's
`bone_offset=2` + per-monster `missing_bones` params exist for exactly this
mapping.) Remaining gaps: (1) the **skeleton bind-pose transforms** are not in the
model file — they live in the engine's runtime `Joint`/`Hierarchy` structures
(structurally decoded 2026-06-13; the bind-pose is a `bind_pose{ Matrix4 transform;
Vec3 scale,rotation,position }` per `Joint`, in a `Hierarchy` of ≤4 root chains,
keyframes via `Hierarchy.motion_table`). See `docs/ANIMATION_FORMAT.md` → "Skeleton
system structurally decoded". The implicit mesh↔bone mapping above still holds (the
`Joint::func` tree-walk keys joints by `+0x114`, `-1` = empty, matching the skip
list). (2) The mapping is count-verified but not yet confirmed against a live
`Hierarchy` dump — the concrete next step (read `ModelBase.hierarchy.roots[]` live,
or `--xref` the overlay `motion_table` writer with `tools/eboot_dis.py`).

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

**Status (2026-06-13): weights are now captured.** `pmo.py` line ~82 no longer
discards them — it stores `vertex['weights'] = [w / weight_trans for w in raw_vertex]`
(OBJ export still ignores the field; importers can read the binding). NOTE:
MHFU **monster** PMOs set `weight = 0` on every vertex group (rigid skinning, see
below), so this path only fires for models that actually blend (e.g. player armor).

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

## Known Limitations (updated 2026-06-13)

1. **Skeleton bind-pose is runtime engine state, not a file blob.** Structurally
   decoded 2026-06-13 (`docs/ANIMATION_FORMAT.md`): the engine holds it in `Joint`
   objects (`bind_pose{ Matrix4 transform; Vec3 scale,rotation,position }`) inside a
   `Hierarchy` (≤4 root chains, keyframes via `motion_table`). The format is no longer
   unknown; the open work is dumping the populated *values* for a given monster (read
   the live `Hierarchy`, or trace the overlay `motion_table` writer). The *binding*
   (which bone each mesh attaches to) is solved — implicit positional, see "Skinning".
2. **No animation data in the PMO** - keyframes stored separately
   (see `docs/ANIMATION_FORMAT.md`).
3. **Geometry import works** - `pmo.py` converts monster PMOs (both model parts) to
   OBJ; weights captured when present. Full rigged import blocked only by (1).

## Blender / Noesis Import (tooling, 2026-06-13)

- **`mhff/psp/pmo.py`** (this repo) — PMO → OBJ. Now handles MHFU monster PMOs
  (auto-detect 0x18 mesh table) and captures skin weights.
- **`m2jean/mhfu-ios-pmo-plugin`** (Noesis, external) — PMO + **skeleton** parser for
  the **MHFU iOS** port (PMO version `"2.0"`, NOT PSP `"1.0"`). Best blueprint for the
  iOS skeleton node-tree (`idx/parent/left-child/right-sibling` int32 + bind matrix);
  re-derive offsets for PSP. PAC layout there is `[skeleton.bin, .pmo, .tmh, anim.bin]`.
- **`svanheulen/mhff io_import_scene_pmo.py`** — original static-mesh Blender addon
  (no skeleton/anim).

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

The PAC header is a simple offset/size table (parsed by `mhff/psp/package.py`,
verified on em01/em02 2026-06-13):

```
0x00  uint32  file_count
0x04  file_count × { uint32 offset, uint32 size }   // INTERLEAVED pairs
```

Each sub-file is `data[offset : offset+size]`. (Note the pairs are interleaved
`(off,size)`, NOT a table of offsets followed by a table of sizes.)

Each `emmodel/emXX.pac` file contains 6 sub-files:

| Index | Type | Size (typical) | Description |
|-------|------|----------------|-------------|
| 0 | PMO | 200-400KB | Main body model (`pmo\0 1.0`) |
| 1 | TMH | 80-200KB | Diffuse textures (`.TMH0.14`) |
| 2 | PMO | 5-15KB | Secondary model (shadow/LOD?) |
| 3 | float blob | 170 bytes | material/color floats + RGBA (NOT skeleton) — verified 2026-06-13 |
| 4 | float blob | 4KB | bounding/hitbox floats (was guessed "bone indices?" — **disproven** 2026-06-13) |
| 5 | HITS | 50-150KB | Hitbox collision data (`HITS` magic @ +0x10; offset table follows) |

**No skeleton/bone-index sub-file exists** in the model PAC. Sub-files 3 and 4
were checked byte-by-byte: both are float tables (radii ~hundreds, scales ~1.0,
RGBA color) consistent with hitbox/bounding/material data, not bone parent indices
or bind matrices.

### Extracting Monster Models

```python
# Using mhff package.py
from mhff.psp.package import extract_package

# Extract em01 model package (file 6060)
extract_package('file_06060.bin')
# Creates: file_06060.bin-0000 (PMO), file_06060.bin-0001 (TMH), etc.
```

### Overlay Files Also Contain Models

**Monster model PAC = `file_0{em_id+0x17AB}.bin`** (the DATA.BIN extract index equals
the file_id). Two layouts:
- **Big monsters** (those with an `em*.ovl` overlay; `file_06111`–`file_06159`):
  `[0]=skeleton (0xC0000000)`, `[1]=PMO`, `[2]=TMH`, `[3]=animation (0x64…)`.
- **Small monsters** (e.g. em01/Popo = `file_06060`): `[0]=PMO`, `[1]=TMH`, `[2]=PMO2`,
  `[3]/[4]=float blobs`, `[5]=HITS` — no skeleton sub-resource.

`file_06043` (an early mis-label for "em01 overlay") is a separate model-asset PAC
(PMO/TMH/PMO2/float/float/HITS) — NOT MIPS code, and not the em01 model PAC (that's
`file_06060`). The real `em*.ovl` AI overlays are MWo3 blobs at `file_06094`+.

## TODO: Undocumented Areas

- [x] Skeleton/bone hierarchy format — `0xC0000000` blob, `tools/skeleton.py`
- [~] Animation file format and linking — keyframe stream = big-mon PAC sub-resource 3
      (`0x64…`); interpolation = cubic `spline()`; decode in progress
- [ ] Weight painting data (monsters are rigid — no per-vertex weights)
- [ ] Hitbox definitions
- [ ] LOD (Level of Detail) data
- [ ] Shader/material properties

## References

- mhff PMO parser: https://github.com/svanheulen/mhff/blob/master/psp/pmo.py
- Blender addon: https://github.com/svanheulen/mhff/blob/master/psp/io_import_scene_pmo.py
