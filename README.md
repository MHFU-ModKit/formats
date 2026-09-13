<p align="center">
  <img src="misc/banner.svg" width="720" alt="MHFU-FORMATS">
</p>

# MHFU ModKit — formats

The Monster Hunter Freedom Unite file formats as a Python library, the tools that get the files
out of your own copy of the game, and the MHP3rd→MHFU monster porter.

- **`tools/mhfu_model/`** — PMO models, PAC archives, skeletons, animations (both the on-disk and
  the in-game recursive form), TMH textures. Parses and re-encodes **byte-identically** on all 49
  big-monster PACs; a constraint validator knows the engine's rules; encoders for skeleton,
  animation, geometry and **texture** edits; a topology-grow encoder that adds vertices and
  faces. The TMH codec round-trips **every texture in the game** — 10 025 images across
  4 294 banks — which is what lets an image be replaced in a bank at exactly its own size.
- **`tools/extract_iso.py`** — dumps and decrypts `DATA.BIN` from your ISO (via `mhef`/`mhff`).
- **The porter** — `build_p3rd_port.py` and friends: MHP3rd geometry, textures, skeleton and
  full moveset onto an MHFU-loadable PAC, with `verify_port.py` / `port_anim_verify.py`
  checking the motion joint for joint against the source.
- **`docs/`** — the format specifications, written while decoding them.

## Setup

```bash
git clone https://github.com/MHFU-ModKit/formats.git
cd formats
tools/setup.sh                    # venv, requirements, clones mhef + mhff next to the tools
source venv/bin/activate
python tools/extract_iso.py workspace/iso/game.iso workspace/extracted/     # your own dump
python -m mhfu_model.validate workspace/extracted/data_files/file_06185.bin
```

Run the library with `PYTHONPATH=tools` (or from a checkout that has `tools/` on the path — the
editor and the Blender addon both do). [`tools/mhfu_model/README.md`](tools/mhfu_model/README.md)
is the library guide; [`docs/ASSETS.md`](docs/ASSETS.md) explains every generated file and how to
reproduce it.

## Documentation

[`PMO_MODEL_FORMAT`](docs/PMO_MODEL_FORMAT.md) · [`ANIMATION_FORMAT`](docs/ANIMATION_FORMAT.md) ·
[`TMH_TEXTURE_FORMAT`](docs/TMH_TEXTURE_FORMAT.md) · [`DATA_BIN_FORMAT`](docs/DATA_BIN_FORMAT.md) ·
[`QUEST_FORMAT`](docs/QUEST_FORMAT.md) · [`ENCRYPTION`](docs/ENCRYPTION.md) ·
[`MHP3RD_FILE_MAP`](docs/MHP3RD_FILE_MAP.md) · [`BRUTE_TIGREX_PORT`](docs/BRUTE_TIGREX_PORT.md)
(the porter, end to end) · [`MONSTER_PORT_SKINNING_PLAN`](docs/MONSTER_PORT_SKINNING_PLAN.md).
These were written alongside the reverse engineering and refer to tooling that lives in the
upstream research repository; where a path does not exist here, that is why.

## No game data is included

This repository contains **no game files, no extracted assets, no artwork** — not the ISO, not
decrypted archives, not models or textures, not dumped tables. All of it is gitignored and is
reproduced from your own legally obtained copy of the game (see the `formats` repo's
`docs/ASSETS.md`). Everything targets **MHFU EU (ULES01213)**; addresses will not line up with a
JP or NA build.

## About this repository

`formats` is one of the [MHFU-ModKit](https://github.com/MHFU-ModKit) repositories. They are cut
from one upstream research repository and re-published from it, so they move in lockstep — a
file that appears in two of them is the same file at the same commit. Pull requests are welcome
here; an accepted one is applied upstream and comes back in the next export, which is why
`main` only takes changes through PRs. Issues are welcome for bugs, questions and findings alike.

The siblings:

- [`framework`](https://github.com/MHFU-ModKit/framework) — the runtime mod framework: one PRX, many mods, hot-reloaded Lua
- [`example-mods`](https://github.com/MHFU-ModKit/example-mods) — Lua mods and port manifests to learn from and drop on a memory stick
- [`monster-editor`](https://github.com/MHFU-ModKit/monster-editor) — the desktop editor for ported monsters
- [`hud`](https://github.com/MHFU-ModKit/hud) — a live read-only HUD and AI editor over the PPSSPP debugger
- [`blender-addon`](https://github.com/MHFU-ModKit/blender-addon) — import, edit and export big monsters in Blender

## License

[MIT](LICENSE). Not affiliated with or endorsed by Capcom. Monster Hunter is a trademark of
Capcom Co., Ltd.

## Credits

[mhff](https://github.com/svanheulen/mhff) and [mhef](https://github.com/svanheulen/mhef) by
svanheulen are the foundation of the extraction; [tclamb/mhp2g-decomp](https://github.com/tclamb/mhp2g-decomp)
confirmed several struct layouts.
