# Brute Tigrex live port — integration RE & status (2026-06-21)

Branch `mhp3rd-monster-port`. Goal: port **Brute Tigrex** from MHP3rd into MHFU
(his own model + skeleton + animation), running live in a Giadrome quest.

This doc covers the **live in-game integration** (the second half of the port).
Asset conversion (extraction, PMO `102`→`1.0`, skeleton `0x80000000`→`0xC0000000`,
TMH) is in `docs/MHP3RD_FILE_MAP.md` + `tools/mhfu_model/`. The animation format
is in `docs/ANIMATION_FORMAT.md` ("MHFU in-game (0x38) anim — RE'd 2026-06-19").

## Result so far

| piece | state |
|-------|-------|
| Model (PMO 1.0) | ✅ converts + loads + renders-ready |
| Skeleton (46-bone `0xC0000000`) | ✅ converts + loads |
| Textures (TMH) | ✅ convert + load |
| **Loads into the quest** | ✅ construction completes (reached basecamp) |
| **In-game anim encoder** | ✅ built + byte-exact round-trip + 5 tests (`tools/mhfu_model/anim_ingame.py`) |
| **Blender addon emits .bin** | ✅ operator + headless test (`export_ingame_bindpose_pac`) |
| **Loads with NO crash** | ✅ v25 (2026-06-20) — past all construction + FK crashes |
| **Draw node + engage + un-cull** | ✅ when player co-located: `+0x008` built, `+0x004` skip-draw clear, `+0x5dc`=1.0 |
| **Model + bones + textures RENDER in-game** | ✅ **v29 (2026-06-20) — complete TEXTURED Brute renders live, no crash** |
| **Mesh ASSEMBLES (static bind pose)** | ✅ **v32 — model-space verts + per-group nearest-bone → recognizable assembled Brute** |
| **Bone matcher + anim bone_map + Blender export** | ✅ `tools/mhfu_model/bone_match.py` + `from_flat_anim(bone_map=)` + exporter (commit c72db28, 70 tests) |
| **Real-motion animation (coherent)** | ❌ tears under animation — the Brute mesh uses per-vertex BLEND skinning (see below) |

**The model + bones + textures RENDER live** as an assembled, recognizable, textured
Brute Tigrex (v32). The long-standing collapse/crash was NOT an anim problem — it was
the PMO **mesh-table format**: the converter emitted the **0x20 "player" layout** but
the engine's monster loader needs the **0x18 "monster" layout** (`+0x14` = a
vgroup-table index, not vertices; vg[2] = a real skeleton bone). v25/v26/v27 collapsed
(engine read count=0 → no geometry); v28 (0x18) crashed (`+0x14` carried a cumulative
*vertex* count ≤2862 → OOB vgroup read); **v29 fixed `+0x14`=(vgroup_idx<<16)|count →
renders.** Skinning then resolved for a *static* pose (v30 flat→v31 bone-local crunch→
**v32 model-space verts + nearest-bone = assembled**, after proving native verts are
model-space + bind-inverse skinning).

**The remaining wall is the ANIMATION, and the root cause is now definitive: the Brute
mesh uses TRUE per-vertex BLEND skinning** — 58/88 vgroups are multi-bone (verts in one
group weighted to *different* bones) and **30.9% of weights are fractional blends**.
MHFU native monsters are **rigid, one-bone-per-group**. v32 forced every vertex to a
single bone (slot 0) → assembles statically (at bind all bones are home) but **tears the
moment bones animate** (a vertex that should blend several moving bones rigidly follows
one → pieces separate → GE hang). The MHP3rd v102 PMO stores the bone NOT in vg[2]
(all 0) but in per-vertex weights + a per-vgroup **bone-matrix palette** set by GE
display-list bone commands. So the generalizable remaining fix = **port the per-vertex
skinning** (preserve blend weights + emit each vgroup's bone-matrix palette, mapping
source→MHFU bone via the matcher) OR **split multi-bone groups into per-bone rigid
sub-groups** (native's approach — coarser, reuses the rigid path). The bone matcher is
built and feeds either. Full arc + addresses below; detail in memory
`brute-port-ingame-anim-encoder`.

## v22→v25: crash ladder to LOAD, then the mesh-collapse wall (2026-06-20)

After the v14–v21 crashes (below), the breakthroughs that got the Brute to LOAD:
- **v22** — skeleton animated-count word (`skel+0x1C`) synced 42→45 (must equal the anim bone
  count AND the host). Also: the inject SILENTLY SKIPS without a `<BRUTE_PAC>.orig` sibling
  (`= native file_06185`) — the diff-fingerprint gate needs it; missing → 64B-prefix match →
  native header matches → no overwrite → you see the plain native Tigrex.
- **v25 — THE LOAD FIX: per-bone STREAM-ID partition `bone+0x50`.** The engine binds anim sections
  to joints sequentially in tree-walk order, only to joints whose stream-id (`joint+0x114` =
  `skeleton bone+0x50`, set at `0x08860110`) matches the target stream. Native `file_06185`
  bone+0x50 = `[0]*31+[1]*9+[2]*5+[3]*3` (streams 0/1/2/3 = 31/9/5/3, sum 48). The Brute's were
  ALL ZERO → 46 joints all claimed stream 0, but the main stream has 31 sections → overrun →
  FK crash (`0x088630d0`/`0x08863198`). v25 sets bone+0x50 to the native partition → byte-exact
  histogram {0:31,1:9,2:5,3:3} → **loads with no crash.**
- **The mesh-collapse wall (what v25 exposed):** with v25 loaded and the player co-located in his
  section, the Brute builds a draw node (`entity+0x008`=0x090BDC40, holds the live animated 4x3
  matrix at +0x0c..+0x48), is un-culled (`+0x004` skip-draw clear via gate `0x09AC4960`:
  `+0x29A`==area && `+0x638`&0x8000), and engages (`+0x5dc`=1.0). BUT his mesh renders COLLAPSED
  (shadow + a few "extensions") and drawing it hangs the GE. The per-frame big-mon anim chain is
  `0x09AC4960`→`0x09AC51A0`→**`0x088640f8`** (anim bind, `a0`=entity+0x80; ra=0x09AC51E0) — it
  fires every frame for a NATIVE Tigrex (confirmed via `catch_bp.py`) but did not fire for the
  Brute in-window (ambiguous — the GE was likely already hung). Net: the converted
  skeleton/model/anim load + construct but don't produce a valid POSED mesh.
- **Key RE correction:** the `entity+0x4C8` joint array is STATIC bind data even for the visibly
  animating native (0 changed words over 7s of roar). The animation lands in the DRAW NODE matrix,
  NOT the joint structs — every "joints static → not animating" reading was the wrong buffer.
- **GE-hang rule:** drawing a collapsed/degenerate big-mon mesh hangs the GE (ticks stop → PPSSPP
  kill). Keep the monster CULLED (render-fix off) to keep the game playable. NEVER manually clear
  skip-draw to force-draw an unposed monster.

## In-game animation: the live-debug arc (2026-06-19)

The Brute anim is the team's MHP3rd→flat anim (`tmp/brute_tigrex_port/brute_final_mhfu.pac`
sub[3], 19 clips × 43 bone tracks). `anim_ingame.from_flat_anim` converts flat → the
recursive 3-stream in-game format. Versions + what each proved:

- **v14** (3-stream bind pose, *empty* bone sections): LOADED zero-crash → the format/encoder
  is valid in-game. But the mesh **collapsed to a dot** (huge correct shadow, tiny blob): the
  engine only computes a joint matrix for bones that have keyframe channels; empty sections leave
  the matrix zeroed → rigid mesh implodes to the entity origin.
- **v15** (identity-rotation keyframes): rendered with **hitboxes working** but **underground** —
  live capture showed the per-frame anim path (`entity+0x150/0x1d0 +0x64`) was NULL → no anim
  applied → joints at origin. (Skeleton `bind_rot` is all-zeros; rotation is anim-only.)
- **v17 / v19** (real motion, 42 / 45 bone): CRASHED identically `Write @0x0D8C59B0, PC
  0x08863250`. Live crash regs: the FK joint-walker read a CHANNEL ctype `0x80120200` = bit
  **0x200 = SCALE X**; the engine's bit→ordinal table `0x089A5C44` maps ONLY rot (0x08/0x10/0x20)
  + loc (0x40/0x80/0x100) → `table[0x200]` OOB = garbage → wild write. **MHFU's in-game anim has
  NO scale channels.** Native Tigrex never carries scale; the team's flat anim does. → FIX: strip
  bits ≥0x200 on conversion.
- **v20** (42-bone, scale stripped): got PAST the scale crash → NEW crash `Read @f3e9dc32, PC
  0x088630d0` (keyframe interpolator). Cause: **bone-count mismatch** — the engine iterates the
  HOST count (main=31, `entity+0x1a4`=45=31+9+5, the Tigrex-slot overlay's count) but v20's main
  block had only 28 → ran off the end → junk bone section → junk keyframe ptr. The anim must be
  **45-bone 31/9/5 (host layout)**, not 42 (our skeleton's animated count).
- **v21** (45-bone 31/9/5 + scale stripped): got past the scale crash but STILL crashed in the
  same interpolator `0x088630d0` (read of wild ptr `0x956e1d9c`). Offline the channel bits were
  all clean (0 bad / 13800), so the desync wasn't the channel data — it was a **count mismatch
  between the skeleton and the anim**: the anim was forced to 45 bones (31/9/5) but the Brute
  **skeleton still declared 42 animated bones** (word `+0x1C`). Native is internally consistent
  (skel-animated 45 == anim 45 == host 45); v21 was not.
- **v22** (= v21 + skeleton animated-count word `+0x1C` bumped 42→45): makes skel-animated == anim
  == host == 45. One byte changed (PAC offset 0x44 = skeleton `bone_count`/animated region), size
  identical. **First v22 boot showed only the NATIVE Tigrex** — NOT a v22 result: the inject was
  SKIPPED because the `<BRUTE_PAC>.orig` content-match sibling was missing (`[inject] no .orig …
  -> 64B-prefix match` → the 64-byte header is identical to native so the gate thought the buffer
  was already done and never overwrote). After creating `brute_tigrex_v22_skel45.bin.orig`
  (= pristine native `file_06185`; first diff word at 0x44), the gate fires. Awaiting the real
  v22 cold-boot.

**Two hard rules for the in-game anim, both proven live:** (1) NO scale channels — rot+loc only;
(2) the bone partition must match the **host** (Tigrex = 45, split 31/9/5), AND the injected
skeleton's declared animated-count (`+0x1C`) must equal it. A bind/static pose collapses unless
every bone has real keyframes.

**Inject gotcha (cost a whole cold-boot):** `mhfu.inject_register(fid, path)` content-matches the
live raw buffer against `<path>.orig` (the PRISTINE native PAC) via a diff-fingerprint = the first
word where our edit ≠ orig. WITHOUT the `.orig` it falls back to a 64-byte-prefix match, which the
injected PAC's native-identical header defeats → the overwrite is silently skipped and the engine
shows the unmodified native monster. Every deployed `*.bin` needs its `*.bin.orig` (= native
`file_06185`) sibling in the inject dir. (`exporter.inject_to_live` writes it automatically.)

## The host JOINT count is data-driven — the construction crash + forge answer (2026-06-19)

v22 (skeleton `+0x1C`=45) cleared every per-frame FK crash but crashed during **construction** at
`0x08864160` reading a garbage vtable. Live RE (clean native-Tigrex capture +
`tools/eboot_dis.py`) mapped the whole anim sub-struct + joint builder:

- The anim sub-struct is at **`entity+0x80`**: component array `+0x110` (= entity+0x190), component
  **count `+0x120`** (= entity+0x1A0), **joint count `+0x124`** (= entity+0x1A4).
- **Joint builder `0x088dc40c`**: `joint_count = 0x88dc748(skeleton)`; stores it at `entity+0x1A4`;
  allocates `joint_count` Joints of **0x250** bytes.
- **`0x88dc748` (decisive):** `v0 = skeleton.bone_count (@+4)`; if `skeleton.magic (@+0) & 0x80000000`
  (0xC0000000 → yes) then `v0--`. ⇒ **`entity+0x1A4 = skeleton.bone_count − 1`.** This is read straight
  from OUR injected skeleton — **NOT a baked overlay constant. The host joint count is FORGEABLE via the
  skeleton's `bone_count` field.** (Native 49→48; v22 had 46→45.)
- **Components** (loop `0x088dc5d4`): `comp[i] = &joint_array[idx_i * 0x250]` — pointers INTO the joint
  array, with count + index list from a descriptor (`s2+0x10`/`+0x18`). **If `idx_i ≥ joint_count` the
  component points past the allocation → uninitialised → garbage vtable → crash.** That is the v22
  crash: 45 joints, but a component referenced a higher bone index. Native's 48 joints cover all its
  component indices.

**Native template (working):** `entity+0x1A4`=48, count=2 (both valid), anim 31/9/5=45; the skeleton
parses to **48 bone SECTIONS with header `bone_count`=49** (joints = 49−1 = 48). So a valid skeleton =
N sections + header bone_count = N+1.

**Forge vs conform:** the *joint count* is forgeable (set `skeleton.bone_count`); a true small slot
(e.g. 42 joints) additionally needs the component index list < 42 (descriptor source not yet fully
pinned). **v23** sidesteps that by matching native: Brute's 46 sections + native sections 46,47 = 48
sections, header bone_count=49 → 48 joints, anim 31/9/5, same size 1216512. Built + deployed (`.orig`
= native, `brute_overlay_hook` OFF since the native-structured skeleton shouldn't need the joint-fix);
awaiting cold-boot. Tools: `src/ppsspp_debug/capture_native_construction.py` (forge template),
`capture_fk_crash.py` (construction-crash reader).

## How the Brute is injected (the host-slot + overwrite path)

Brute Tigrex doesn't exist in MHFU, so we borrow the **Tigrex big-monster slot**
as the construction host (Giadrome is also a big monster but Brute Tigrex is a
Tigrex subspecies, so the Tigrex overlay/AI is the natural host):

1. **`brute_tigrex.lua`** (lua_host) hooks `QUEST_TARGETS_BUILDING` and swaps the
   Giadrome → Tigrex (`mhfu_quest_replace_monster`) so the engine natively loads
   the Tigrex model PAC **`file_06185`** + the Tigrex AI overlay.
2. It registers an **in-place inject** over `file_06185` (`mhfu_inject_register` +
   `mhfu_inject_now` to prime) — a same-size (1216512 B) PAC whose subs are padded
   to native byte offsets. The `get_subresource 0x088B89B0` seam overwrites the
   engine's raw count=7 buffer with our PAC **before** the transform reads it, so
   the engine restructures OUR data. (`inject.cpp`, the proven Phase-4 racefree
   seam — see memory `phase4-descriptor-table-seam`.)
3. The PAC = Brute skeleton(0)/PMO(1)/TMH(2)/anim(3) + native secondary
   subs(4,5,6). Layout byte-identical to native so the engine's restructure lands
   each sub where it expects.

The engine fileId for `file_06185` is the cosmetic id; the inject matches by
content (256-B header vs a `.orig` sibling + a diff-fingerprint word).

## ROOT CAUSE that blocked everything first: the PRX-stack collision

For ~10 cold-boot iterations the quest crashed during load with a **"Lua VM
corruption"** (`mhfu_lua_host` reading `0x27bd001c`) or **`mhfu_deferred` jumping
to `0x0c000000`**. These were the SAME bug, NOT a Lua bug:

- PPSSPP loads the framework PRX at a **fixed base `0x09D65000`** (size-independent;
  `sceKernelAllocPartitionMemory` over the image FAILS = it's reserved, yet thread
  stacks bypass that reservation).
- The engine's **big-monster construction thread** ("user_main" uid ≈ 0x119) runs
  with a stack at **`~0x09D8A000` — *inside* the PRX image**. As construction
  recurses, `sw`/frame writes overwrite whatever PRX content sits at `base+0x25000`:
  the **import stubs** (small PRX → `mhfu_deferred` dies calling `sceKernelDelayThread`)
  or the **Lua VM** (large PRX → `mhfu_lua_host` dies).
- The TRIGGER that tipped the stack over the edge was the **joint-fix stub's
  `jal joint_builder_fix_c`** — a C-call frame, firing even on the native passthrough.

**FIX (working): a frame-free, branchless inline-MIPS joint-fix stub** — no `jal`,
single basic block, `movn`-conditional (`framework/prx/mods/brute_overlay_hook/
mod.cpp::build_jb_stub`). It corrects the Brute's mis-computed skeleton pointer
(→ `0x0B000040`, the inject's xram copy) and rebases the bone-array, adding ZERO
stack. With it, the clobber is gone and construction completes. (The earlier
`reserve_self_memory()` attempt in `bootstrap.cpp` does NOT work — partition
reservation doesn't stop the engine's thread-stack allocator; kept only as a
documented dead end. The frame-free stub is the real fix.)

Memory: `brute-port-prx-stack-collision`. Diagnostic tooling:
`tmp/brute_prx_writewatch.py` (write-watch on the PRX import-stub band caught engine
code writing with `sp` inside the PRX), `tmp/brute_threadlist.py` (`hle.thread.list`).
Map a PRX crash PC→symbol via `base 0x09D65000 + elf_off` (psp-nm/objdump on
`mhfu_framework.elf`).

## The animation blocker (the last piece)

After the construction crash was fixed, the remaining crashes are all the anim:
1. `0x0886423c` alignment — the MHP3rd/lobby container is **hsize 0x18**; the engine
   needs **hsize 0x38**.
2. `0x08863250` bone-ref `254` OOB — the 0x38 container's secondary stream-tables
   held stale Tigrex offsets.
3. `0x0886025c` null — emptying those tables → the engine follows a null stream.
4. `0x088636ac` float-as-index — flattening the recursive block structure → the
   per-frame interpolator descends into nothing.

ALL of these are because **MHFU's in-game anim is a recursive 3-stream format the
Brute anim was never converted into**, and the streams must partition the Brute's
own 46 bones. See `docs/ANIMATION_FORMAT.md` for the decoded format. Memory:
`brute-port-anim-boneref-oob`.

## Remaining work (well-defined)

DONE: the recursive in-game anim encoder (`tools/mhfu_model/anim_ingame.py` — byte-exact
round-trip on native `file_06185`, 5 tests) + the flat→in-game converter (`from_flat_anim` /
`swap_anim_to_realmotion`) + the Blender operator (`export_ingame_bindpose_pac` /
`EXPORT_OT_mhfu_monster_ingame`, headless test passes).

DONE this session:
- ✅ **v25 loads with no crash** (stream-id partition `bone+0x50` = native {31,9,5,3}).
- ✅ host-count layout generalized into the library (`swap_anim_to_realmotion(host_count=...)`) +
  Blender exporter (`export_ingame_realmotion_pac`); 65/65 model tests pass.
- ✅ confirmed (corrected) the draw node DOES build + engage + un-cull work when co-located.
- ✅ reliable event-driven breakpoint catcher `src/ppsspp_debug/catch_bp.py`.

DONE 2026-06-20 (the COLLAPSE was a PMO-FORMAT bug, not anim):
- ✅ **Root cause of the collapse FOUND** — the converted PMO used the **0x20 "player"
  mesh-table format**; the engine's monster loader needs the **0x18 "monster" format**.
  v26 (identity-rotation rest-pose) still collapsing PROVED the anim/skeleton were red herrings.
- ✅ **0x18 monster mesh-record format fully RE'd** from native `file_06185`:
  `<2f I I 2H I>` = scale(1,1), `+0x08`=`0x80000000|vtype`(3 common, 6/7 textured),
  `+0x0C`=0 (or material-flag on textured meshes), `count`/`start` u16 @+0x10/+0x12,
  `+0x14`=`(cumulative_vgroup_index<<16)|vgroup_count`. Vgroup `2BH3I`: vg[0]=mat,
  vg[1]=unk, **vg[2]=skeleton bone (palette base)**, vg[3..5]=geoff/vbuf/ibuf (rel ge_base).
- ✅ **v29 — the Brute model + bones + textures RENDER LIVE in-game** (complete textured
  monster, no crash). v28 crashed because `+0x14` carried a cumulative *vertex* count
  (≤2862) → OOB vgroup read; v29 fixed it to the vgroup index.

DONE 2026-06-21 (static skinning solved; animation root cause pinned; matcher built):
- ✅ **Skinning math RE'd** — native verts are MODEL-SPACE (g5 verts x710 ≈ bone8 world x650;
  g0 verts z574 bound to root@origin), so the engine uses **bind-inverse** skinning (at rest all
  bone matrices ≈ identity → model-space verts render in place). Versions: v29 spiky → v30 (all
  slot0=root) FLAT (root matrix rank-deficient) → v31 (bone-LOCAL verts) CRUNCHED (bone-local was
  the wrong direction given bind-inverse) → **v32 (model-space verts + per-group nearest-bone vg[2]
  + weights slot 0) = ASSEMBLED, recognizable Brute** (bind pose; the "lying flat/splayed" is just
  the rest pose — vert bbox matches native exactly X1686/Y487/Z1398, so NOT a coordinate bug).
- ✅ **Bone matcher + anim bone_map + Blender export built** (commit c72db28, 70 tests):
  `tools/mhfu_model/bone_match.py` `match_skeletons()` (bind-position + tree-depth, cycle-guarded);
  `from_flat_anim(bone_map=)` / `swap_anim_to_realmotion(bone_map=)`; exporter `src_skeleton_pac`.
- ✅ **Animation root cause = per-vertex BLEND skinning** (DEFINITIVE). Real-motion anim (v33/v34)
  tears regardless of stream-id alignment; v36 (rotation-only) still tears but only single-bone
  groups (head/claws) move. Offline cross-ref: nearest-bone bound body groups to bones with
  mismatched motion (group53 146v→bone41 motion 259; group86 136v→bone43 motion 0). WHY: the
  original Brute mesh has **58/88 multi-bone vgroups + 30.9% fractional weights** (true blend
  skinning); v32 forced one-bone rigid → static-OK, animated-tear. MHP3rd v102 vg[2] is all-0
  (bone is in the per-vertex weights + a GE bone-matrix palette, NOT vg[2]).

REMAINING (the animation — port the per-vertex skinning; generalizable, well-defined):
1. **Option A (faithful):** parse each MHP3rd vgroup's bone-matrix PALETTE from its GE display list
   (run_ge currently captures weights but NOT the palette — add bone-matrix command handling),
   preserve the per-vertex blend weights, emit MHFU vgroups with the mapped palette (source bone →
   MHFU bone via the matcher).
2. **Option B (simpler, recommended first):** split each multi-bone vgroup into per-bone rigid
   sub-groups (assign each vertex to its dominant-weight bone, split, rigid-bind each piece with
   weight slot 0 + vg[2]=that bone). Native's own granularity; reuses the working rigid path + the
   matcher; loses blend smoothness but gets coherent animation. Each vertex's bone still needs the
   GE palette to resolve which bone a weight slot means.
3. Either way the per-vgroup **bone-matrix palette** must be extracted from the source GE list —
   that is the one missing parser piece. The matcher (built) handles source→MHFU bone indices.

NOTE: tried using the native Tigrex anim on the Brute (v35) — coherent motion but it's a FAKE
(only works because Brute is Tigrex-family; doesn't generalize). Rejected per the goal (support
the monster as-is). v32 (assembled rigid bind pose) is the stable shippable milestone.

OPERATIONAL: `.orig` sibling required for the inject to fire. The model renders now, so the
render-fix (`brute_tigrex.lua` HOME_AREA=100) is safe to leave on for skinning iteration.

## Key addresses (live RE, MHFU EU)

| addr | what |
|------|------|
| `0x09D65000` | PRX load base (fixed) — `+0x25000` overlaps the construction-thread stack |
| `0x088dc40c` / `0x088dc444` | joint builder (allocs `joint_count`×0x250 Joints) / our post-prologue patch point |
| `0x088dc748` | `joint_count = skeleton.bone_count − 1` (for 0xC0000000) — sets `entity+0x1A4`. FORGE lever |
| `0x088dc5d4` | component loop: `comp[i] = &joint[idx_i*0x250]` (idx must be < joint_count) |
| `entity+0x80` | anim sub-struct: components `+0x110`, count `+0x120`(=ent+0x1A0), joint count `+0x124`(=ent+0x1A4) |
| `0x08864160` | construction crash site (calls `comp->vt[0xC]`; garbage if comp idx ≥ joint_count) |
| `0x088B89B0` | `get_subresource` inject seam |
| `0x0885fa0c → 08863198 → 088630d0 → 08863668` | per-frame anim/keyframe walker chain |
| `0x08863668` | keyframe interpolator (`lh [sect+0xE]` frame time, recursive walk) |
| `0x089A5C44` | channel-bit → ordinal table (maps ONLY 0x08/0x10/0x20→3/4/5, 0x40/0x80/0x100→6/7/8; scale 0x200+ is OOB → crash). NOT a bone remap (old name retracted) |
| `0x088630d0` / `0x08863668` | keyframe interpolator / keyframe-pair search (called by the FK) |
| `0x0885fa0c` | per-joint anim apply (recurses skeleton children via `[joint+0x148]/[+0x14c]`) |
| `entity+0x1a4` | u16 anim-bone-count the engine uses = **host (Tigrex) 45**, NOT our skeleton's 42 |
| `entity+0x1ac` | per-entity anim-pack ptr (points at our injected 0x38 container) |
| `entity+0x1c0` | stream count (=3) |
| `entity+0x150` / `+0x1d0` | the two anim blend buffers; FK block ptr at `+0x64` (null = no anim playing) |
| `0x0949FCE0` (variable) | engine raw model buffer the inject overwrites |
| `0x0B000000` | inject xram (Brute PAC copy; skeleton sub at `+0x40`) |
| `skeleton bone+0x50` | **stream-id** (→ `joint+0x114` via `0x08860110`); native = [0]*31+[1]*9+[2]*5+[3]*3 |
| `0x0885f848` | anim section→joint BIND: sequential tree-walk, only joints whose `+0x114`==target stream; `t1 += [t1+8]` per section. Overrun if a stream has more joints than sections |
| `0x09AC4960` | per-frame visibility gate: clears skip-draw (`+0x004` bit4) iff `+0x29A`==area && `+0x638`&0x8000; then calls `0x09AC51A0`, `0x09AD62C8` |
| `0x09AC51A0` | big-mon per-frame render/anim prep → `0x088640f8` (anim bind, a0=entity+0x80) ; ra at the call = `0x09AC51E0` |
| `0x088640f8` | per-frame anim bind driver (fires every frame for a NATIVE big-mon; the per-frame anim runner) |
| `entity+0x008` | render DRAW NODE ptr (built when co-located; holds live animated 4x3 matrix @ node+0x0c..+0x48; vtable 0x089bb330). NULL when culled/not-co-located |
| `entity+0x4C8` | joint array base (stride 0x250) — **STATIC bind data; the animation is in the DRAW NODE, not here** |
| `entity+0x5dc` | engage flag (1.0 = engaged) |

## Files

- `framework/prx/mods/brute_overlay_hook/mod.cpp` — frame-free joint-fix.
- `framework/prx/mods/lua_host/scripts/brute_tigrex.lua` — swap + inject + (disabled) AI cycle.
- `framework/prx/mods/brute_port/mod.cpp` — pure-C swap+inject (superseded by the Lua mod).
- `tools/mhfu_model/{pmo_p3rd,skeleton_p3rd}.py`, `tools/mhp3rd/scan_monster_pacs.py` — converters.
- 6★ unlock to reach Tigrex quests: `tmp/unlock_ranks.py` (flag `0x2BC1` = `save_obj+0x445C` bit4).

---

## 2026-06-21 — BRUTE RENDERS + ANIMATES (textured, recognizable). Skinning solved via blend encoder.

The Brute now renders as a recognizable, textured, **animated** Brute Tigrex in-game (red back
spikes, tiger-stripe carapace, 4 legs, wings, tail), deforming under the native Tigrex animation;
only the tail still scrambles.

**Major correction — MHFU monsters are NATIVELY BLEND-SKINNED.** The vgroup field previously called
`vg[2]=boneref` is `cumulativeBoneCount`. The real bone palette is the PMO `skeleton` section
(header field 10) = `Weight{slot:u8, bone:u8}[]`, a *running-aux* state machine: walking vgroups in
index order, each consumes its `boneCount` entries patching `aux[slot]=bone` (persists across
vgroups); each vertex blends `aux[0..numweights-1]` by its VTYPE weights. Native Tigrex `file_06185`
uses up to 8 bones/vgroup. The earlier "MHFU is rigid one-bone-per-group" and "per-vertex-blend wall"
are **retracted**.

**`tools/mhfu_model/pmo_skin.py` (blend skinning reader + encoder, 75 tests):**
- `read(blob)` — resolves per-vertex `(bone, weight)` via the running palette.
- `encode(SkinModel)` — re-serialises to a native monster PMO. **Byte-faithful round-trip of the
  native Tigrex** (214 vgroups / 4128 verts / 2919 faces, 0.0 position+weight error, winding kept).
- `build(scale, vgroups, materials)` — from-scratch monster PMO (generated mesh/material tables).
- `auto_skin(mesh_groups, bone_world, nb=3)` — **derive** smooth blend weights (each vertex → its
  `nb` nearest skeleton bones, inverse-distance; per-vgroup palette capped at PSP's 8). For ported
  rigid-piece sources that have no weights.

**The Brute port (shipped, v44):** clean v32 geometry + **native Tigrex tiger-stripe textures** +
**`auto_skin` nearest-3-bone blend** to the native Tigrex skeleton, injected in-place over
`file_06185`, driven by the native Tigrex skel+anim. v37 (rigid one-bone) splayed the wings at the
roar peak; **v44 (auto-blend, avg 5.6 bones/vgroup) is "way less torn apart"** — the payoff of the
blend encoder. Remaining: the tail scrambles (long bone chain; nearest-N grabs non-chain bones).

**Texture:** `file_04898`'s OWN textures are lava-orange (tex7) + grey rock (tex1/4) — NOT the brown
tiger-stripe Brute. The native Tigrex atlas IS that look (Brute is a Tigrex subspecies), so the port
uses the native Tigrex textures. (`pmo_p3rd` material→texID also corrected: add the per-mesh
`cumulativeMaterialCount`.) Decode TMH with `tools/mhfu_model/tmh.decode_tmh`.

**OPEN — raw v102 geometry import.** `pmo_p3rd` over-expands v102 strips (34087 garbage verts / flat
sheets vs the clean 2862) — v102 strips re-index a SHARED per-group vertex pool, which `pmo.run_ge`
mishandles. AsteriskAmpersand's **PMO-Importer** parses verts correctly (5221, coherent) but its
per-mesh scale/position **assembly** isn't yet cracked (global & per-mesh scale both jumble in
replication). The clean `brute_tigrex_v32_modelspace.bin` geometry came from an unknown earlier
tool and is NOT reproducible from raw `file_04898`+`file_04899` yet. This blocks (a) a rendered
catalog of MHP3rd big monsters and (b) an authentic source-geometry rebuild in the Blender addon.
Self-contained v102 PMO = `pmo_sub + companion` (companion at `ge_base == len(pmo_sub)`).

---

## STATUS 2026-06-24 — sink SOLVED (anim retarget), damage confirmed, chest holes open

Deep HITL RE this session (full write-up: memory `brute-terrain-sink-re`). Three results:

- **Sink RESOLVED — it was the anim retarget, NOT terrain.** The long-standing "swap monster
  isn't terrain-registered → sinks" theory is **RETRACTED**. Proven HITL: a swapped *native* Tigrex
  never sinks; the swapped Brute's **entity sits exactly on the floor** (entity `+0x204` == player
  combat-entity `0x090B3440+0x204`, measured co-located — note `camera-target 0x09998D54` is a
  CONSTANT ~270, NOT the floor). The engine grounds the entity correctly; the **mesh** rendered ~a
  lower-body below the origin because the cross-game **bone-matcher mis-aligned the collapsed root
  chain** (host Tigrex 3 origin bones vs Brute source 2) and starved the **host HIP (joint 2)** of
  its source vertical track (`locY`≈4809). Fixed at the source: `bone_match._fix_leading_root_chain`
  (align the leading origin run from the tail; surplus host root → placeholder). Rebuilt
  **`brute_tigrex_v53_animfix.bin`**; cold-booted → Brute **stands on his feet, idle and moving.**
  The obsolete per-frame floor-poke hack in `brute_tigrex.lua` is removed.

- **Damage CONFIRMED working.** The Brute hits the player. A Giadrome→Tigrex *swap* yields a fully
  combat-registered native monster (collision node `entity+0x2EC` present). The `combat-registration-
  node-gate` ~2-damaging-monster cap is a CLONE limitation; a single swapped monster is unaffected.

- **OPEN (minor): chest skinning holes.** Red gaps at the chest/throat/front-leg boundary under
  animation. NOT missing geometry (88 grp / 2689 v / 2973 f all preserved; bind pose renders clean)
  — a pose-dependent **skinning tear** where verts blended across body-region-boundary bones
  separate when posed, exposing backfaces. Fix = refine the chest-boundary skinning (rebuild +
  in-game iteration). Next-session follow-up.

- Also still open from before: real per-clip AI (movement looks "yanked" = native action cycling,
  no bespoke AI layer yet) and the source-geometry rebuild from raw MHP3rd (companion-file path).

---

## STATUS 2026-06-24 (cont.) — skinning glitches + the generalization plan

After grounding, in-game review found residual **skinning glitches**: a chest/throat hole and, at
the wing roots, a tear. Root cause: our skinning is GUESSED (`pmo_skin.auto_skin` nearest-bone) +
PATCHED (`pmo_skin.weld_seams`). Iterated welds (all on disk as rollback PACs):
- v53 = no weld (chest+hip holes, wings fine).
- v54 = weld ALL coincident cross-bone seams (>150 boneDist) to a single shared bone → holes gone
  but the **wing root stiffened** (welding a thin membrane to one rigid bone distorts it).
- v56/v57 = BANDED weld (`pmo_skin.weld_seams(min_bonedist,max_bonedist)`, band the DOMINANT-bone
  separation, default [150,300]) → wings preserved (333-boneDist membrane skipped) + chest welded,
  but the single-bone weld now makes **rigid spikes** on belly/back, and a throat↔chest seam tears.
Shipped build = `tmp/brute_tigrex_v57_weldband2.bin`. New tools: `tools/find_skin_seams.py`
(pose-independent tear detector — the reliable offline metric), `blender_mhfu/hole_check.py`
(approximate multi-angle render; do NOT trust an anim-posed offline render — the importer FK
diverges from the engine).

**Conclusion: single-bone welding is the wrong tool (fixes holes, makes spikes). The principled fix
= WEIGHT TRANSFER (drop the weld).** And the user wants to port monsters with **no similar MHFU
native** — which breaks "transfer from the native" — so the plan generalizes: same-family transfers
from the native MHFU monster; no-reference uses the SOURCE model's own rigid binding remapped onto
the host via a bone map; both then smooth + inpaint + interactive review.

**→ Full forward plan + 3-agent research synthesis (algorithms, free/open tools to adopt, the
interactive-addon design): `docs/MONSTER_PORT_SKINNING_PLAN.md` (Phases A/B/C).** Continue there.
