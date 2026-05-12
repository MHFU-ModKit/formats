# DATA.BIN File Format Specification

## Overview

DATA.BIN is the main game archive containing all game assets for Monster Hunter PSP games. In MHP2G/MHFU, this file is **encrypted** and must be decrypted before modification.

## File Structure

```
+------------------+
| Header (4 bytes) |  <- TOC size indicator
+------------------+
| TOC (variable)   |  <- Table of Contents
+------------------+
| File Data        |  <- Packed files in 2048-byte blocks
+------------------+
```

### Header

| Offset | Size | Type   | Description |
|--------|------|--------|-------------|
| 0x00   | 4    | uint32 | TOC size multiplier (value * 2048 = TOC byte length) |

### Table of Contents (TOC)

The TOC is an array of 32-bit unsigned integers stored sequentially.

```python
# TOC interpretation
toc[i] = starting block position of file i (blocks are 2048 bytes)
toc[i+1] - toc[i] = number of blocks occupied by file i

# File count determination
file_count = index where toc[index] == (file_size // 2048)
```

### Extended Metadata

After the primary file index, additional TOC entries appear in pairs:
- `toc[i]` references a file index
- `toc[i+1]` stores associated data (typically actual file size for variable-length content)

## Block Alignment

All files are stored in **2048-byte aligned blocks**. This means:
- File at block N starts at byte offset `N * 2048`
- Files smaller than 2048 bytes still occupy one full block
- File sizes are padded to block boundaries

## Extraction Algorithm

```python
def extract_data_bin(data):
    # Read TOC size
    toc_size = struct.unpack('<I', data[0:4])[0] * 2048

    # Read TOC entries
    toc = []
    for i in range(4, toc_size, 4):
        toc.append(struct.unpack('<I', data[i:i+4])[0])

    # Find file count
    file_size_blocks = len(data) // 2048
    file_count = 0
    for i, entry in enumerate(toc):
        if entry >= file_size_blocks:
            file_count = i
            break

    # Extract files
    files = []
    for i in range(file_count):
        start_block = toc[i]
        end_block = toc[i + 1] if i + 1 < len(toc) else file_size_blocks

        start_byte = start_block * 2048
        end_byte = end_block * 2048

        files.append(data[start_byte:end_byte])

    return files
```

## Replacement Algorithm

When replacing files:
1. If new data requires more blocks, shift subsequent files backward
2. If fewer blocks needed, shift files forward
3. Update all TOC entries accordingly
4. Update extended metadata (actual file sizes)
5. Truncate file to new total size

## Encryption (MHP2G/MHFU)

DATA.BIN in MHP2G and MHFU is encrypted using a custom encryption scheme. Use the `mhef` library to decrypt/encrypt:

```python
from mhef.psp import DataCipher

# Decrypt
cipher = DataCipher(DataCipher.MHP2G)
decrypted = cipher.decrypt(encrypted_data)

# Encrypt
encrypted = cipher.encrypt(decrypted_data)
```

## Compression

Some files within DATA.BIN use **LZSS compression** with a 4KB sliding window:
- 1 word header with 16 words following
- Header contains 1-bit flags indicating literal vs window reference
- 11-bit length encoding, 5-bit offset encoding

## File Index

**Total files in MHFU EU**: 6,656 files

A complete file index is available at: `tools/FUComplete-Patch/data/index.csv`

### File Type Distribution (MHFU EU)

| Type | Count | Description |
|------|-------|-------------|
| .bin | ~6,300 | Various binary formats (see below) |
| .tmh | 58 | Standalone texture packages |
| .wav | 280 | Audio files |
| .pmf | 17 | Video files |

### Binary Format Signatures

| Magic | Format | Count | Description |
|-------|--------|-------|-------------|
| `pmo\0` | PMO | ~1 standalone | 3D models (most inside .pac) |
| `.TMH0.14` | TMH | 58+ | Texture packages |
| `Head ` | Head/Prog | 513 | Motion/animation tables |
| `HITS` | HITS | Many | Hitbox data (inside .pac) |
| `MWo3` | MWo3 | ~14 | Game overlay containers |
| `dbsT` | dbsT | 72 | Unknown (possibly debug/table data) |
| `03000000 20000000` | PAC | ~200 | Container archives |
| `06000000 40000000` | PAC | ~100 | Container archives (6 files) |

### Key File Ranges

| Index Range | Content |
|-------------|---------|
| 0-60 | System files, icons, modules |
| 61 | Player common motion table |
| 62-3376 | Player models, equipment |
| 3377-3387 | Weapon motion tables (w00-w10) |
| 5364-5368 | Additional motion tables |
| 6000-6038 | Stage/map packages |
| 6039-6042 | Effect packages |
| 6043-6059 | Monster overlays (AI code) |
| 6060-6148 | Monster model packages |
| 6149-6300+ | Monster sounds, other data |
| 6323-6324 | Monster motion tables (em04, em10 only) |

## References

- mhff library: https://github.com/svanheulen/mhff
- mhef library: https://github.com/svanheulen/mhef
- ZenHAX discussion: https://www.zenhax.com/viewtopic.php@t=2863.html
