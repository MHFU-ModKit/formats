# MHP3rd File Map — T1 findings (extraction + monster packaging)

Branch `mhp3rd-monster-port`. Produced by orchestrator pass 2026-06-18. This is the
**starting map** for the asset-pipeline agents — it has confirmed facts AND open questions
flagged `[OPEN]`. Resolve the OPENs as job #1 of the asset track.

## Extraction (DONE — reproducible)

```
# ISO already extracted:
workspace/extracted_mhp3/PSP_GAME/USRDIR/DATA.BIN        # encrypted, 1.09 GB
workspace/extracted_mhp3/DATA_decrypted.BIN              # decrypted
workspace/extracted_mhp3/data_files/file_NNNNN.bin       # 5954 extracted files

# Re-run (venv active):
PYTHONPATH=tools/mhef:tools python -c "import mhef.psp,extract_iso; \
  mhef.psp.DataCipher(mhef.psp.MHP3_JP).decrypt_file(\
  'workspace/extracted_mhp3/PSP_GAME/USRDIR/DATA.BIN','workspace/extracted_mhp3/DATA_decrypted.BIN'); \
  extract_iso.extract_data_bin('workspace/extracted_mhp3/DATA_decrypted.BIN','workspace/extracted_mhp3/data_files/')"
```
Key API delta vs MHFU: MHP3rd DATA.BIN is **LBA-keyed** → use `DataCipher.decrypt_file()`
(NOT `decrypt(buff)` — that needs an `lba` per block). `DataCipher.MHP3` attr does NOT
exist; use the module constant `mhef.psp.MHP3_JP` (=6).

## PAC container (same family as MHFU)

`u32 count` + `count×(u32 off,u32 size)` table + data. Scanner: `tools/mhp3rd/scan_monster_pacs.py`
(`<data_dir>` for histogram, `--detail <file>` for one PAC's sub layout).

## Format deltas MHP3rd vs MHFU (CONFIRMED)

| Resource | MHFU (gen-2) | MHP3rd (gen-3) |
|---|---|---|
| PMO geometry | magic `pmo\0` ver `1.0\0` | magic `pmo\0` ver **`102\0`** (per-mesh scale, diff normals) |
| Skeleton | sub-0 magic **`0xC0000000`**, bone_count@+4 | magic **`0x80000000`**, bone_count@+4 (same blob family, diff top-bit) |
| Texture | `.TMH0.14` | `.TMH0.14` (same) |
| Animation | sub-3, magic `0x64`/hdr `0x18` | **NOT in the model PAC** `[OPEN]` — no `0x64` magic anywhere; gen-3 relocates/reformats anim |
| Container | `[skel,pmo,tmh,anim]` 4-sub | **multi-sub (12–13)** w/ gen-3 FourCC tags `NSP\0`(0x0050534e) `ASB\0` `ARV\0`, **dual PMO + dual TMH** |

## Monster model PACs (located)

The 16 high-bone-count PACs (`bones>30`, FourCC-tagged) are the monster models — two
mirrored groups (likely LO/HI or two villages' display set):

```
group 1: file_04868(73b) 04870(82b) 04872(67b) 04880(86b) 04898(104b) 04900(88b)
group 2: file_05032(73b) 05034(82b) 05036(67b) 05044(74b) 05062(108b) 05064(91b)
extra:   file_05094(124b) 05106(36b) 05297(47b) 05412(47b)
```
The 22-bone files (e.g. `file_00107` 371 KB PMO) are PLAYER/armor rigs, NOT monsters.

### `[RESOLVED]` Geometry location (OPEN-1)
Geometry is in a **companion file**: `file_NNNN.bin` = PAC (tables + skeleton + TMH),
`file_NNNN+1.bin` = raw GE display list (starts with 0x14000000 ORIGIN_ADDR command).
The PMO header field `ge_base` (vals[12] of `struct.unpack_from('<I4f2H8I', blob, 8)`)
equals `len(pmo_blob)` for companion-file PACs → redirect GE reads to `geo_blob`.
Lobby-style PACs (e.g. file_05248 sub[5]) have `ge_base < len(blob)` = self-contained.
Confirmed: file_04898 (104 bones, companion=file_04899): 95 groups, 34701 verts, 24901 faces.
Parser: `tools/mhfu_model/pmo_p3rd.py::parse(blob, geo_blob=None)`. Tests: 9/9 pass.

### `[RESOLVED]` Identify port target (OPEN-2)
**Ground truth from user (domain expert) — overrides all prior heuristic labels:**
- **`file_05248` = BRUTE TIGREX** ← PORT TARGET
- **`file_05229` = DIABLOS** (was incorrectly labeled "Black Tigrex em023" by color heuristic)
- Prior em058/em023 labels for these files were WRONG; texture-distance and sub7 heuristics are unreliable for species identification. User visual ID is authoritative.

**Port target — confirmed by user:**
| File | Geo | Bones | Meshes | TMH RGB | Identity |
|------|-----|-------|--------|---------|----------|
| **`file_05248`** | **`file_05249`** | 46 | 88 | (152,159,154) | **BRUTE TIGREX — port target** |

Render: `tmp/brute_tigrex_candidates/target_file05248_CONFIRMED.png` — tan/grey body, red markings, 88 mesh groups, fully textured.

**Other lobby PACs identified in this session (renders in `tmp/brute_tigrex_candidates/`):**
| File | Geo | Monster | Render result |
|------|-----|---------|---------------|
| `file_05229` | `file_05230` | **Diablos** | dark-olive body — user confirmed |
| `file_05412` | `file_05413` | Unknown Tigrex-rig variant | dark black/charcoal with red accents |
| `file_05409` | `file_05410` | Unknown Tigrex-rig variant | orange/rust-striped |
| `file_05297` | `file_05298` | Unknown (NOT Tigrex) | green wyvern |

Note: sub7 species index and skeleton fingerprint heuristics produced multiple wrong labels in this session. Do not use them for species ID without user confirmation.

### `[RESOLVED]` Animation location (OPEN-3)
MHP3rd monster animation is in the **PAC sub[3]** (in-quest PACs like file_04016/04900),
NOT in a separate em/animation/emNNN.bin file (file_05413 turned out to be a GE companion
geometry list, not an animation pack). The `anim.parse_p3rd` parser is DONE (Task 5).

- Tigrex (em058, file_04900) sub[3]: `anim_count=87` (magic), `slot_count=60`, 10+ valid slots.
- Black Tigrex (em023, file_04898) sub[3]: similar layout.
- file_05413 = GE display list companion (0x14000000 GE opcodes), NOT animation.
- Parser: `tools/mhfu_model/anim.py::parse_p3rd(blob) -> AnimationPack`. Tests: 16/16.
- Full keyframe decode (within each slot block) is v2 — block layout differs from MHFU's P3rd pack.

## Skeleton format (0x80000000) — confirmed details

Same bone-section layout as MHFU 0xC0000000 (stride 0x5C=92, fields at identical offsets).
Differences vs MHFU:
- Header: may have **extra 4-byte word at +0x1C** (lobby PACs); probe both 0x1C and 0x20
  for the first 0x40000001/2 section magic to find real start.
- Section magic: both `0x40000001` and **`0x40000002`** appear (in-quest PACs alternate freely).
- Bone count in header may be off-by-1 if last section is truncated.

`tools/mhfu_model/skeleton_p3rd.py::parse(blob)` handles all variants; returns same `Skeleton` dataclass.

## Hitzone / part data (Task 6) — confirmed location

**Verdict: MHP3rd hitzone RESISTANCE values are NOT in the per-monster PAC.**
They live in a separate game data table (same pattern as MHFU). The PAC carries
geometry / physics / AI-hint data, not the hit-resistance numbers themselves.

For the Brute Tigrex / Tigrex port, use MHFU's existing Tigrex damage tables —
no conversion needed (the hosted model rides MHFU Tigrex's combat rules).

### Sub roles decoded (file_04900 = likely Tigrex, 88 bones)

| Sub | Magic / size | Contents |
|-----|-------------|----------|
| [0] | `pmo\0` v102 | Main PMO (hi-quality companion-file geometry) |
| [1] | `0x80000000` | Skeleton (88 bones, 0x5C/bone sections) |
| [2] | `0x57`=87 u32, 1652B | **Part table** — count = bone_count − 1; likely bone→part-ID mapping + some per-part flags; stride ~19B; NOT resistances |
| [3] | `.TMH0.14` | Main texture package |
| [4] | `NSP\0` ver 325, 200B | **Node Spring Physics** — f32 spring/damp params + 3×3 matrix (cloth/tail simulation) |
| [5] | `ASB\0` ver 330, 80B | **Attack/Shield Boundary** — bounding center (3246, −6506, −3740), 2 u32 counts, then u8 values (0x0C=12, 0x4B=75, 0x4B=75); the 75s are likely part-break thresholds or attack multipliers, NOT standard resistances |
| [6] | `ARV\0` ver 321, 16B | **Attack Rate Variation** — empty (all zeros); subspecies variant flag |
| [7] | 2B blob | Tiny flags blob (`01 05`) |
| [8] | `0x00000102`, 4096B | **CLUT / palette** — indexed-texture look-up table (u16 pairs `0x4E20` = 20000, repeating = palette entries) |
| [9] | `pmo\0` v102 | LOD / small PMO |
| [10] | `.TMH0.14` | LOD texture |
| [11] | `0x00000003`, 5792B | **Hitbox geometry** — sub-offset table (9 blobs): f32 radii, spring constants, collision sphere centers; NOT resistance values |

### Animation sub[3] format (confirmed, Task 5)
`u32 anim_count`, `u32 hsize=0x18`, `u32 slot_count`, pad; slot table at `hsize-4`.
Per slot: `u32 bone_count`, `u32 block_size`, `u32 loop_flag`. Keyframe decode = v2 (deeper RE needed).
Parser: `tools/mhfu_model/anim.py::parse_p3rd(blob)`. Tests: 16/16 pass.

## Sub-resource magics seen on a monster PAC (file_04868, reference)
```
[0] pmo  v102  | [1] skeleton 0x80000000 (73 bones) | [2] 0x00000048 (?)
[3] tmh        | [4] NSP\0 | [5] ASB\0 | [6] ARV\0 | [7] tiny(4B)
[8] 0x00000102 (4096B, palette/clut?) | [9] pmo v102 (small) | [10] tmh (small) | [11] 0x00000003 (?)
```
