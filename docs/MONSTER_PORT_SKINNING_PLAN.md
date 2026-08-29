# MHP3rd → MHFU Monster-Port Skinning Pipeline — Plan (Phases A/B/C)

Branch `mhp3rd-monster-port`. Forward plan + research synthesis for **clean, generalizable
monster porting**. Written 2026-06-24 after the Brute Tigrex port reached "renders + animates
+ textured + grounded + deals damage, but with residual skinning glitches."

> **STATUS 2026-08-29: PHASE A DONE (in-game). PHASE B's SKINNING IS DONE AND PROVEN
> LOSSLESS — and it turned out not to be the blocker. PHASE C not started.**
>
> The premise this plan was written on ("MHP3rd blend-skins, MHFU is rigid, so a
> no-reference port needs derived weights") is **half wrong**: MHFU's own big monsters are
> blend-skinned too, both games share the PSP GE's 8-matrix limit, and a monster's
> authentic per-vertex skin therefore transfers **exactly**. Measured, not argued —
> `tools/skin_fidelity.py` round-trips **226 of 226** in-quest MHP3rd monsters with a max
> weight error of **0.0**, and across all 2120 skinned MHP3rd PACs no vgroup exceeds 8
> bones, so the palette cap can never drop an influence. There is no weight-derivation
> problem to solve for a no-similar-native monster: ship the source rig
> (`--source-skeleton`) and its own weights come with it (`--skin source`, auto-selected).
>
> **What actually blocked a no-similar-native port was the anim STREAM PARTITION**, one
> level up from skinning — MHFU walks a rig in three streams that must each be one
> complete subtree in contiguous index order, and MHP3rd rigs are not authored that way
> (187 of 212 need reordering). Fixed by `skeleton.derive_stream_partition` +
> `reorder_bones`, which reproduce the native Tigrex's `[31, 9, 5]` exactly. See
> `docs/ANIMATION_FORMAT.md` "Stream partition".
>
> **Still open:** nothing in this plan has been cold-booted since the fix. A Zinogre port
> (`file_05339`, 51 bones, split `[33, 6, 7]`) builds and passes every offline check in
> `tools/verify_port.py` — including the ones the native `file_06185` passes — but has
> never been loaded. That is the next step, and it is the only remaining unknown for the
> Phase-B goal. Sections B/C below are kept as written; B's steps 1/3/4 are superseded by
> the above, its steps 2/6/7 (bone map for a RETARGET port, bind-correction, host-slot
> strategy) still stand, and C has not started.

---

## Where we are (current state, 2026-06-24)

The **authentic Brute Tigrex** is ported and live in MHFU (Giadrome→Tigrex swap quest):
- ✅ his own geometry (MHP3rd `file_05248`/`file_05249`, v102), own brown textures, own 77-clip
  moveset; renders, animates, **deals damage** (swap = combat-registered).
- ✅ **Grounded** — the "sinks into the floor" bug was the **anim-retarget bone-matcher
  off-by-one** (collapsed root chain starved the host hip of its vertical `locY`), fixed in
  `bone_match._fix_leading_root_chain`. NOT a terrain problem. (See `BRUTE_TIGREX_PORT.md`,
  memory `brute-terrain-sink-re`.)
- ✅ **SKINNING FIXED (Phase A, v58, in-game confirmed 2026-06-24)** — replaced the *guessed*
  (`pmo_skin.auto_skin` nearest-bone) + *patched* (`pmo_skin.weld_seams`) skinning with principled
  **weight TRANSFER from the native Tigrex** (`pmo_skin.transfer_weights_from_reference`): the
  native `file_06185` sub1 is already perfectly skinned to the exact host rig, so for each Brute
  vert we closest-surface-barycentric-blend the native influences. No guess, no weld → throat/belly
  holes gone, spikes gone, tail no longer cut (HITL-verified). Shipped build =
  `tmp/brute_tigrex_v58_transfer.bin`. Offline seam metric: INTER-vgroup tear candidates
  191(v53)/122(v57) → **6**, worst bone-sep 333 → 116.

**The new constraint that shapes this plan:** the user wants to port monsters with **NO similar
native monster in MHFU** (Zinogre, Arzuros, …), not just Tigrex-family. So the pipeline must work
*without* a same-family reference model.

---

## The unifying insight (one pipeline, pluggable seed)

Same-family and no-reference ports differ ONLY in where the skinning **seed** comes from; the
downstream is identical:

```
[1] SEED      same-family → copy the NATIVE MHFU monster's weights (perfect oracle, same rig)
              source-rig  → use the SOURCE model's OWN blend weights (decoded from the v102 bone
                            palette by pmo_p3rd → pmo_skin.from_source_influences). IMPLEMENTED
                            2026-06-29 (`--skin source`); best when the source rig is SHIPPED
                            (source-skeleton: bone i → i+lead_pad, 1:1). NOTE: MHP3rd big monsters
                            ARE blend-skinned (the old "rigid pieces" claim was a misID).
              no-native   → remap the source weights onto the host skeleton via a bone map
[2] SMOOTH    seed → clean blend weights (region-locked auto_skin / Blender Data-Transfer /
                      Robust Weight-Inpainting for occluded verts)
[3] SEAMS     close tears: merge coincident verts, OR equalize bone at seams — NOT a rigid
                      single-bone weld (that caused the spikes)
[4] QA        interactive Blender review loop (anim playback + self-intersection flagging)
```

**The real bottleneck is bone CORRESPONDENCE (source→host map), not skinning math** (all 3
research agents agree). Same-family = automatic (have it). Cross-species (wolf→wyvern slot) =
position-matching fails at the limbs → needs a **one-time ~15-min manual bone map per creature
archetype**. That manual map is the single unavoidable human step; everything after it automates.

**Host-slot reality:** the MHFU engine drives a FIXED overlay slot whose host skeleton has a
fixed bone count + stream partition (Tigrex slot = 45 animated bones, 31/9/5). The injected
model MUST conform to it. The host skeleton controls the ANIMATION; the MESH can be any shape.
So a no-native creature uses the closest-archetype host slot (Tigrex for big monsters) + its
animations, and we force only the action-IDs whose motion makes visual sense
(`mhfu.on_bigmonster_action`).

---

## Research synthesis (3 web agents, 2026-06-24)

**Algorithms** (free/open, headless-scriptable unless noted):
- **Blender Data Transfer modifier** (`vert_mapping='POLYINTERP_NEAREST'`, `data_types_verts=
  {'VGROUP_WEIGHTS'}`, `layers_vgroup_select_src='ALL'`) — transfer weights from a reference mesh
  by nearest-face barycentric interp. The same-family fix. Must pre-create target vgroups by name;
  normalize + `vertex_group_smooth` after. GPL (Blender).
- **Robust Skin Weights Transfer via Weight Inpainting** (Abdrashitov et al., SIGGRAPH Asia 2023)
  — closest-surface transfer with a distance+normal acceptance gate, then **Laplacian inpainting**
  for unmatched (occluded/concave) verts (wing armpit, throat fold). Open impls:
  `rin-23/RobustSkinWeightsTransferCode` (MIT, standalone Python via `libigl`+`robust-laplacian`)
  and `sentfromspacevr/robust-weight-transfer` (GPL-3, Blender; core `weighttransfer.py` is pure
  numpy/scipy, separable). **The top recommended algorithm — works WITH or WITHOUT a same-family
  reference.**
- **Our existing `pmo_skin.auto_skin`** (segment-distance + chain-aware + region-lock) is already
  state-of-art for no-reference disjoint-piece low-poly meshes (Agent 3) — the improvement is to
  **SEED its region-dominant with the remapped source bone** instead of a nearest-bone vote, and
  to **drop the single-bone `weld_seams`** (the spike cause).
- **libigl BBW** = premium from-scratch, but needs a watertight tet mesh → impractical for our
  disjoint "mesh soup." **Bone Heat** (Blender auto-weights) FAILS on disjoint pieces. **Voxel
  Heat Diffuse Skinning** (free `meshonline/Surface-Heat-Diffuse-Skinning`) handles disjoint
  meshes (cross-check only; not segment-aware). **UniRig** (neural, MIT) = from-scratch rig, needs
  GPU, predicts its own skeleton (not our fixed host) → not for this case.

**Tools to ADOPT (don't reinvent):**
| Tool | License | Use |
|---|---|---|
| Robust Weight Transfer (`sentfromspacevr` / `rin-23`) | GPL / MIT | core transfer+inpaint algorithm |
| **EasyWeight** (Blender Studio, extensions.blender.org) | GPL | **"Weight Islands" = auto stray-weight/spike detection** + normalize/clean/smooth/symmetrize |
| **braverabbit Smooth Weights** (gumroad, free) | free | volume-smoothing **across disconnected pieces** = our rigid-piece seams |
| **Mwni blender-animation-retargeting** (GitHub) | MIT | interactive **bone-map editor** for cross-species (export map → feed our pipeline) |
| AsteriskAmpersand **PMO-Importer** (GitHub) | GPL-3 | reference only; ours is more capable (v102 + anim + live inject). Confirms this port pipeline is genuinely novel. |

**Interactive-addon APIs found (Agent 2):** anim-clip `EnumProperty` dropdown + `scene.frame_set`
scrub + "scan all clips"; weight-cleanup ops (`vertex_group_normalize_all/clean/smooth/mirror`,
`data_transfer`); **`mathutils.bvhtree.BVHTree.overlap()` per animation frame → auto-flag the
broken poses**; GPU deformation-magnitude overlay (`SpaceView3D.draw_handler_add`); Blender 4.4+
uses `animation_data.action_slot` (legacy `.action` removed in 5.0).

Full URLs/snippets are in the 3 agent reports (this session's transcript) — pull them in when
implementing each phase.

---

## PHASE A — fix the Brute (same-family, quick win)

**STATUS 2026-06-24: DONE — IN-GAME CONFIRMED.** v58 = `tmp/brute_tigrex_v58_transfer.bin`
(deployed to both PPSSPP memsticks; `brute_tigrex.lua` points at it; relocate inject, 1.62 MB).
HITL-verified live: throat/belly holes gone, spikes gone, tail no longer cut. Offline seam
metric (`find_skin_seams.py`) **collapsed**: INTER-vgroup tear candidates **191 (v53) / 122
(v57) → 6**, worst bone-sep **333 → 116**; the 6 residual are mild creases at the hip/groin
junction (bone 2 vs 21/26), not red holes. Encode valid (0 unresolved weights, all sums = 1,
palette ≤ 8). The reference-transfer approach is validated end-to-end.

**Goal:** a clean v58 Brute — no spikes, no holes — by replacing the guess+patch skinning with
native-Tigrex weight transfer. Validates the reference-transfer approach end-to-end.

**Implemented (this session):**
- `pmo_skin.transfer_weights_from_reference(mesh_groups, ref, parents=, dead=)` — closest-surface
  barycentric weight transfer from a fully-skinned reference SkinModel (vectorized-numpy Ericson
  `_closest_bary_all`). Dead host joints (anim leaves at rest) reassigned to nearest live ancestor
  (`_live_ancestor`) — preserves the tail fix. Pure-Python, headless, no scipy/trimesh.
- `port_p3rd.port_monster(..., skin="transfer")` — same-family path: reference = the host frame's
  OWN PMO sub (native Tigrex `file_06185` sub1); drops `auto_skin`+`weld_seams` entirely.
- CLI `build_p3rd_port.py --skin transfer`; tests `test_pmo_skin.py` (transfer correctness +
  dead-joint reassignment), all 9 pass. `auto_skin`/`weld_seams` remain the **no-reference**
  default (Phase B).

**Tasks:**
1. Implement weight transfer from the native Tigrex (`file_06185` sub1, already perfectly skinned
   to this exact skeleton; parse with `pmo_skin.read`). Two options:
   - **Pure-Python** (keeps headless CLI): for each Brute vert, nearest-triangle on the native
     mesh → barycentric-interpolate native influences (use `trimesh.proximity.closest_point` or a
     KD-tree). Implement as `pmo_skin.transfer_weights_from_reference(brute_groups, native_skinmodel)`.
   - **Blender** (reference quality): Data Transfer `POLYINTERP_NEAREST` + Robust Inpainting for
     the throat fold; in the addon export path.
2. **DROP `weld_seams`** from the Brute build (it caused the spikes); optionally keep
   `merge coincident verts` (≈1.5u) to close seams topologically.
3. Add a `vertex_group_smooth` (2 passes) + normalize pass.
4. Rebuild → v58; verify with `tools/find_skin_seams.py` (tears should be near-zero) and
   `blender_mhfu/hole_check.py` (note: synthetic-pose render is approximate — see Gotchas).
5. Deploy v58, cold-boot HITL to confirm (chest/throat/belly/back clean, wings still good).

**Key files:** `tools/mhfu_model/pmo_skin.py` (add `transfer_weights_from_reference`),
`tools/mhfu_model/port_p3rd.py` (swap `auto_skin`+`weld` → transfer for same-family),
`tools/build_p3rd_port.py`. Effort: ~½–1 day. Rollback PACs on disk: v53 (no weld) / v54
(weld-all) / v57 (banded weld) / v58 (transfer).

---

## PHASE B — general no-reference pipeline (Zinogre/Arzuros-class)

> **NOTE (2026-06-29):** the **source-skeleton** Brute's tail-cut is **NOT** a Phase-B
> skinning defect. Proven offline 6 ways: `auto_skin`'s region-lock already binds the tail
> vgroups to **tail-only bones**, there are **0 tail tears** (the only 2 real tears sit on
> the upper back/wing), the tail joints are **fully animated**, and the source-skeleton v61
> is **bind-pose-identical** to the transfer-skinned v58. So no skinning change fixes it —
> the cut is a **posed-only / structural severable-tail** artifact (the 4-joint source tail
> vs the host's 5), which belongs with the deferred **sever mechanic**, not here. Phase B
> remains about *holes/spikes* on a genuinely-no-reference monster, which is a different
> problem.

**Goal:** port a monster with no similar MHFU native, cleanly, using the source's own binding.

**Tasks:**
1. **Read the source binding:** ⚠️ CORRECTED 2026-06-29 — MHP3rd big monsters are **blend-skinned,
   not rigid** (the "weightCount=0" claim was a misidentified model). `pmo_p3rd.parse` now decodes the
   v102 bone palette (header field 10) and yields each vert's real `[(source_bone, weight), …]`;
   `pmo_skin.from_source_influences` ports them. (Genuinely-rigid sources still resolve to
   `[(bone, 1.0)]` — the bc=1 case.)
2. **Bone-correspondence map (the human step):** for non-Tigrex creatures, position-distance
   (`bone_match`) fails at extremities → build a **topology-aware** matcher (label bones by
   parent-chain depth + child-count, match labels first, ties by distance) AND/OR an interactive
   map (import both skeletons, use Mwni retargeting UI, export a `{source_bone:host_bone}` dict,
   one-time ~15 min per archetype, reusable per family).
3. **Remap rigid binding onto the host** via the map; verts of unmapped source bones → nearest
   mapped ancestor.
4. **Smooth:** `auto_skin(parents=host_parents, hops=1, region_lock=True, segment=True, nb=3)`
   SEEDED by the remapped bone as the region dominant (extend `auto_skin` to accept a seed).
5. **Close seams** (merge coincident OR blend-zone falloff — NOT rigid weld).
6. **Retarget animation:** `anim_ingame.from_flat_anim` with the bone map + a per-bone bind-space
   correction quaternion (host-bind-dir → source-bind-dir) for dissimilar rest orientations.
7. **Host-slot/action strategy:** use the closest-archetype host (Tigrex big-mon slot); force only
   sensible action-IDs via `mhfu.on_bigmonster_action`.

**Key files:** `bone_match.py` (topology-aware matcher + map I/O), `pmo_skin.py` (seeded auto_skin,
merge/blend-zone), `anim_ingame.py` (bind-correction), `port_p3rd.py` (no-reference path).
Effort: ~1–2 days + per-creature manual map. **Unavoidable human step = the bone map (step 2).**

---

## PHASE C — interactive Blender addon (modder-in-the-loop)

**Goal:** let a modder import a ported monster, REVIEW + FIX deformation in Blender (anim playback,
weight paint, QA), and re-export — catching glitches BEFORE the emulator. The generalizer that
makes Phase B practical (no perfect reference → manual touch-up needed).

**Tasks (feature panel):**
1. **Animation review:** clip `EnumProperty` dropdown over `bpy.data.actions`; assign + scrub
   (`scene.frame_set`); "scan all clips" batch (step keyframes, `bpy.ops.render.opengl`).
2. **Weight tools:** one-click normalize/clean/smooth/symmetrize/transfer-from-reference; integrate
   **EasyWeight "Weight Islands"** (stray-weight/spike detection) + **braverabbit Smooth Weights**
   (disjoint-piece smoothing).
3. **Deformation QA:** `BVHTree.overlap()` on the evaluated mesh per frame across all clips →
   auto-flag (clip, frame) with self-intersections / gaps; scrollable "jump to" list.
4. **Overlay:** GPU per-vertex deformation-magnitude heatmap (`SpaceView3D.draw_handler_add`).
5. **Bone-map editor** (for Phase B): interactive source→host pairing (adopt/wrap Mwni), export to
   the pipeline's map format.
6. **Export:** route the reviewed mesh back through `exporter.export_skinned_monster_pac` /
   `port_p3rd_monster_pac`.

**Key files:** `blender_mhfu/` (new operators/panels), reuse `importer.py`/`exporter.py`. Effort:
several days. Build against Blender 4.4+ (slotted actions). This phase *contains* Phase B's
interactive layer.

---

## Tooling already built this session (reuse)
- `tools/find_skin_seams.py` — pose-independent tear detector (coincident verts skinned to far-apart
  bones; reports position + vgroups + bone-dist). The reliable offline metric.
- `blender_mhfu/hole_check.py` — multi-angle render with backface culling + gentle/anim/bind pose.
  NOTE: synthetic-pose render is only approximate (importer anim FK diverges from the engine;
  arbitrary posing over-separates membranes) — good for *spotting*, not *verifying*. Use
  `find_skin_seams.py` as the reliable check; final sign-off = cold boot.
- `blender_mhfu/compare_height.py` / `compare_posed.py` — bind/posed Z-extent vs origin.
- `pmo_skin.weld_seams` (banded, single-bone) — SUPERSEDED by Phase A/B (kept for reference; remove
  from the build once transfer lands).

## Gotchas / hard-won facts
- camera-target `0x09998D54` is a CONSTANT (~270), NOT the floor; use player combat-entity
  `0x090B3440+0x204` as the floor gauge.
- Plugins load on cold boot only; the inject fires at quest depart / section entry.
- The importer's animation FK does NOT match the engine — never trust an anim-posed offline render
  for verification.
- 8-bone-per-vgroup palette cap in the PMO encoder; seam fixes must respect it.
- `tools/mhfu_model/pmo.py` reshape encoder is FROZEN (49/49 byte-identical round-trip) — extend via
  new modules.

## Recommended order
**A** (clean Brute + validate transfer) ✅ DONE → **C** (the addon, folds in B's interactive bits)
→ finish **B** algorithm pieces inside the addon. Each phase is independently shippable. **B & C
are DEFERRED** as of 2026-06-24 (Phase A meets current needs); pick up here for a no-similar-native
monster (Arzuros suggested first — quadruped, no wings/tail, fewer bone-map edge-cases than Zinogre).
