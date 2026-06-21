# MHP3rd big-monster file → species map (visually identified 2026-06-22)

Identified from headless model renders (`blender_mhfu/render_p3rd.py`, geometry is a bit
noisy — the v102 strip parser over-expands — but colour + silhouette are clear) plus
skeleton bind-pose matching to the MHFU Tigrex skeleton (`file_06185`). Renders +
texture atlases are in `tmp/mhp3rd_monster_renders/` (gitignored).

## In-quest big-monster layout (per monster, 5 consecutive files)
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
