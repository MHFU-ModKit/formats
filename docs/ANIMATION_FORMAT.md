# Animation Format Research

## Status: SOLVED — full rigged-monster pipeline is static (2026-06-13)

Everything Blender needs for rigged big-monster import/export is now decoded from
static analysis alone:
- **Geometry** → `tools/mhff/psp/pmo.py`
- **Skeleton + bind-pose** → `tools/skeleton.py` (PAC sub-0, `0xC0000000` blob;
  validated on Tigrex + 66 monsters) — see "✅ SKELETON + BIND-POSE SOLVED".
- **Animation keyframes** → `tools/anim.py` (PAC sub-3, P3rd-style pack;
  validated on Tigrex, 22 anims) — see "✅ KEYFRAME STREAM SOLVED".
- **Mesh↔bone binding** → implicit positional (`docs/PMO_MODEL_FORMAT.md`).
- **Interpolation** → cubic `spline()` with ease-in/out tangents.

The engine classes (`Joint`/`Hierarchy`, `Joint::update`, builders) are named + laid out
via the decomp + decrypted EU EBOOT (`tools/eboot_dis.py`). Small monsters (em01/Popo)
have no skeleton sub-resource and ride a rigid/shared path.

### How: decrypted EBOOT + decomp symbol map

* **Decrypted EBOOT** = `workspace/extracted/PSP_GAME/SYSDIR/BOOT.BIN` (an ELF;
  `EBOOT.BIN` is the `~PSP`-encrypted one). Single PT_LOAD: file `0x25b4` → VA
  `0x08804000`, size `0x1c7a90` — covers all `0x088xxxxx`/`0x089xxxxx` code.
* **Disassembler harness:** `tools/eboot_dis.py` (`<va> [n]`, `--words`, `--xref`).
* **Address delta:** in the animation/skeleton CODE region the decomp's JP addresses
  map to EU by a constant **+8** (verified: `Joint::update`, `pmo::compile`,
  `pmo::drawWeight`, `Joint::func` each land exactly on a prologue; `Joint::func`
  EU `0x0885F928` == our previously-pinned tree-walker). The **+8 holds for code
  only** — vtable/data symbols (e.g. `__vt__5Joint`) sit in a different region with
  their own delta; verify per-symbol.

### Engine skeleton classes (from `joint.hpp` / `model_base.hpp`)

```c
struct bind_pose {           // 0x80 bytes
    ScePspFMatrix4 transform;    // +0x00
    ScePspFVector3 scale;        // +0x40
    ScePspFVector3 rotation;     // +0x4C
    ScePspFVector3 position;     // +0x58
    u16 f0x64[14];               // +0x64
};
struct Joint {               // a BONE; ~0x250 bytes; virtual (vtable @+0x00)
    // vptr; { ~Joint(); update(Matrix4* parent, Matrix4* out, float x,y,z); }
    ScePspFVector3 f0x4;         // +0x04
    ScePspFMatrix4 f0x10;        // +0x10
    ScePspFMatrix4 f0x50;        // +0x50
    ScePspFMatrix4 localPose;    // +0x90   (Joint::update writes/uses this)
    ScePspFMatrix4 globalPose;   // +0xD0
    u16 f0x110, f0x112, key, f0x116;  // +0x110.. ; `key` @+0x114 = anim node id
    float f0x118, f0x11c;        // +0x118
    ScePspFMatrix3 f0x120;       // +0x120  (3x3, 36B)
    Joint *parent, *sibling, *child;  // +0x144 / +0x148 / +0x14C  (tree links)
    bind_pose bind;              // +0x150  (scale @+0x190 — Joint::update reads this)
    bind_pose alt_bind;          // +0x1D0
};
struct Hierarchy {           // the SKELETON; virtual
    u8   unknown_0x4[0x10C];     // +0x04
    Joint *roots[4];             // +0x110  (up to 4 root chains)
    u16  root_count;             // +0x120
    u16  chain_count;            // +0x122
    u32  joint_count;            // +0x124
    u8   unknown_0x128[4];       // +0x128
    u32 *motion_table;           // +0x12C  <-- the animation/keyframe source
    u16  unknown_0x130[4];       // +0x130
    u16  unknown_0x138[4];       // +0x138
};
struct ModelBase : Draw {        // owns the renderable: transform, pmo, tmh, hierarchy
    ScePspFMatrix4 transform; pmo model_pmo; tmh model_tmh; Hierarchy hierarchy; ...
};
```

### Key EU function addresses (JP+8, code-region)

| Function | EU VA | Role |
|----------|-------|------|
| `Joint::update(Matrix4* parent, Matrix4* out, f,f,f)` | `0x08860328` | compose bone global from parent×local, scaled by xyz = `bind.scale` |
| `Joint::func(Joint*, u32 key)` (tree walk) | `0x0885F928` | find joint by `key` (+0x114); `-1`/`0xFFFF` = empty |
| `Joint::func_eboot_0885FFB4(Vector4*, int, f, f)` | `0x0885FFBC` | keyframe→transform sampler (candidate) |
| `pmo::compile(void*, pmo_header*, pmo_mesh_data*)` | `0x088623DC` | build renderable from PMO |
| `pmo::draw(Hierarchy*, tmh*, Matrix4*)` | `0x08861694` | rigid skinned draw (per-mesh bone) |
| `pmo::drawWeight(Hierarchy*, tmh*, Matrix4*)` | `0x088646F0` | blended skinned draw |
| `pmo::drawMesh / drawWeightMesh` | `0x0886171C` / `0x0886477C` | per-mesh variants |
| `ModelBase::compile_pmo / compile_tmh` | `0x08862510` / `0x088626D0` | model load |
| `world_matrix(Vec3*,Vec3*,Vec3*,int,Matrix4*)` | `0x08861E9C` | build matrix from pos/rot/scale |
| `func_eboot_088641B8(Hierarchy*)` | `0x088641C0` | Hierarchy setup (decomp `extern`) |

### What this changes

* The **bind-pose is a known structure** (`bind_pose`: a 4×4 matrix PLUS decomposed
  scale/rotation/position vec3s), stored **per `Joint`**, in a `Hierarchy` of up to 4
  root chains. It was never a mystery format — it's runtime engine state.
* Monster PMOs carry **zero bone data** (verified: 90/90 monster PMOs have
  `bone_data_offset == material_data_offset`, i.e. empty — see `docs/PMO_MODEL_FORMAT.md`).
  The skeleton is a **separate PAC sub-resource**, not part of the PMO.
* **RESOLVED below:** the big-monster skeleton + bind-pose IS on disk — PAC
  sub-resource 0, a `0xC0000000` blob — and `Joint` trees are built from it at load.
  See "✅ SKELETON + BIND-POSE SOLVED". (`Hierarchy.motion_table` points at the
  keyframe stream, PAC sub-resource 3.)

---

## (historical) Status before 2026-06-13: UNDOCUMENTED (Critical Blocker)

The animation/skeleton format was the #1 blocker for monster model export with full rigging. The findings below predate the skeleton-class decode above.

### ✅ KEYFRAME STREAM SOLVED — big-monster animation (2026-06-13)

Big-monster animation = **PAC sub-resource 3**, a P3rd-style animation pack. Parser:
**`tools/anim.py`** (validated on Tigrex: 22 animations, bone counts match the
skeleton, all size-chains exact). The engine interpolates with the cubic `spline()`
(ease-in/out tangents, decompiled in `model_base.cpp`).

```
Container header 0x18:  u32 magic(0x64) ; u32 header_size(0x18) ; u32 slot_count ;
                        u32 ? ; u32 ? ; u32 first_offset
Offset table @+0x14:    slot_count × u32 — offset to an anim block, or 0xFFFFFFFF = empty.
```

Every level is a section `{ u32 (0x80000000 | tag) ; u32 count ; u32 size }`; `size`
includes the 12-byte header and chains exactly to the next sibling:

```
Animation block:  count = bone_count ; +0x0C u32 loop ; +0x10 f32 loop_start ;
                  header 0x14, then `bone_count` bone records (1 per skeleton bone, in order).
Bone record:      tag = channel bitmask (rotX/Y/Z=0x08/10/20, locX/Y/Z=0x40/80/100,
                  sclX/Y/Z=0x200/400/800) ; count = #channels. Empty bone = 12B header only.
Channel record:   tag = channel type ; count = #keyframes ; then the keyframes.
Keyframe (8B):    s16 value ; s16 frame ; s16 ease_in ; s16 ease_out.
```

Quantization (P3rd sibling): **rotation 4096 = 90°**, location 16 = 1.0, scale 256 = 1.0.

Verified on Tigrex (`file_06134`) anim[0]: 24 bone records (= the skeleton's 24 bones),
bone 2 (root) = rot+loc (mask 0x1F8, 6 channels), bones 3–23 = rot XYZ (mask 0x38);
a sample rotation channel runs frames 0→39→77→113→150 with values ≈ −27° (sane), ease
tangents present. ⇒ 1:1 anim↔skeleton bone mapping; the pack holds up to 100 animation
slots (22 used on Tigrex), each an action (idle / walk / roar / …).

### ✅ MHP3rd SOURCE anim (`parse_p3rd`) + cross-game port (2026-06-21/22)

The MHP3rd in-quest moveset is the **same recursive data** as the MHFU `0x64` pack but with
**compact `u16` bone/channel headers** (cross-checked byte-for-byte against
AsteriskAmpersand/Kurogami2134 `p3rd_monster_anim.bt`). Parser:
**`mhfu_model.anim.parse_p3rd`** (was a stub returning `tracks=[]` — that's why no conversion
existed before; now fully decoded, 16 tests):
```
BLOCK   : u32 bone_count ; u32 block_size ; u32 loop ; u32 pad
BONE    : u16 num_channels ; u16 record_size
CHANNEL : u16 channel_bit (SAME bits: 0x40=locX …) ; u16 kf_count ; u32 chan_size(=8+8*kf)
KEYFRAME: <4h> value, frame, ease_in, ease_out   (IDENTICAL to MHFU 0x64)
```
Container header is **variable-size**: word1 = `header_size`; the LAST header word (at
`header_size-4`) = `first_anim`; the slot table is at **`header_size+4`** with length
`(first_anim - header_size - 4)/4` (NOT word0/word2 — that was the old decode-0-anims bug;
`header_size` is 0x18 for small monsters, 0x20 for big). Same quantization (rot 4096=90°,
loc /16, scl /256 — `shared.py`). Real in-quest movesets: **`file_03997`–`file_04016`** (small/
medium monsters) and the **raw `.anim`** big monsters **`file_05142`–`file_05424`** (42-48
bones). The authentic Brute moveset = **`file_05250`** (77 clips). Per-monster anim→skeleton
bone maps (`bone_offset`/`missing_bones`) are in the upstream `skipped_bones.md`.

**Cross-game port → MHFU 0x64 3-stream** (`anim_ingame.swap_anim_to_realmotion`,
`from_flat_anim`): `bone_match.match_skeletons` builds the source→host joint correspondence
(by bind-world position); each source track is re-emitted on the host joint it drives,
re-sorted to native channel order, **SCALE channels DROPPED** (the engine's bit→ordinal table
`0x089A5C44` only maps rot+loc; scale → OOB crash), padded/partitioned to the host count
(Tigrex = 45, split 31/9/5). Cross-rig fixes (2026-06-22): unmatched host joints →
`rest_bone` (identity rot + bind pos, NOT `empty_bone` which zeroes the matrix → collapse);
a host chain LONGER than the source (Tigrex tail 5 vs Brute 4) uses `bone_match.fill_unmatched`
+ skinning `exclude=` so the extra joint rests without kinking (a parent+child sharing one
source compounds rotation → tail whip). Driven end-to-end by `port_p3rd.port_monster`
(see `docs/PMO_MODEL_FORMAT.md`).

**Cross-rig fix (2026-06-24) — leading root-chain alignment (`bone_match._fix_leading_root_chain`).**
The position matcher is greedy nearest-by-bind-world; it **fails on the collapsed structural root
chain** — the leading run of bones all at the origin (zero-length structural joints). The MHFU
Tigrex host has **3** origin bones, the MHP3rd Brute source **2**, so greedy paired host0↔src0,
host1↔src1 and left **host joint 2 (the HIP) UNMATCHED**. The hip carries the body's vertical
positioning `locY` (≈4809 on the Brute) — undriven, the mesh renders ~a lower-body-height below the
(correctly-grounded) entity origin and the monster looks **sunk into the floor** (this was long
misdiagnosed as a "terrain-registration gap" — it is NOT; the engine grounds the entity correctly,
memory `brute-terrain-sink-re`). FIX = a post-pass in `match_skeletons` that detects the leading
origin run in each skeleton (`Lh`, `Ls`) and re-aligns them **from the TAIL** (host[Lh-1]↔src[Ls-1],
…), leaving surplus LEADING host bones as placeholders (None) — exactly the native layout's leading
empty joints. No-op when the chains are equal length (safe for equal-root / same-rig pairs).
Result on the Brute: `host2(hip) ← src1`, branch matches unchanged (avg bind-dist 14.3), all 26
model tests pass, in-game = stands on his feet.

**This closes animation export.** Full static pipeline now available:
geometry (`pmo.py`) + skeleton & bind-pose (`skeleton.py`) + animation (`anim.py`) +
implicit mesh↔bone mapping → everything Blender needs for rigged monster import/export.

### Runtime skeleton build — static trace (2026-06-13)

Followed the build path statically in `BOOT.BIN` (`tools/eboot_dis.py` + decomp source
`joint.cpp`/`model_base.cpp`). The skeleton is constructed at model-load time, NOT read
from the model file:

* **Joint-tree builder** = EU `0x0886789C` (in `obj_manager`, the em/player object
  manager). Signature `builder(Hierarchy* hier, void* skel_src, Joint* joint_buf,
  float sx, sy, sz)`. Called from 5 model-type setup sites (`0x08867804`, `c60`, `e2c`,
  `0x08868138`, `3ec`) — one per model class (monster / player body / armor / …). Each
  site: `compile_pmo` → **builder** → `func_eboot_088641B8(hier)` (the per-frame "update
  all roots" driver: loops `hier->root_count` @+0x120, calls `Joint`-FK on each
  `hier->roots[i]` @+0x110).
* The builder **allocates `joint_count` Joints of stride `0x250`** (confirms `sizeof
  Joint`), sets each Joint's vtable to **`0x089BAB08`**, zeroes the tree links
  (`+0x144` parent / `+0x148` sibling / `+0x14C` child) and keyframe arrays
  (`+0x1B4` `bind.f0x64` / `+0x234` `alt_bind.f0x64`), writes `hier->joint_count`
  (`+0x124`) and `hier->chain_count` (`+0x122`).
* **`skel_src` record format** (per bone, walked by the builder; `func_eboot_08860054`
  fills each `Joint.bind` from it):

  | Off | Field |
  |-----|-------|
  | +0x00 | flags (high bit `0x80000000` toggles the joint count) |
  | +0x04 | joint count (header record) |
  | +0x08 | **record size** (variable stride → `src += [src+8]`) |
  | +0x0C | bind-transform data (→ `func_eboot_08860054` → `Joint.bind.transform`) |
  | +0x10 | parent joint **index** (−1 = none; → `joint_buf + idx*0x250`) |
  | +0x14 | child joint index (−1 = none) |
  | +0x18 | sibling joint index (−1 = none) |
  | +0x50 | chain / root id (maxed into `hier->chain_count`) |

  Tree links are stored as **indices** into the joint array (resolved to pointers at
  build) — so the on-disk/in-RAM skeleton is an index-linked bone list with
  variable-length records, each carrying its own bind transform.
* The monster's `skel_src` pointer (`a1`) is passed *into* the setup function from the
  em-object spawn; `joint_buf` is freshly allocated (`jal 0x8859b44`, size
  `joint_count*0x250`); the scale comes from `model+0x60/0x64/0x68`; the `Hierarchy` is
  embedded at `model+0x80`.

### Monsters DO have a Joint skeleton — proven (2026-06-13)

The `0x0886789C` builder above turned out to be the **player/equipment** path (5 vtable
setup methods; its `skel_src` is PAC resource index 1 — but a monster PAC's sub-file 1
is the TMH, and monster PMO `bone_data` is empty, so that path is not the monster's).
The **monster path is separate** and was proven by scanning the Tigrex overlay
(`file_06108`, em75) for `jal`s into the EBOOT model code:

* The overlay **drives** a skeleton every frame — it calls `pmo::drawWeightMesh`
  (`0x0886477C`), `world_matrix` (`0x08861E9C`), the per-`Joint` FK op (`0x08860648`),
  `ObjBase::testAnimation` (`0x08865CB8`), and the per-frame draw funcs
  (`0x08864348` ×280). ⇒ **monsters are bone-animated via the same `Joint`/`Hierarchy`
  system.** (The earlier "rigid-skinned" finding is about vertex→bone *weights* — there
  are none, binding is per-mesh — NOT about the absence of bones. The bones exist and
  animate.)
* The overlay does **not** build the skeleton (no `Joint::new` / builder / `pmo::compile`
  calls) — it only drives an already-built one. It reaches into the model-loader module
  (`0x088dcebc`, `0x088de060`).

**Monster skeleton builder = EU `0x088dc40c`** (in the em/character model-loader module,
the *second* `Joint::operator new` caller). `builder(Hierarchy* hier, Joint* joint_buf,
void* skel_src, float sx,sy,sz)`:
* reads `joint_count` via `0x088dc748(skel_src)` → `hier->joint_count` (+0x124);
* allocates `joint_count` Joints @stride `0x250`; per-joint init via `0x088dc720`.
* `skel_src` header is **identical** to the player path: `flags @+0x00` (bit
  `0x80000000` adjusts the count), `count @+0x04`, then the variable-stride per-bone
  records documented above.
* Called once at em-spawn from `0x088dc38c`, where `skel_src = <resource-accessor
  0x088b89b0>(resource_array, 0)` (a registered resource, **index 0** of the em model's
  resource set — distinct from the player PAC layout). The Joint buffer is allocated
  from the ObjManager arena (`[0x08A62C5C] + 0x80000`); scale from `model+0x60/64/68`;
  the `Hierarchy` is embedded at `model+0x80`.

### ✅ SKELETON + BIND-POSE SOLVED — it's on disk (2026-06-13)

`skel_src` is **sub-resource 0 of the big-monster model PAC**, a `0xC0000000` skeleton
blob — the *same* format the iOS port uses (`m2jean/mhfu-ios-pmo-plugin`). Parser:
**`tools/skeleton.py`** (validated on Tigrex + 66 monsters).

* **File mapping:** `file_id = em_id + 0x17AB`, and the DATA.BIN extract index == file_id,
  so monster PAC = `file_0{em_id+0x17AB}.bin`. **Big monsters** (those with an `em*.ovl`
  overlay) carry a skeleton: `file_06111`–`file_06159` all have sub-0 = skeleton
  (17–61 bones). **Small monsters** (Popo/em01 = `file_06060`) do NOT — their sub-0 is
  the PMO; they ride a rigid/shared path.
* **Big-monster PAC layout:** `[0]=skeleton (0xC0000000)`, `[1]=PMO`, `[2]=TMH`,
  `[3]=animation (0x64… keyframes)`. (Small-monster PAC: `[0]=PMO, [1]=TMH, [2]=PMO2,
  [3,4]=float blobs, [5]=HITS` — no skeleton.)
* **Skeleton blob format** (matches engine builder `0x088dc40c` + iOS):
  ```
  Header 0x1C:  u32 magic 0xC0000000 ; u32 bone_count ; u32 total_size ; u32 ×4
  per bone (section, size from +0x08, = 0x10C on Tigrex):
    +0x00 u32 section_magic 0x40000001
    +0x04 u32 flag (1)
    +0x08 u32 section_size
    +0x0C s32 index
    +0x10 s32 parent  (-1 = none)     +0x14 s32 left_child   +0x18 s32 right_sibling
    +0x1C 3f  bind scale     (+1.0 pad)
    +0x2C 3f  bind rotation  (euler; +1.0 pad)
    +0x3C 3f  bind position  (offset from parent; +1.0 pad)
    … remainder zero/aux within the 0x10C section
  ```
  Verified: Tigrex (em75, `file_06134`) = 25 bones, single root (bone 0), coherent tree
  (spine 0→1→2→3; bone 3 = limb/head/tail hub; symmetric left/right limbs with mirrored
  ±X positions; tail chain 21→22→23). The engine builds one `Joint` (0x250) per bone,
  links parent/child/sibling by index, stores scale/rotation/position into `Joint.bind`,
  then `Joint::update` runs FK from these.

**This closes the bind-pose blocker.** Full rigged-export inputs now available statically:
geometry (`pmo.py`) + skeleton & bind-pose (`skeleton.py`) + implicit mesh↔bone mapping.
The only remaining piece for *animation* export is decoding PAC sub-resource **3** (the
`0x64…` keyframe stream) against the `spline()` interpolator / P3rd keyframe shape —
keyframes, not the skeleton.

---

**`skel_src` container traced to DataManager (2026-06-13).** The setup function
(`0x088dc1f0`) reads its source container from a **DataManager entries slot**:
`buffer = entries[*].buffer` where the entries array base is the global `[0x09A4F0D0]`
(EU) and the slot is taken at offset `+0x60`, guarded by the entry's loaded bit
(`flags & 2`). Then:

* `skel_src = 0x088b89b0(buffer, 0)` — **sub-resource 0** of that container;
* `model/pmo = 0x088b89b0(buffer, 1)` — sub-resource 1 (fed to `compile_pmo`, mesh
  count at `+0x1c`).

So this container's layout is **{[0] = skeleton, [1] = model}** — the *opposite* order
from a monster *model* PAC (`[0]=PMO`), i.e. `skel_src` is NOT in the model PAC; it
lives in a **separate DataManager-loaded file**. `0x088b89b0(buf, i)` just indexes that
file's `count + (offset,size)…` sub-table (same shape as a PAC) and returns
`&entry[i]` when its size word is non-zero.

**The one remaining link (last mile):** identify which `file_id` is loaded into that
DataManager slot (`DataManager::load(slot, file_id, size)`) for a given monster — that
file's sub-resource 0 is the skeleton blob. Then decode the blob against the per-bone
record table above (`flags@0, count@4, recsize@8, bind-data@0xC, parent/child/sibling
idx@0x10/14/18, chain@0x50`) → a fully static monster bind-pose + skeleton export.
Everything up to the file_id is mapped; the file_id↔slot binding is the open piece
(continue the backtrace from `0x088dc1f0`'s callers, or read the live DataManager
`entries` to see which file sits in the slot). The format itself is no longer unknown.

## Reference: decoded sibling-engine format (MHP3rd) — 2026-06-13

`Kurogami2134/blender_p3rd_anim` (external) is a Blender **import+export** addon for
**Monster Hunter Portable 3rd** *monster* animations — the direct successor engine to
MHP2G/MHFU. It fully decodes a per-bone / per-channel keyframe format that is almost
certainly close to MHFU's (same engine family). Use it as the template when decoding
MHFU's `Prog` payload.

**Per-animation layout (P3rd):**
```
Header 0x10:  3if = u32 bone_count, u32 size, u32 loop(0/1), f32 loop_start
per bone (BoneAnimation):
    u16 transform_count, u16 size
    per transform:
        u16 type (bitflag), u16 keyframe_count, u32 size
        KeyFrame[] : 4×s16 = s16 value, u16 frame, s16 ease_in, s16 ease_out  (8B each)
empty bone = (u16 0, u16 4)
```
**Transform type bitflags:** rot X/Y/Z = `0x08/0x10/0x20`, loc X/Y/Z = `0x40/0x80/0x100`,
scale X/Y/Z = `0x200/0x400/0x800`.

**Value quantization (decode math):**
- rotation: `4096 units = 90°` → `radians = raw * radians(90/4096)`
- location: `16 units = 1.0`
- scale: `256 units = 1.0`

**Animation-pack container (P3rd):** `u32 ?`, `u32 header_size`@0x04; header = `header_size/4`
ints; anim count = `(header[-1] - header_size - 4) / 4`; offset table at `header_size+4`
(4B entries), **`-1` = empty slot** → seek to that anim. (See the `Head`/`Prog` note below
— MHFU's wrapper uses the same `0xFFFFFFFF` empty-slot convention.)

## Reference: external tooling (2026-06-13)

| Tool | Game | Covers | Note |
|------|------|--------|------|
| `Kurogami2134/blender_p3rd_anim` | MHP3rd | monster anim import+export | keyframe format above; sibling engine |
| `m2jean/mhfu-ios-pmo-plugin` | MHFU **iOS** | PMO + **skeleton** + anim (Noesis) | iOS port (PMO v2.0); blueprint for skeleton node-tree |
| `svanheulen/mhff` | MH PSP | PMO/TMH/PAC parse | vendored in `tools/mhff/` |
| `replydev/mhfu-hd-retexture-eu` | MHFU **EU PSP** | texture replacement | proves TMH swap on our exact target |

`skipped_bones.md` in the P3rd repo lists, per monster id, the skeleton bones with **no
geometry** — this is exactly the skip list that makes MHFU's implicit mesh↔bone mapping
work (see `docs/PMO_MODEL_FORMAT.md`; em01: 31 meshes + skipped {8,15,25} = 34 bones).

## What We Know

### Animation-Related Files

| File Type | Magic | Location | Purpose |
|-----------|-------|----------|---------|
| Motion Tables | `Head `/`Prog` | motion/*.bin | Animation lookup/data |
| AHI Files | None (null start) | emmodel/em32/ | Unknown (animation/hitbox?) |
| ~~Unknown~~ | ~~PAC index 4~~ | emmodel/*.pac | ~~bone indices~~ — **disproven 2026-06-13: bounding/hitbox floats** (see PMO doc) |

### Motion Table Files (513 total)

**Location**: Various indices, pattern `motion/*_tbl.bin`

**Known files**:
- `motion/plcom_tbl.bin` (index 61) - Player common animations
- `motion/w00_tbl.bin` to `w10_tbl.bin` (3377-3387) - Weapon animations
- `motion/em04_tbl.bin` (6323) - Monster em04 animations
- `motion/em10_tbl.bin` (6324) - Monster em10 animations

**IMPORTANT (refined 2026-06-13)**: only 2 *loose* `em*_tbl.bin` motion files exist
(em04, em10) — and both are dead ends for keyframes (em04's `Prog` registry is empty;
em10 is opaque-packed; see the decoded section above). The real monster animation
lives **inside each big-monster model PAC as sub-resource 3** (`0x64…` keyframe stream),
loaded alongside the skeleton (sub-0) and PMO (sub-1). So "most monsters share/overlay/
runtime anims" is superseded: big monsters each ship their own keyframes in their PAC.

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

### DECODED 2026-06-13 — and the wall it hit

Parser: `tools/motion.py` (decodes the wrapper + em04 joint table; reports
em10 as opaque). Findings against the two on-disk monster motion tables:

**em04_tbl (file_06323, 2048 B):** valid `Head`/`Prog` wrapper —
```
Head sections=2  declared_size=0x770
Prog @0x20  size=0x360  anim_slots=63
```
…but the `Prog` **animation offset table is 100% empty** — all 63 slots are
`0xFFFFFFFF`. **Zero P3rd-shaped keyframe animations are registered on disk.** The
only payload is a trailing **per-joint parameter table**: 41 × 14-byte records,
anchor = `u16 0xFF00`, layout `{sep u16, joint-id u16 (doubled byte, 60…), c1 u16=200,
c2 u16=200, scale-hi u16 (upper half of an f32 ≈ 3.4–4.0), 0 u16, seq u16}` — bone
scale/length-ish constants, **not keyframes**. A second undecoded section follows
`[0x380, 0x580)`.

**em10_tbl (file_06324, 133 KB):** **no `Head`/`Prog` magic at all** — a distinct
packed/high-entropy container (`u32 count = 54 @0x10`, raw stream from `0x18`, *not*
length-prefixed). Does not match the P3rd struct.

**⇒ Wall:** the P3rd per-bone/9-channel keyframe struct does **not** map onto either
on-disk monster motion table. There is no populated P3rd-shaped keyframe payload to
decode here. This corroborates the standing finding that monster **skeletal
animation is overlay-embedded / runtime**, not file-resident — the same class of
blocker as the skeleton bind-pose. Decoding real monster keyframes needs MIPS disasm
of the overlay anim loader or live PPSSPP RE, not static file parsing.

(The `0xFFFFFFFF` empty-slot convention in the `Prog` table does match the P3rd
animation-pack container — so the *wrapper* is the same engine family; only the
inner payload was never populated for em04 on disk.)

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

## Status of each piece (2026-06-13)

| Piece | State | Where |
|-------|-------|-------|
| Skeleton / bone hierarchy | **SOLVED** | big-mon PAC sub-resource 0, `0xC0000000` blob — `tools/skeleton.py` |
| Bind-pose (per-bone scale/rot/pos + tree) | **SOLVED** | same blob (bone section `+0x1C/2C/3C`) |
| Mesh↔bone binding | **SOLVED** | implicit positional (see `docs/PMO_MODEL_FORMAT.md`) |
| Runtime skeleton classes + FK | **SOLVED** | `Joint`/`Hierarchy`, `Joint::update`, builder `0x088dc40c` (above) |
| Keyframe interpolation method | **KNOWN** | cubic `spline()` w/ ease tangents (decomp `model_base.cpp`) |
| Keyframe stream encoding | **SOLVED** | big-mon PAC **sub-resource 3** — `tools/anim.py` (see "✅ KEYFRAME STREAM SOLVED") |
| em04/em10 loose motion tables | dead end | `tools/motion.py` (em04 registry empty, em10 opaque) |

The `em32.ahi` (Rajang) and `Head`/`Prog` notes below are retained as historical
reference; the live monster-animation source is the per-PAC sub-resource 3, not these.

## ⚠️ MHFU in-game (0x38) anim vs lobby (0x18) — RE'd 2026-06-19 (Brute port)

`tools/anim.py`'s model (pack header `0x18`, slot table @`hsize-4`, bone records
`{mask,nch,bsz}`, block header `0x14`) is the **MHP3rd / lobby** form. The **in-game**
anim the engine actually plays (native Tigrex `file_06185` sub-3) is a DIFFERENT,
RECURSIVE 3-stream form — decoded live via the per-frame interpolator chain
`0x0885fa0c → 08863198 → 088630d0 → 08863668`. Critical for any cross-game port.

- **Pack header = `0x38`** (not `0x18`): `magic 0x64, hsize 0x38`, then **five
  `(0x64, suboffset)` pairs** @`+0x08..+0x2F`, `u32 0` @`+0x30`, then the **main
  100-slot table @`0x34`**. The 5 sub-offsets point to **five contiguous 100-entry
  u32 sub-tables** (`0x1C8/0x358/0x4E8/0x678/0x808`, each `0x190`, ending at the
  first anim `0x998`). Empty entries/tables = `0xFFFFFFFF`.
- **THREE parallel streams** populate three tables — main(@`0x34`), sub1(@`0x358`),
  sub3(@`0x678`) — that **partition the skeleton's bones** (native Tigrex main block
  `bc=31`, sub1 `bc=9`, sub3 `bc=5`; 31+9+5 ≈ bone count). Each animation = THREE
  blocks (one/stream); tables 0/2/4 stay empty. Block tags carry `0x80000000`.
- **Blocks are RECURSIVE sections** `{0x80000000|tag, u32 count, u32 size}` down to
  keyframes (top anim block has extra `loop@+0xC`/`loop_start@+0x10`). The per-frame
  interpolator `0x08863668` reads each keyframe section's FRAME-TIME `lh [sect+0xE]`,
  compares to the current frame `f12`, and `[sect+4]` as a count.
- **The per-frame tick requires the anim and skeleton to describe the SAME bones.**
  Proven: unmodified native Tigrex anim + a Brute 46-bone skeleton crashes the
  per-frame walker identically (`0x088636ac`, wild read) — the per-bone traversal
  lands on a `loop_start` float used as an index. A ported monster's anim MUST be
  authored in this format matching its OWN skeleton; you cannot scaffold with
  another species' anim.

**Implication:** a real cross-game anim port needs a **recursive in-game encoder**
(nested `{0x80000000|tag,count,size}` sections + the 3 stream tables + 0x38 header),
not `anim.py`'s flat form. `anim.py`'s encoder is correct only for byte-identical
RESHAPE of an existing in-game pack, not for synthesis.

### ✅ in-game encoder BUILT — `tools/mhfu_model/anim_ingame.py` (2026-06-19)

`anim_ingame.py` is that recursive encoder: `parse_ingame`/`encode_ingame` round-trip
native `file_06185` sub[3] BYTE-EXACT (1008288 B); `from_flat_anim` converts a flat
(lobby/MHP3rd) pack → the 3-stream in-game form; `make_static_pose`/`rest_bone` build
bind/rest poses. Tests: `tools/mhfu_model/tests/test_anim_ingame.py` (5 pass). Wired into
the Blender addon (`blender_mhfu/exporter.export_ingame_bindpose_pac` + operator
`EXPORT_OT_mhfu_monster_ingame`).

**Two hard engine rules, both PROVEN LIVE (Brute port, see `docs/BRUTE_TIGREX_PORT.md`):**
1. **NO scale channels.** The per-frame FK (`0x08863198`) reads each channel's ctype
   low-u16 as a bit and indexes table `0x089A5C44`, which maps ONLY rotation
   (0x08/0x10/0x20 → 3/4/5) + location (0x40/0x80/0x100 → 6/7/8). Scale bits
   (0x200/0x400/0x800) index OOB → garbage joint ptr → crash (`Write @0x0D8C59B0, PC
   0x08863250`). Native Tigrex anims never carry scale; `from_flat_anim` drops bits ≥0x200.
2. **The bone partition must match the HOST**, not the injected skeleton. When hosting on
   the Tigrex slot the engine iterates `entity+0x1a4` = **45** bones (split 31/9/5); a
   42-bone anim runs the joint walk off the end → junk keyframe ptr → crash (`Read
   @f3e9dc32, PC 0x088630d0`, the keyframe interpolator).
3. A bind/static pose with EMPTY bone sections COLLAPSES the mesh (joints not computed) —
   every bone needs real keyframes; skeleton `bind_rot` is all-zeros (rotation is anim-only).

Full debugging arc + key addresses: `docs/BRUTE_TIGREX_PORT.md`.

## References

- Skeleton (iOS, same format): `m2jean/mhfu-ios-pmo-plugin`
- Keyframe shape (sibling engine): `Kurogami2134/blender_p3rd_anim`
- Engine source (decompiled): `tools/mhfu_external/mhp2g-decomp` (`joint.cpp`, `model_base.cpp`)
- Disasm harness: `tools/eboot_dis.py`; skeleton parser: `tools/skeleton.py`
