# Quest File Format (.mib)

## Overview

Quest files in MHFU use the `.mib` extension and are stored encrypted in the game's DATA.BIN. Custom quests can also be stored in savedata.

## Encryption

Quest files use the same encryption as other MH data. Use mhef to decrypt:

```python
from mhef.psp import QuestCipher

cipher = QuestCipher(QuestCipher.MHP2G)
decrypted = cipher.decrypt(encrypted_quest)
```

## File Structure (Decrypted)

```
+------------------+
| Quest Header     |
+------------------+
| Monster Data     |
+------------------+
| Objective Data   |
+------------------+
| Reward Data      |
+------------------+
| Supply Box Items |
+------------------+
| Map Settings     |
+------------------+
| String Data      |
+------------------+
```

## Quest Header

| Offset | Size | Type | Description |
|--------|------|------|-------------|
| 0x00 | 4 | uint32 | Quest ID |
| 0x04 | 2 | uint16 | Quest type |
| 0x06 | 2 | uint16 | Quest star rating |
| 0x08 | 2 | uint16 | Time limit (minutes) |
| 0x0A | 2 | uint16 | Fee (zenny) |
| 0x0C | 4 | uint32 | Main reward zenny |
| 0x10 | 4 | uint32 | Sub reward zenny |
| 0x14 | 2 | uint16 | HR requirement |
| 0x16 | 2 | uint16 | Map ID |
| 0x18 | 1 | uint8 | Max players |
| 0x19 | 1 | uint8 | Join restriction |

## Quest Types

| Value | Type |
|-------|------|
| 0x00 | Hunt |
| 0x01 | Capture |
| 0x02 | Kill |
| 0x03 | Deliver |
| 0x04 | Special |
| 0x05 | Training |

## Monster Data Section

Each monster spawn definition:

| Offset | Size | Type | Description |
|--------|------|------|-------------|
| 0x00 | 2 | uint16 | Monster ID |
| 0x02 | 2 | uint16 | Spawn area |
| 0x04 | 2 | uint16 | HP modifier (%) |
| 0x06 | 2 | uint16 | Attack modifier (%) |
| 0x08 | 2 | uint16 | Defense modifier (%) |
| 0x0A | 2 | uint16 | Size modifier |
| 0x0C | 4 | uint32 | Special flags |

## Objective Data

### Main Objective

| Offset | Size | Type | Description |
|--------|------|------|-------------|
| 0x00 | 2 | uint16 | Objective type |
| 0x02 | 2 | uint16 | Target ID |
| 0x04 | 2 | uint16 | Required count |

### Sub Objective

Same structure as main objective.

## Objective Types

| Value | Type | Description |
|-------|------|-------------|
| 0x01 | Hunt | Slay target monster |
| 0x02 | Capture | Capture target monster |
| 0x03 | Hunt All | Slay all large monsters |
| 0x04 | Deliver | Deliver item to red box |
| 0x05 | Break Part | Break specific monster part |
| 0x06 | Mount | Mount monster X times |

## Reward Tables

### Fixed Rewards

Always given on quest completion:

```
Entry:
  - uint16: Item ID
  - uint16: Quantity
  - uint8: Percentage (100 = guaranteed)
```

### Random Rewards

Lottery-style reward pool:

```
Entry:
  - uint16: Item ID
  - uint16: Quantity
  - uint8: Weight (higher = more likely)
```

## Supply Box Items

Starting items provided in blue box:

```
Entry:
  - uint16: Item ID
  - uint16: Quantity
```

## Map Settings

| Offset | Size | Type | Description |
|--------|------|------|-------------|
| 0x00 | 2 | uint16 | Map ID |
| 0x02 | 2 | uint16 | Starting area |
| 0x04 | 2 | uint16 | Base camp area |
| 0x06 | 1 | uint8 | Day/Night flag |
| 0x07 | 1 | uint8 | Weather |

## Map IDs

| ID | Map Name |
|----|----------|
| 0x00 | Forest and Hills |
| 0x01 | Jungle |
| 0x02 | Desert |
| 0x03 | Swamp |
| 0x04 | Volcano |
| 0x05 | Snowy Mountains |
| 0x06 | Tower |
| 0x07 | Old Jungle |
| 0x08 | Old Desert |
| 0x09 | Old Swamp |
| 0x0A | Old Volcano |
| 0x0B | Great Forest |
| 0x0C | Arena |
| 0x0D | Fortress |
| 0x0E | Town |
| 0x0F | Battleground |

## String Data

Quest strings are stored at the end of the file:
- Quest name
- Quest description
- Client name
- Success conditions
- Failure conditions

Strings use shift-JIS encoding (Japanese) or ASCII (localized).

## FUComplete Quest Injection

FUComplete allows injecting up to 18 custom quests via savedata:
1. Decrypt quest file
2. Convert to .mib format if needed
3. Use FUCTool to inject into save
4. Toggle custom quests in-game

## Quest Editor Tools

- Legacy: MHFU Quest Editor (SourceForge, 2014)
- Modern: FUCTool quest tab
- Custom: Direct binary editing

## References

- mhef quest cipher: https://github.com/svanheulen/mhef
- FUCTool: https://github.com/FUComplete/FUCTool
- Quest editor: https://sourceforge.net/projects/mhfuquesteditor/
