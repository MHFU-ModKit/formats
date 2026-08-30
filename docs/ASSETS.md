# Regenerating the game-derived assets

This repository ships **no game data and no game artwork**. Five categories of
file are produced locally, gitignored, and never committed, because they are
derived from Capcom-owned material that is not ours to redistribute:

| Category | Path | Needs a copy of the game? | Regenerate with |
|---|---|---|---|
| A — HUD artwork | `mhfu_hud/assets/` | no | `mhfu_hud/tools/fetch_assets.py` |
| B — Disassembly listings | `tools/out/**/*.asm` | yes | `tools/eboot_dis.py` (static) or PPSSPP (live) |
| C — Game-data tables | `tools/out/**/*.bin` | yes | the `tools/re_*.py` dumpers |
| D — Ported monster PACs | `tmp/*.bin` | yes (**two** games) | `tools/build_p3rd_port.py --manifest ports/<name>.toml` |
| E — Species action intel | `species/*.json` | yes | `tools/em_intel.py --all` |

Everything here is reproducible from **your own** legally obtained copy of the
game. Nothing in this repo requires, distributes, or links to game files.

If you only want to run the tooling and read the RE notes, you need none of
this — the docs in `docs/` stand on their own, and the HUD degrades gracefully
without artwork.

---

## Prerequisites

```bash
cd tools && ./setup.sh          # clones mhff/mhef, creates venv
source ../venv/bin/activate
pip install -r tools/requirements.txt
```

Category A additionally needs `pillow`; categories B and C need `websockets`
for the PPSSPP debugger bridge:

```bash
pip install -r mhfu_hud/requirements.txt      # pygame-ce, pillow, websockets
pip install -r src/ppsspp_debug/requirements.txt
```

---

## Category A — HUD artwork (943 images, ~11 MB)

The live HUD (`mhfu_hud/`) draws item, monster and map icons plus a village
backdrop. These are **Capcom artwork hosted on the Monster Hunter Fandom wiki**,
fetched at setup time rather than vendored.

**No copy of the game is required for this category.**

```bash
python mhfu_hud/tools/fetch_assets.py
```

That populates, under `mhfu_hud/assets/`:

| Directory | Contents | Source |
|---|---|---|
| `backgrounds/` | `village.png` | fixed wiki URL |
| `maps/` | `snowy_mountains.png` + best-effort per-location resource maps | fixed URL + scrape |
| `monsters/` | `<slug>.png` — the MHFU iOS icon set, via the MediaWiki `allimages` API | wiki CDN |
| `items/` | `<slug>.png` — scraped from `MHFU:_Item_List` | wiki scrape |

Every directory also gets a `manifest.json` (slug → filename) written by the
same script, so the mapping is regenerated too — there is nothing to restore by
hand.

Useful flags:

```bash
python mhfu_hud/tools/fetch_assets.py --quick        # only the two fixed-URL assets
python mhfu_hud/tools/fetch_assets.py --no-items     # skip the 850 item icons (slowest part)
python mhfu_hud/tools/fetch_assets.py --no-maps
python mhfu_hud/tools/fetch_assets.py --no-monsters
python mhfu_hud/tools/fetch_assets.py --only-items
```

All images are normalised to PNG through Pillow, so webp/gif/jpg sources come
out uniform. **Network failures are logged and skipped, not fatal** — the HUD
falls back to drawn placeholders for anything missing, so a partial fetch still
leaves you with a working HUD.

Wiki page structure changes over time; if a scrape comes back thin, the fixed-URL
assets (`--quick`) are the stable subset.

---

## Getting a copy of the game (categories B and C)

Categories B and C read the game's own code and data, so they need a dump of a
copy **you own**. The only method described here is dumping your own disc:

1. A PSP running custom firmware can dump a UMD you physically own to an ISO
   (CFW's VSH menu exposes a UMD-dump option; standalone dumper homebrew does
   the same). If you own the digital release instead, you already have the data
   on your own console/account.
2. Put the resulting ISO in `workspace/iso/`. That whole directory is gitignored.

`tools/extract_iso.py` recognises known-good dumps by MD5 and will tell you
which one you have:

| MD5 | Release |
|---|---|
| `1f76ee9ccbd6d39158f06e6e5354a5bd` | MHP2G, UMD |
| `cc39d070b2d2c44c9ac8187e00b75dc4` | MHP2G, PSN |

Then extract:

```bash
python tools/extract_iso.py workspace/iso/game.iso workspace/extracted/
```

This yields `workspace/extracted/PSP_GAME/SYSDIR/BOOT.BIN` — the decrypted
EBOOT ELF that category B reads — plus the archive you can unpack further per
the "Quick Start" section of `CLAUDE.md` (`--decrypt` / `--extract-data` for
`DATA.BIN`).

> **Region matters.** All runtime RE in this project targets **MHFU EU
> (ULES01213)**, and every address in `docs/` and in the listings below is an EU
> address. A JP (MHP2G) or NA dump loads at different addresses; the tooling
> still works, but the specific VAs will not line up. `tools/eboot_dis.py`
> hardcodes the EU segment map (file `0x25b4` → VA `0x08804000`, length
> `0x1c7a90`).

---

## Category B — disassembly listings (`tools/out/**/*.asm`)

MIPS listings of the game's own code, used as working notes throughout the RE
docs. They split by **where the code lives**, which decides how you regenerate
them.

### B1 — EBOOT code (`0x088xxxxx` / `0x089xxxxx`) — static, no emulator

Readable straight out of `BOOT.BIN`:

```bash
python tools/eboot_dis.py <va> [count]           # disassemble count insns from VA
python tools/eboot_dis.py --words <va> [n]       # raw u32 words (data / tables)
python tools/eboot_dis.py --xref <va> [from] [to] # find lui/jal references to VA
```

The 13 EBOOT-range listings and their entry points:

| Listing | Entry VA | Generator |
|---|---|---|
| `vt8_resolver/apply_0885F848.asm` | `0x0885F848` | `tools/re_vt8_and_resolver.py` |
| `vt8_resolver/anim_resolver_0885F928.asm` | `0x0885F928` | `tools/re_vt8_and_resolver.py` |
| `vt8_resolver/vt8_picker_08865254.asm` | `0x08865254` | `tools/re_vt8_and_resolver.py` |
| `walker_re/installer_0885F9A0.asm` | `0x0885F9A0` | `tools/re_installer_and_vt8.py` |
| `walker_re/walker_088637C4.asm` | `0x088637C4` | `tools/re_walker_setters.py` |
| `walker_re/real_caller_08865648.asm` | `0x08865734` | `tools/re_walker_setters.py` |
| `slot_installer/installer_110_08860390.asm` | `0x08860390` | `tools/find_slot_installer.py` |
| `slot_installer/applier_08863E70.asm` | `0x08863E70` | `tools/find_slot_installer.py` |
| `slot_installer/caller_func_08865044.asm` | `0x08865044` | `tools/disasm_driver_caller.py` |
| `cutscene_driver/disasm_func_088637C4.asm` | `0x088637C4` | `tools/disasm_cutscene_driver.py` |
| `cutscene_driver/disasm_writer_088639A4.asm` | `0x088639A4` | `tools/disasm_cutscene_driver.py` |
| `evdemo_eu/disasm_eu_trigger_088D5754.asm` | `0x088D5754` | `tools/verify_evdemo_eu.py` |
| `ai_step_bigmonster/ai_step_callers.asm` | JAL scan of `0x08865648` | `tools/re_ai_step_and_bigmonster_list.py` |

The last one is a scan rather than a linear disassembly: it sweeps
`0x08800000..0x089FFFFF` for the encoded `jal 0x08865648` word (`0x0C219592`) to
enumerate callers of the per-frame AI tick.

### B2 — overlay code (`0x09Axxxxx` / `0x09Cxxxxx` / `0x09Dxxxxx`) — needs a running game

Monster AI overlays are **not in the EBOOT**. They are loaded into RAM at
runtime, so they can only be disassembled from a live emulator with the target
monster loaded. Set up the PPSSPP debugger connection first — see
`docs/agent_debugging.md`.

```bash
PYTHONPATH=src python src/ppsspp_debug/disasm_func.py 0x09AC52DC --count 280
PYTHONPATH=src python src/ppsspp_debug/disasm_func.py 0x088637C4 --marks 0x088639A4,0x088639C0
```

Output lands in `src/ppsspp_debug/output/disasm/` (also gitignored).

| Listing | Entry VA | Generator |
|---|---|---|
| `tigrex_base_writers/.../func_prologue.asm` | `0x09AC5080` | `tools/re_disasm_slot_loop.py` |
| `tigrex_base_writers/.../dispatcher_09AC5200.asm` | `0x09AC5200` | `tools/re_disasm_slot_loop.py` |
| `tigrex_base_writers/.../slot_loop_09AC52DC.asm` | `0x09AC52DC` | `tools/re_disasm_slot_loop.py` |
| `tigrex_base_writers/.../caller_09D26570.asm` | `0x09D26500` | `tools/re_disasm_slot_loop.py` |
| `ai_step_bigmonster/sw_0x640_writers.asm` | `0x09AC46D8` region | `tools/re_ai_step_and_bigmonster_list.py` |

`tools/re_disasm_slot_loop.py` is self-driving: it launches PPSSPP, loads a
Tigrex savestate (slot 7), disassembles the ranges, writes
`tools/out/tigrex_base_writers/disasm_<timestamp>/*.asm`, and exits. It sets no
breakpoints, so it cannot freeze the emulator. Savestates are yours and are not
in the repo — record one in a Tigrex quest first.

> **Always use `memory.disasm`, never a raw RAM read.** PPSSPP's JIT rewrites
> translated overlay code with `0x68XX_XXXX` EMUHACK markers, so a raw read of
> overlay code returns markers instead of instructions. The debugger's disasm
> event returns the original opcodes. This is why B2 listings come from the
> debugger and not from a memory dump.

---

## Category C — game-data tables (`tools/out/**/*.bin`)

Two small tables read verbatim out of a live monster's data. Both need a
running game with a Tigrex loaded, and the PPSSPP debugger enabled
(`docs/agent_debugging.md`).

| File | Size | Contents | Regenerate with |
|---|---|---|---|
| `tools/out/tigrex_prob_table/tigrex_prob_table.bin` | 1024 B | the action probability table at `entity+0x1AC` | `PYTHONPATH=src python tools/re_tigrex_probability_table.py` |
| `tools/out/ai_step_bigmonster/tigrex_actionlist_640.bin` | 256 B | the big-monster action list at `entity+0x640` | `PYTHONPATH=src python tools/re_ai_step_and_bigmonster_list.py` |

`re_tigrex_probability_table.py` reads the table base from `entity+0x1AC`, dumps
`0x400` bytes, scans for the `0xFFFF` sentinel / 8-byte record header, walks the
records, and dumps the first `0x40` bytes at each unique pointer it finds — so
it prints a decoded view alongside the raw `.bin`.

Both scripts write into `tools/out/<name>/` and also emit `.txt` / `.json`
companions. **Only the `.bin` and `.asm` outputs are gitignored** — the textual
analysis logs in `tools/out/` are our own notes and remain tracked, so you can
read the conclusions without regenerating anything.

---

## Category D — ported monster PACs (`tmp/*.bin`)

A ported monster is an MHFU big-monster PAC spliced from **two** games' data — an
MHP3rd donor (model, skeleton, textures, moveset) onto an MHFU host frame. Every
byte of it is Capcom's, so no built PAC is committed, and `tmp/` is gitignored.

What *is* committed is the recipe: one `port.toml` per port under `ports/`,
hand-authored file ids and numbers, read by `mhfu_monster_editor.manifest`.

```bash
python tools/build_p3rd_port.py --manifest ports/zinogre.toml     --out tmp/zinogre_v10.bin
python tools/build_p3rd_port.py --manifest ports/brute_tigrex.toml --out tmp/brute_tigrex_em058.bin
```

Both need `workspace/extracted/` (your MHFU dump) and `workspace/extracted_mhp3/`
(your MHP3rd dump), produced by `tools/extract_iso.py`. The manifest build is
byte-identical to the documented flag soup it replaces — pinned by
`mhfu_monster_editor/tests/test_ports_build.py`, which returns early when the
extracts are absent.

---

## Category E — species action intel (`species/*.json`)

`species/emNN.json` is the host species' action table: every `(main, sub)` behaviour
pair its overlay dispatches, the handler address behind each one, the executor `a1`
animation ids it plays, what ENDS it (the clip, a cursor frame, or the `+0x414`
budget), and the literal `spawn_effect(id, bone, frame)` arguments its handlers
carry. All of that is **the game's own code and data, read out of `em*.ovl`** — the
same category as the disassembly listings in B, just in JSON — so it is gitignored
and never committed.

```bash
python tools/em_intel.py --all                      # all 17 -> species/em01.json ...
python tools/em_intel.py file_06108.bin             # just the Tigrex -> species/em75.json
```

It reads `workspace/extracted/data_files/` (your MHFU dump) and nothing else — no
emulator, no running game, ~4 s for all 17 overlays. The editor finds the result
through `mhfu_monster_editor.intel.find_intel(host_species)`; without it the
validator warns `INTEL_ABSENT` and keeps going, so a checkout that has never run the
command still works.

One field is **measured** rather than read: the per-pair dwell census from
`tools/em_state_census.py`, which needs a cold boot with the observe-only probe
deployed. Absent — which is the normal state — every pair's `measured` block is
`null` and the file says why. Attach one with:

```bash
python tools/em_intel.py file_06108.bin --log <framework.log> --census-species 75
```

---

## Why these are excluded

The wiki artwork is Capcom's, redistributed by the wiki under fan use; bundling
it in a code repository is a different act from a fan wiki hosting it. The
disassembly listings are the game's own code in disassembled form, the species
intel is that same code read into JSON, and the tables are its data copied
byte-for-byte. All of them are trivially reproducible
by anyone who owns the game, so excluding them costs contributors a single
command and keeps this repository free of material we have no right to ship.

The RE findings themselves — addresses, struct layouts, offsets, behaviour —
are facts about how the game works, documented throughout `docs/`, and are not
affected by any of this.
