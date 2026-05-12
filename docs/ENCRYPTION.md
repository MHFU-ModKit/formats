# Monster Hunter PSP Encryption

## Overview

Monster Hunter PSP games (MHP2G, MHFU, MHP3rd) use encryption on various data files. The `mhef` (Monster Hunter Encryption Functions) library provides tools to decrypt and encrypt these files.

## Encrypted File Types

| File Type | Description | Encryption |
|-----------|-------------|------------|
| DATA.BIN | Main game archive | Data cipher |
| Quest files (.mib) | Quest definitions | Quest cipher |
| Save data | Player saves | Save cipher |
| DLC files | Downloaded content | DLC cipher |

## Data Cipher (DATA.BIN)

Used for the main DATA.BIN archive:

```python
from mhef.psp import DataCipher

# Game-specific cipher
cipher = DataCipher(DataCipher.MHP2G)  # For MHFU/MHP2G
# cipher = DataCipher(DataCipher.MHP3)  # For MHP3rd

# Decrypt
with open('DATA.BIN', 'rb') as f:
    encrypted = f.read()
decrypted = cipher.decrypt(encrypted)

# Encrypt
encrypted = cipher.encrypt(decrypted)
```

## Quest Cipher

Used for quest/mission files:

```python
from mhef.psp import QuestCipher

cipher = QuestCipher(QuestCipher.MHP2G)

# Decrypt quest file
decrypted = cipher.decrypt(encrypted_quest)

# Encrypt quest file
encrypted = cipher.encrypt(decrypted_quest)
```

## Save Cipher

Used for save game data:

```python
from mhef.psp import SaveCipher

cipher = SaveCipher(SaveCipher.MHP2G)

# Decrypt save
decrypted = cipher.decrypt(encrypted_save)

# Encrypt save
encrypted = cipher.encrypt(decrypted_save)
```

## DLC Cipher

Used for downloaded content:

```python
from mhef.psp import DLCCipher

cipher = DLCCipher(DLCCipher.MHP2G)

# Decrypt DLC
decrypted = cipher.decrypt(encrypted_dlc)

# Encrypt DLC
encrypted = cipher.encrypt(decrypted_dlc)
```

## Cipher Implementations

### Technical Details

The encryption uses a combination of:
- XOR operations with key tables
- Byte shuffling/permutation
- Block-based processing

The key tables are derived from game-specific seeds and vary by:
- Game version (MHP2G vs MHP3)
- File type (data vs quest vs save)
- Region (JP vs NA vs EU)

### Key Table Generation

```python
# Pseudocode for key table generation
def generate_key_table(seed, size):
    table = bytearray(size)
    state = seed

    for i in range(size):
        state = (state * MULTIPLIER + INCREMENT) & 0xFFFFFFFF
        table[i] = (state >> 16) & 0xFF

    return table
```

## Region Differences

Different game regions may use different encryption keys:

| Game | Region | Notes |
|------|--------|-------|
| MHP2G | JP | Original Japanese release |
| MHFU | NA | North American release |
| MHFU | EU | European release |

FUComplete handles cross-region saves by supporting all key variants.

## Command Line Usage

mhef includes command-line tools:

```bash
# Decrypt DATA.BIN
python -m mhef.psp.data decrypt MHP2G DATA.BIN DATA_decrypted.BIN

# Encrypt DATA.BIN
python -m mhef.psp.data encrypt MHP2G DATA_decrypted.BIN DATA.BIN

# Decrypt quest
python -m mhef.psp.quest decrypt MHP2G quest.mib quest_decrypted.mib
```

## Integration with Other Tools

### FUComplete Workflow

1. Extract ISO to get DATA.BIN
2. Decrypt DATA.BIN using mhef
3. Modify files
4. Re-encrypt DATA.BIN
5. Replace in ISO

### UMD-Replace

Used after encryption to replace DATA.BIN in the ISO without full rebuild.

## Dependencies

mhef requires:
- Python 3.x
- PyCrypto or PyCryptodome

```bash
pip install pycryptodome
pip install mhef
```

## References

- mhef library: https://github.com/svanheulen/mhef
- GitLab mirror: https://gitlab.com/svanheulen/mhef
