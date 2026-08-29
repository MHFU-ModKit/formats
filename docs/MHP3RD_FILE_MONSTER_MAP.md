# MHP3rd big-monster file → species map (visually identified 2026-06-22)

Identified from headless model renders (`blender_mhfu/render_p3rd.py`) plus skeleton
bind-pose matching to the MHFU Tigrex skeleton (`file_06185`). (These renders were made
with the OLD v102 walker that over-expanded strips; the parser is now FIXED —
`pmo_p3rd.run_ge_v102`, see `docs/PMO_MODEL_FORMAT.md` — so re-renders are clean.) Renders +
texture atlases are in `tmp/mhp3rd_monster_renders/` (gitignored).

## ⚠️ These files IDENTIFY THEMSELVES — the renders were never needed (2026-08-29)

Every group opens with the species' AI overlay, and an `MWo3` header carries the
overlay's **name** at file offset 32. `file_05337` says `em040m0.ovl`, so the group is
em040 — an identification, not a guess. `tools/mhp3rd/em_groups.py` prints all 43 groups
(146 asset sets) in a second and agrees with the visual work below on every row it
overlaps: Zinogre = **em040** (`file_05339`), Brute Tigrex = **em058** (`file_05248`),
Green Nargacuga = **em059** (`file_05297`), Akantor = **em060**, Ukanlos = **em061**.

Two things the "5 consecutive files" rule below gets wrong, and both mis-assign files:

- **The overlay count is 2 or 4.** `m0`/`m1` load at `0x09DB3D80`/`0x09DE8C00`; some
  species also ship `m2`/`m3` at `0x09E1DA80`/`0x09E32500`. em010 has four.
  (MHFU has ONE such slot, `0x09D1A180` — worth remembering when reasoning about how
  many big monsters each engine was built to run.)
- **A family shares one overlay and repeats the asset triple.** em001 spans
  `file_05138..05145`: the overlays, then Rathian (`05140`) *and* Rathalos (`05143`).

**`file_05342`/`file_05343` are NOT the Zinogre's.** They are `em041m0`/`em041m1` — the
next monster's overlay pair, which is why they look like an unexplained identical-size
couple sitting just past his moveset. The Zinogre's group is exactly `file_05337..05341`
and contains **no effect/VFX file**; his effects are code in `em040m0.ovl`. See
`docs/EFFECTS_AND_VFX.md`.

## In-quest big-monster layout (per monster, 5 consecutive files)
⚠️ Superseded by the section above — true only for a single-variant, two-overlay species.
`[overlay MWo3][overlay2][model+skel PAC][GE-geometry raw][moveset raw .anim]`
- **model+skel PAC**: `pmo` + `0x80000000` skeleton (0x5C-stride compact) + `.TMH`
  textures (his real atlas). Geometry often in the adjacent GE-list companion file.
- **moveset**: raw `.anim`, the MHP3rd `0x64`-family format (decoded by
  `mhfu_model.anim.parse_p3rd`). Header: word1=size, table at size+4, len
  (first_anim-size-4)/4. Block→bone→channel→`<4h>` keyframe (identical to MHFU 0x64).
- The **anim file = model file + 2** (e.g. Brute model 05248 → anim 05250).

## Confirmed species (model file → monster)
| model file | anim file | monster | notes |
|---|---|---|---|
| **file_05248** | **file_05250** | **BRUTE TIGREX** | brown tiger-stripe + red eyes; skel matches MHFU Tigrex best (err 14.3, 46/48); moveset = 77 clips / 157,803 kf. **THE port target.** |
| file_05140 | file_05142 | Rathian | |
| file_05143 | file_05145 | Rathalos | |
| file_05148 | file_05150 | (bird wyvern — Qurupeco?) | "looks like a bird", not Tigrex |
| file_05153 | file_05155 | (new Khezu-like) | green body, pink wing membrane |
| file_05158 | file_05160 | Basarios | |
| file_05163 | file_05165 | Diablos | |
| file_05206 | file_05208 | Gold Rathian | |
| file_05221 | file_05223 | Silver Rathalos | |
| file_05229 | file_05231 | Black Diablos | |
| file_05253 | file_05255 | (an elder dragon) | large feathered/furred wings |
| **file_05339** | **file_05341** | **ZINOGRE** | teal body, gold spikes + fur mane, wolf-shaped; 51 bones / 4180 verts / 181 vgroups. **The no-similar-native port target** — MHFU has no Fanged Wyvern. Stream split `[33, 6, 7]`, needs bone reordering. |
| file_05354 | file_05356 | (a Fanged Beast — **Lagombi** most likely) | white/cream bear, broad flat head, big fore-claws; 31 bones / 2633 verts / 65 vgroups. Second no-similar-native candidate. Rendered with the correct texID→atlas mapping it is cream-white, not blue, which argues Lagombi over Arzuros — but the species is not pinned. |
| file_05275 | file_05277 | Popo | mammoth, curved tusks — a SMALL monster (MHFU has it too) |
| file_05282 | file_05284 | (Rhenoplos?) | small armoured quadruped, spiked head crest |
| file_05297 | file_05299 | Green Nargacuga | |
| file_05372 | file_05374 | (big sandfish — Nibelsnarf?) | |
| file_05388 | file_05390 | (red bird wyvern — Qurupeco subspecies?) | |
| file_05391 | file_05393 | (Khezu-like related) | purple/teal |
| file_05409 | file_05411 | (Tigrex?) | skel pairs with Brute 05248 at err 14.3 — likely regular Tigrex (subspecies pair); unrendered/unconfirmed |
| file_05412 | file_05414 | (pairs with Green Narga 05297, err 28.4) | likely the other Nargacuga or Barioth; unconfirmed |
| file_05417 | file_05419 | Akantor | black/orange spiky; NOT Tigrex (coincidental 48-bone skel match) |
| file_05422 | file_05424 | Ukanlos | white/ice; NOT Brute (coincidental rig match to Akantor) |

## Corrections to prior project assumptions
- **`file_04898` is NOT Brute Tigrex** — its atlas is lava/stone (Lavasioth-like). The
  whole earlier port used a wrong mesh + native Tigrex textures (which is why it only
  "looked Brute-ish"). The real Brute Tigrex is `file_05248`/`file_05250`.
- The "48-bone Tigrex-family" skeleton matches (Akantor `05417`, Ukanlos `05422`) were
  coincidental bone-count collisions; the bind-pose ranking (matched-joint avg error)
  is the reliable discriminator — Brute `05248` ranked #1.
