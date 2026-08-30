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

### Split-mesh PMOs: TWO mesh sets (verified 2026-06-17, file_06185 = Tigrex)

Some big-monster PMOs split their geometry into **two mesh sets**, and the
`header[5]` mesh table only covers the FIRST set. The header has a second count
and two extra table pointers that describe the rest:

| Field | Offset (struct `I4f2H8I` @ pmo+8) | Meaning |
|-------|-----------------------------------|---------|
| `header[5]` | u16 @ pmo+0x1C | mesh count for **set A** (mesh table @ `header[7]`, stride 0x18) |
| `header[6]` | u16 @ pmo+0x1E | mesh count for **set B** |
| `header[9]` | u32 @ pmo+0x28 | **end of the vgroup table** (set-B index table @ this offset) |
| `header[10]`| u32 @ pmo+0x2C | set-B mesh table (`(material, vgroup)` byte-pairs) |

`file_06185` (the native-quest Tigrex): set A = 7 meshes → 23 vgroups (the
**extremities** — tail/claws/head, ~370 verts); the **body** is in vgroups the
set-A table never references. Walking only `header[5]` drops the body (why early
imports showed only the extremities).

**Robust rule:** the full vgroup table spans **`[header[8], header[9])`**, so
`vgroup_count = (header[9] − header[8]) / 0x10`; enumerate ALL of them, not just
the ones the mesh table indexes. `pmo.py::_append_unreferenced_vgroups` appends
any vgroup the mesh-table walk missed (file_06185: 370 → **4128 verts**, full
model). Single-set monsters (mesh table already covers every vgroup) are
unaffected; all 49 big-mon PACs still round-trip byte-identical.

### 🟢 Per-vertex skinning ports LOSSLESSLY — measured, not assumed (2026-08-29)

The long-standing "MHP3rd is blend-skinned, MHFU is rigid" framing was wrong on the
second half, and it made the port look like a format gap that had to be bridged. It is
not one. **Both games use the same per-vertex blend skinning and both are bound by the
PSP GE's 8-bone-matrix limit.** Scanned across every skinned MHP3rd PAC (**2120** with a
v102 PMO + a `0x80000000` skeleton): the largest `boneCount` on any vgroup anywhere is
**exactly 8**, and **zero** vgroups exceed it — so `pmo_skin`'s `max_pal=8` cap can never
fire on a source's authentic skin.

`tools/skin_fidelity.py` closes it end to end: parse the source's v102 palette → run the
porter's skinning stage → encode a native MHFU PMO → decode it with the independent
reader → compare per vertex. **226 of 226** in-quest MHP3rd monsters keep every vertex's
exact bone set with a **max weight error of 0.0** — not "within tolerance": MHP3rd stores
weights as u8/128 and so does our encoder, so the re-quantisation is an identity.

The remaining generalisation gap is NOT skinning — it is the anim **stream partition**
(`docs/ANIMATION_FORMAT.md` "Stream partition").

### Skinning: small monsters RIGID, big monsters often SKINNED

**0 of 62** em01 (small-monster) vertex groups set the VTYPE weight bits → **no
per-vertex blend weights**; each group is rigid-bound to one bone. But big
monsters CAN be skinned: `file_06185`'s 214 vgroups all carry blend weights
(weight-count 1–8 per vertex, VTYPE weight bits set). `pmo.py` (`run_ge`)
captures weights into `vertex['weights']` for the models that use blend skinning.

### MHP3rd v102 geometry parse + cross-game skinning (porter, 2026-06-22)

**v102 GE-list walker — `pmo_p3rd.run_ge_v102`.** MHP3rd `102` PMOs encode geometry as
PSP GE display lists that **address vertices THROUGH an index buffer and dedup by
address** (tristrips share verts). The MHFU `1.0` walker (`pmo.run_ge`) read vertices
flat/sequentially → it over-expanded a v102 mesh to ~34k garbage verts. `run_ge_v102`
(ported faithfully from AsteriskAmpersand's PMO-Importer `build_prim`) walks
`VADDR/IADDR/VTYPE/PRIM/RET`, reads the per-`PRIM` index buffer, fetches each vertex at
`base + vertex_address + index*stride`, dedups, and builds tristrip faces with the
`FFACE` winding flip. Correct VTYPE decode too: **4-bit `weightCount` (bits 14-18)** +
**`bypass` bit (23)** for normalized/raw scaling, plus the exact field sizes (int16 pad on
8-bit UV; trailing `w` on 8/16-bit normals). Result on the Brute (`file_05248` + companion
`file_05249`): clean **2689 verts / 2973 faces**. Geometry is often in a **companion file**
(`ge_base >= pmo size` → read GE from `file_<model+1>`); `pmo_p3rd.parse(pmo, geo_blob=)`.

**MHP3rd v102 bone palette / per-vertex skinning — `pmo_p3rd` (RE'd + validated 2026-06-29).**
CORRECTION: MHP3rd big monsters are **blend-skinned, NOT rigid.** The real Brute
(`file_05248`) carries genuine per-vertex weights — 1492/2689 verts have fractional
(0<w<1) influences, 1–6 bones each. (The earlier "all vgroups weightCount=0 / rigid
pieces" claim came from a *misidentified* Lavasioth lobby model `file_04898`.) The v102
skin uses the **SAME palette model as MHFU** (see "Skinning" above):
- **Header field [10]** (`skeletonOffset`, the one long mislabeled `unk10`) = the **bone
  palette** = a `Weight{slot:u8, bone:u8}[]` array.
- **vgroup record `2BH3I`**: `vg[0]`=materialOffset, **`vg[1]`=boneCount**, **`vg[2]`=
  cumulativeBoneCount** (offset into the palette — NOT a single `boneref`), then the 3 GE
  pointers. The engine keeps a running `aux[slot]=bone`; each vgroup consumes its
  `boneCount` palette entries at `palette[cum : cum+bc]`.
- **per vertex**: the VTYPE `weightCount` fractions blend `aux[0..wc-1]`, so influences =
  `[(palette[cum+k].bone, weight[k])]`. `bone` indexes the source `0x80000000` skeleton.
- The real **vgroup count is `max(vg_start+vg_count)` over the mesh table**, NOT header
  field [6] (unreliable — e.g. Brute reports 24, real is 88).
- Validated zero-error on `file_05248`: 300/304 palette entries covered by the 88 vgroups,
  every slot sequential, every bone < 46 (the skeleton's bone count). See memory
  `p3rd-v102-bone-palette-decoded`.

`pmo_p3rd.parse` now reads this palette (`_resolve_running_palette` from `pmo_skin`) and
attaches each vertex's authentic `influences = [(bone, weight)]` (source-skeleton indices).

**Authentic-skin port — `pmo_skin.from_source_influences`.** The principled path: pair
each vertex's source influences with the OUTPUT rig (source-skeleton mode: source bone
`i → i + lead_pad`, 1:1) → the monster's REAL skin, no guess, no oracle. Caps each vgroup
at the PSP 8-matrix limit. Selected by `port_p3rd` `skin="source"` (auto-upgraded from
`"auto"` in `source_skeleton` mode when the source carries weights). This is what
`build_p3rd_port.py --source-skeleton --skin source` (the Brute **v62**) uses, replacing
the `auto_skin` guess that caused the source-skeleton "crunch / bends-wrong" deformation.

**Cross-game skinning (no-reference fallback) — `pmo_skin.auto_skin`.** When the source
has no usable weights (or a no-similar-native target), DERIVE blend skinning instead.
`auto_skin(mesh_groups, bone_world, parents=, …)` weights each vertex to nearby bones with
these controls (all proven on the Brute):
- `segment=True` (default): **bone-SEGMENT distance** (distance to the bone's line from its
  parent, not the joint) — keeps a chest vertex on the spine instead of the euclidean-near
  wing-root joint (fixes 679u stretch flaps).
- `parents=`+`hops`: **chain-aware** — a vertex blends only bones within `hops` tree edges
  of its nearest bone (a tail vert blends adjacent tail joints, not a leg bone).
- `region_lock` (default): confine a whole source vgroup (= one rigid body part) to its
  dominant bone's neighborhood.
- `exclude=`: drop host joints the anim leaves at rest (so geometry never pins to an
  un-rotating joint → the tail kink). `bone_match.fill_unmatched` handles a host chain
  LONGER than the source (Tigrex tail 5 joints vs Brute 4): an unmatched joint inherits a
  neighbour's source instead of compounding rotation on the shared one.
The native blend-skinning encoder is `pmo_skin.encode`/`build` (running bone-palette +
per-vertex weights; byte-exact round-trip of the native Tigrex `file_06185`).

**The porter — `port_p3rd.port_monster` (CLI `tools/build_p3rd_port.py`, Blender operator
"Port MHP3rd Monster" / `exporter.port_p3rd_monster_pac`, byte-identical).** Splices an
MHP3rd monster onto an MHFU host frame (e.g. the Tigrex `file_06185`): its v102 geometry
chain-aware-skinned onto the host `0xC0000000` skeleton + its OWN textures + its OWN moveset
(see `docs/ANIMATION_FORMAT.md`). Generalized for the Tigrex-family; first port = the
authentic Brute Tigrex (`file_05248`/`05250`). One OPEN visual issue is placement, not the
model: a swap-spawned monster's world Y is engine-pinned to a ground target of 0 (it isn't
terrain-registered) → it sinks; see `docs/agent_memory_map.md` `+0x200`.

### TMH textures + in-memory decode (2026-06-17)

`mhfu_model/tmh.py::decode_tmh(raw)` decodes the TMH sub (PAC sub 2) to RGBA8 with
**no PIL dependency** (ported from `mhff/psp/tmh.py`; modes 0–8 + CLUT, BGRA→RGBA
swap; DXT3/5 modes 9/10 skipped). Byte-exact vs the PIL reference on all of
`file_06185`'s 5 textures. The Blender importer turns each into a packed image +
Principled material, **explicitly UV-mapped** (a `ShaderNodeUVMap` → the texture's
`Vector` input; without it the texture falls back to generated coords and smears).

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
**small** monster PMOs (em01-class) set `weight = 0` on every vertex group (rigid
skinning), but **big** monsters blend (e.g. Tigrex `file_06185`, 1–8 bones/vertex) — and
so do MHP3rd big monsters (see the v102 bone-palette section above). The bone *indices*
live in the PMO bone palette (header field 10), not the per-vertex stream.

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
   (which bone each mesh attaches to) is solved — the vgroup **bone palette**, see
   "Skinning". ⚠️ "implicit positional" (draw order == bind index) is the FALLBACK for
   PMOs with no palette, and reading it as the rule is what welded 166 of file_06185's
   214 groups onto one bone in the Blender importer for two months.
2. **No animation data in the PMO** - keyframes stored separately
   (see `docs/ANIMATION_FORMAT.md`).
3. **Geometry import works** - `pmo.py` converts monster PMOs (both model parts) to
   OBJ; weights captured when present. Full rigged import blocked only by (1).
4. **Topology editing — SOLVED (2026-06-18).** Reshape (move verts at constant
   topology/size) = `tools/mhfu_model/pmo.py` in-place re-encode (byte-exact). ADDING
   vertices/faces = `tools/mhfu_model/pmo_topology.py`: a byte-level rebuild of the
   `geBase` GE-list region (the part from `header[12]` to EOF = per-vgroup
   `[GE list .. RET] + [vertex buffer] + [index buffer]`, 16-byte aligned). It re-lays
   the region, patches each list's `VADDR`/`IADDR` args + each vgroup record's
   `I3=geoff/I4=vbuf/I5=ibuf` (geBase-relative), and bumps `header[0]`; tables before
   `geBase` stay byte-identical. Grows within an existing vgroup (8-bit-index 256-vert/
   group cap; a NEW vgroup has undefined bone binding). PROVEN live in-game: added
   geometry renders (the engine's decode is data-driven). New verts currently inherit
   vertex0's UV/normal/weights (polish TODO). Delivered live via the `framework/prx`
   relocate-source path (`mhfu.inject_relocate`) — see CLAUDE.md Phase 5.

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
