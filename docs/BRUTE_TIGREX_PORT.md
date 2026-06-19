# Brute Tigrex live port — integration RE & status (2026-06-19)

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
| Animation | ❌ blocked — needs a recursive **in-game-format** encoder |

The model + skeleton + textures convert correctly and the engine constructs the
monster into a live quest. The **only** remaining blocker is the animation: the
team's converted anim is in MHP3rd/lobby format, and MHFU's *in-game* anim is a
different, recursive 3-stream format that must be authored to match the 46-bone
skeleton (see `docs/ANIMATION_FORMAT.md`). **A correct anim cannot be faked with
native Tigrex data** — the per-frame interpolator requires the animation and the
skeleton to describe the same bones (proven: unmodified native anim + Brute skel
crashes the per-frame tick identically).

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

Build a **recursive in-game anim encoder** + a **P3rd→in-game converter** (split the
46-bone skeleton into the 3 streams, emit recursive `{0x80000000|tag,count,size}`
sections with the Brute's keyframes), to live in `tools/mhfu_model/anim.py` + the
Blender exporter so the addon emits one usable `.bin` (the user's stated goal). A
correct **bind-pose** in this format (1 keyframe/channel) renders him static; the
real P3rd motion is the same encoder with his keyframes.

## Key addresses (live RE, MHFU EU)

| addr | what |
|------|------|
| `0x09D65000` | PRX load base (fixed) — `+0x25000` overlaps the construction-thread stack |
| `0x088dc40c` / `0x088dc444` | joint builder / our post-prologue patch point |
| `0x088B89B0` | `get_subresource` inject seam |
| `0x0885fa0c → 08863198 → 088630d0 → 08863668` | per-frame anim/keyframe walker chain |
| `0x08863668` | keyframe interpolator (`lh [sect+0xE]` frame time, recursive walk) |
| `0x089A5C44` | bone-remap table (built per loaded skeleton; sized to bone count) |
| `0x0949FCE0` (variable) | engine raw model buffer the inject overwrites |
| `0x0B000000` | inject xram (Brute PAC copy; skeleton sub at `+0x40`) |

## Files

- `framework/prx/mods/brute_overlay_hook/mod.cpp` — frame-free joint-fix.
- `framework/prx/mods/lua_host/scripts/brute_tigrex.lua` — swap + inject + (disabled) AI cycle.
- `framework/prx/mods/brute_port/mod.cpp` — pure-C swap+inject (superseded by the Lua mod).
- `tools/mhfu_model/{pmo_p3rd,skeleton_p3rd}.py`, `tools/mhp3rd/scan_monster_pacs.py` — converters.
- 6★ unlock to reach Tigrex quests: `tmp/unlock_ranks.py` (flag `0x2BC1` = `save_obj+0x445C` bit4).
