# TMH Texture Format Specification

## Overview

TMH is the texture package used by the Monster Hunter PSP games: a flat list of images,
each carrying its own pixel data and (almost always) its own palette. It is the `.TMH`
sub-resource of a monster PAC and `sub[1]` of a stage PAC.

⚠️ **This spec was rewritten 2026-09-13 against a codec that round-trips the whole game.**
The earlier version described the container from the general shape of the mhff reader and
had the **image header, the pixel header, the CLUT entry format and the swizzle block size
all wrong**. Every field below is now measured over **4 294 banks / 10 025 images — every
TMH in the extracted game — with zero walk failures**, and the layout is what
`mhfu_model/tmh.py` reads *and writes*. Where a field is constant across all 10 025, that
is said explicitly rather than called "unknown".

🟢 **It is writable, and a stage's bank is writable at RUNTIME** — see §Writing back and
`docs/STAGE_MAP_FORMAT.md` §4e.

## File structure

Everything is contiguous; there is no offset table and no padding. The walk below must
land exactly on the end of the blob, and `parse_tmh` raises if it does not — a partial
walk is how a same-size edit lands on the wrong image.

```
  bank header    16 bytes
  image 0 ──┬──  image header   16 bytes
            ├──  pixel header   16 bytes
            ├──  pixel data     (pixel header[0] - 16) bytes, PSP-swizzled
            ├──  CLUT header    16 bytes      ] only when image header[3] == 1
            └──  CLUT data      (CLUT header[0] - 16) bytes ]
  image 1 ──...
```

## Bank header (16 bytes)

| Offset | Size | Value | Description |
|--------|------|-------|-------------|
| 0x00 | 8 | `".TMH0.14"` | signature |
| 0x08 | 4 | u32 | **image count** |
| 0x0C | 4 | u32 | **0** in all 4 294 banks |

⚠️ The previous spec had 0x08 and 0x0C the other way round. 0x08 is the count.

## Image header (16 bytes)

| Offset | Size | Value | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | u32 | **size of this whole image entry**, including these 16 bytes — pixel header + pixel data + CLUT header + CLUT data. Verified 10 025/10 025 |
| 0x04 | 4 | **0** | constant across the game |
| 0x08 | 4 | **1** | constant across the game |
| 0x0C | 4 | 0 or 1 | **1 = CLUT-indexed** (a CLUT header follows the pixel data). Matches the pixel mode's need for a palette 10 025/10 025 |

⚠️ This is **not** width/height — the previous spec said it was. Dimensions live in the
pixel header. For a 128×128 4bpp image, `[0]` reads `0x2070` (8 304 = 16 + 16 + 8 192 + 16 + 64).

## Pixel header (16 bytes)

| Offset | Size | Value | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | u32 | **pixel data size, including these 16 bytes**. Verified 10 025/10 025 |
| 0x04 | 4 | **1** | constant across the game |
| 0x08 | 4 | u32 | **pixel format mode** |
| 0x0C | 2 | u16 | **width** |
| 0x0E | 2 | u16 | **height** |

⚠️ The previous spec had mode and size swapped, and read width/height as u32 "block
width/height". They are u16 image dimensions, packed as `<3I2H>`.

## CLUT header (16 bytes) — present only when image header `[0x0C] == 1`

Not documented at all in the previous spec.

| Offset | Size | Value | Description |
|--------|------|-------|-------------|
| 0x00 | 4 | u32 | **CLUT data size, including these 16 bytes**. Verified 10 024/10 024 indexed images |
| 0x04 | 4 | **2** | constant across the game |
| 0x08 | 4 | u32 | **CLUT pixel mode** — the same enum as the pixel mode, applied to palette entries |
| 0x0C | 4 | u32 | **entry count** (16 for a 4bpp image, 256 for 8bpp) |

🔴 **A CLUT is NOT always RGBA8888** — the previous spec asserted it was. Both formats are
common, roughly half the game each:

| CLUT mode | entry format | bytes/entry | count in the game |
|---|---|---|---|
| 1 | RGBA5551 | 2 | 5 113 |
| 3 | RGBA8888 | 4 | 4 911 |

A writer that assumes 8888 produces a CLUT of the wrong length for half the images.

## Pixel format modes

The enum is the PSP GE texture-format enum:

| Mode | Format | Bits/pixel | Used in MHFU? |
|------|--------|-----------|---------------|
| 0 | RGB565 | 16 | never as pixels |
| 1 | RGBA5551 | 16 | **CLUT only** (5 113 palettes) |
| 2 | RGBA4444 | 16 | never |
| 3 | RGBA8888 | 32 | **1 image**, and 4 911 palettes |
| 4 | Indexed4 | 4 | **4 621 images** |
| 5 | Indexed8 | 8 | **5 403 images** |
| 6 | (16-bit) | 16 | never |
| 7 | (32-bit) | 32 | never |
| 8 | DXT1 | 4 | never |
| 9 | DXT3 | 8 | never |
| 10 | DXT5 | 8 | never |

🟢 **Essentially every texture in the game is palettised.** Of 10 025 images, **10 024 are
CLUT-indexed** (mode 4 or 5); the single exception is `file_06143` image 0, a 128×128
direct RGBA8888. That is the fact that makes texture replacement tractable: byte size is
fixed by `(mode, width, height)` alone, so a **same-dimension replacement is automatically
size-identical**, which is exactly what a resident sub-resource demands.

⚠️ **DXT never appears.** The DXT1 decoder in `tmh.py` (mode 8) and the "DXT3/DXT5 not
implemented" caveat are both dead weight for MHFU — kept only because MHP3rd assets flow
through the same reader. Do not treat DXT support as a gap.

Modes 6 and 7 are labelled "Grayscale4/Grayscale8" in older notes; the decoder in fact
treats them as 16- and 32-bit direct formats. Neither occurs, so the label is untested
either way and nothing should be built on it.

## Pixel block storage (swizzling)

PSP textures are stored in blocks for GPU efficiency. The block is always **16 bytes wide
by 8 rows**, so its size *in pixels* falls out of the bit depth:

| Mode | bits/pixel | block, in pixels |
|---|---|---|
| 0, 1, 2, 6 | 16 | 8 × 8 |
| 3, 7 | 32 | 4 × 8 |
| 4 | 4 | **32 × 8** |
| 5 | 8 | **16 × 8** |
| 8, 9, 10 | DXT | 4 × 4 |

⚠️ The previous spec said "standard formats (0–7): 8×8 pixel blocks" for all of them. That
is right only for the 16-bit modes and wrong for the two that the game actually uses —
a 4bpp block is 32 pixels wide, an 8bpp block 16.

The mapping is a pure permutation of pixel indices, so one function serves both directions
(`_perm` in `tmh.py`, with `_deblock` reading and `_swizzle_idx` writing):

```python
def _perm(mode, width, n):
    """For each LINEAR pixel index, its index in the file's block order."""
    bw, bh = _BW[mode], _BH[mode]
    for i in range(n):
        x, y = i % width, i // width
        xb, x = x // bw, x % bw
        yb, y = y // bh, y % bh
        yield bw * bh * xb + width * bh * yb + bw * y + x
```

Deblocking is `out[i] = data[perm[i]]`; swizzling is `out[perm[i]] = data[i]`.

## Reading

```python
from mhfu_model.tmh import decode_tmh, parse_tmh

for tex in decode_tmh(blob):          # pixels: {index, width, height, rgba}
    ...                               # rgba = W*H*4 bytes, row 0 = TOP
for img in parse_tmh(blob):           # structure: byte offsets, raises on a short walk
    img.pix_off, img.clut_off, img.mode, img.clut_entries
```

CLUT expansion happens **before** deblocking (indices are expanded to RGBA, then the u32
pixels are permuted); either order gives the same result.

## Writing back

`encode_into(blob, index, rgba, palette=None)` replaces one image and returns a blob of
**exactly the same length**: quantise → swizzle → pack → splice. Dimensions and pixel mode
belong to the header and are not negotiable, so a replacement is resized to the slot and
requantised to its palette (16 or 256 colours). Pass `palette=` to keep the shipped one and
only re-map onto it.

`quantize(rgba, n)` is a weighted median cut over the *distinct* colours, so a texture that
is mostly one flat colour does not spend half its palette on it.

### The oracle

The check that says the swizzle and the bit packing are right rather than merely plausible
is offline and total: **decode every shipped image, re-encode it with its own palette, and
demand the original bytes back.**

| corpus | images | byte-identical | pixel-identical | failed |
|---|---|---|---|---|
| all 246 stage banks | 4 718 | 4 476 | **4 718 (100 %)** | 0 |
| monster PACs (`file_06060`–`file_06159`) | 1 383 indexed | 1 298 | **1 383 (100 %)** | 0 |

The images that differ in bytes but not pixels are those whose palette holds the same
colour twice, where colour-matching legitimately picks the first index. Run it with
`python tools/stage_tex.py verify`.

## Runtime: a stage's bank is editable live

🟢 The GE reads a stage's `sub[1]` **in place, out of the resident PAC, every frame** — no
pointer fixup, no copy. A texture edit lands on the next frame with no area reload and no
loader breakpoint, and writing the shipped bytes back undoes it just as fast. The CLUT and
the pixel data are independently live, so a 64-byte CLUT write is the cheapest visible
change available. 🔴 It is lost on an area transition (the PAC is re-read from the ISO).

Full detail, including why the bank cannot grow and why an import must *spend* one of the
stage's existing slots: `docs/STAGE_MAP_FORMAT.md` §4e. Tooling: `tools/stage_tex.py`.

## MHP3rd ↔ MHFU compatibility (2026-06-22)

**MHP3rd `.TMH` is byte-format-identical to MHFU `.TMH`** — same `.TMH0.14` header and
texture-table layout (verified: the Brute `file_05248` sub2 and the native Tigrex
`file_06185` sub2 both decode to 5 textures of identical dimensions). So a ported MHP3rd
monster's own texture atlas can be **spliced directly** into an MHFU host PAC's TMH slot
with no conversion — exactly what the porter (`port_p3rd.port_monster`) does (the Brute keeps
his own brown tiger-stripe atlas in-game). `mhfu_model/tmh.py::decode_tmh` decodes both.

## Known limitations

1. **DXT3/DXT5 decompression is not implemented** — and no MHFU texture uses any DXT mode,
   so this is not a gap for this game. DXT1 (mode 8) decodes.
2. **`encode_into` writes CLUT-indexed images only** (modes 4 and 5). That covers 10 024 of
   the game's 10 025 images; the one direct-RGBA8888 image is refused rather than guessed at.
3. **CLUT modes 0/1/2 are lossy on write** for colours that did not come from such a palette
   to begin with — they are 16-bit formats. Mode 3 is exact.
4. An image cannot change dimensions or pixel mode, because a resident sub-resource cannot
   change size.

## Tooling

```bash
python tools/stage_tex.py list 98             # a stage's bank + what each slot costs
python tools/stage_tex.py export 98 --out t/  # every image as a PNG
python tools/stage_tex.py verify              # the round-trip oracle, all 246 stage banks
python -m mhff.psp.tmh extract input.tmh out/ # the external reference reader (gitignored)
```

## References

- mhff TMH parser: https://github.com/svanheulen/mhff/blob/master/psp/tmh.py
- PSP GE texture formats: https://www.psdevwiki.com/psp/GE
