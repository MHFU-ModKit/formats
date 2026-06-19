# MHP3rd → MHFU Monster Port Candidates

**Status:** research compiled 2026-06-18 (branch `mhp3rd-monster-port`).
**Source game:** Monster Hunter Portable 3rd (MHP3rd, PSP, 2010, gen-3 engine).
**Target game:** Monster Hunter Freedom Unite / MHP2G (MHFU, PSP, 2008, gen-2 engine).

This file is the curated **set difference** — every LARGE monster in MHP3rd that is
NOT already in MHFU — ranked by porting suitability. It is the content backlog for the
MHP3rd-port effort. Pipeline + tooling tasks live in `tmp/mhp3rd_port_tasklist.md`.

## Why MHP3rd (vs other MH games)

Closest external source to MHFU by format lineage:
- Same hardware tier (PSP), same container/texture family (PAC / TMH).
- Model = **PMO `102`** (vs MHFU's PMO `1.0`) → needs a conversion pass, NOT a rewrite.
  Differences: per-mesh scaling (v102) vs single global scale (v1.0); different normal
  encoding ("Enforce Normals"); skeleton stores `id`+`ik chain` in MHFU but only `id`
  in P3rd; animation SCALE channel = SCALE_UP in P3rd.
- A reference v102 reader already exists in `tools/mhff/psp/pmo.py` (handles both
  `1.0\x00` and `102\x00`); `mhef` already supports `MHP3_JP = 6` for DATA.BIN/quest decrypt.

**Hard limit (applies to every candidate):** monster AI is compiled native MIPS in
per-monster overlays — NOT portable from any MH game. Every ported monster's behavior
must be **hand-scripted in the Lua AI layer** (it can reuse an existing MHFU AI species
as a baseline; see body-type analog column). The MHP3rd brain is not extractable.

## Gen-3 water risk

MHFU has **no underwater combat**. Gen-3 Leviathans / aquatic elders that fight in/under
water (Royal Ludroth, Agnaktor, Nibelsnarf-sand, Jhen Mohran-sand-sea, Amatsu-arena) are
the high-risk tail — land-phase-only ports lose their identity. Flagged TIER C.

---

## TIER A — port first (terrestrial, close to an existing MHFU chassis, no water)

| Monster | JP (romaji) | Class | MHFU body analog (AI baseline) | Notes |
|---|---|---|---|---|
| **Brute Tigrex** | Tigarekkusu Kishu | Flying Wyvern | **Tigrex (resident!)** | Rare Tigrex subspecies — skeleton+anim already in MHFU. Cheapest possible port (palette + behavior). |
| **Green Nargacuga** | Narugakuruga Kishu | Flying Wyvern | **Nargacuga (resident!)** | Rare Nargacuga subspecies — rig already in MHFU. Same story. |
| **Arzuros** | Aoashira | Fanged Beast | Congalala / Blangonga | Blue bear, simple quadruped. Excellent first NEW-model port. |
| **Lagombi** | Urukususu | Fanged Beast | Blangonga | Snow bear/rabbit; maps near-1:1 to Blangonga chassis. |
| **Great Wroggi** | Dosu Furogii | Bird Wyvern | Iodrome | Poison-spit alpha; ~1:1 to Iodrome body plan. |
| **Great Jaggi** | Dosu Jagii | Bird Wyvern | Velocidrome / Giadrome | Pack-leader raptor; same chassis as the *drome family. |
| **Great Baggi** | Dosu Bagii | Bird Wyvern | Velocidrome / Giadrome | Sleep-spit variant of Great Jaggi body. |
| **Zinogre** | Jin'ouga | Fanged Wyvern | Nargacuga | Wolf-thunder flagship; quadruped, charge mechanic, **fully land-based**. Marquee target. |
| **Volvidon** | Rangurotora | Fanged Beast | Congalala | Armadillo roller; roll = behavior hook, not a render/water problem. |
| **Barroth** | Boruboros | Brute Wyvern | Gravios / Diablos | Mud-roll desert brute; solid land base. |
| **Jade Barroth** | Boruboros Ashu | Brute Wyvern | Barroth (shares rig) | Snow subspecies; do after base Barroth. |
| **Steel Uragaan** | Uragankin Ashu | Brute Wyvern | Uragaan (shares rig) | Subspecies; do after base Uragaan. |
| **Sand Barioth** | Bareosu Ashu | Flying Wyvern | Barioth (shares rig) | Subspecies; do after base Barioth. |

## TIER B — moderate (terrestrial, novel rig or complex mechanic / large)

| Monster | JP (romaji) | Class | MHFU body analog | Notes |
|---|---|---|---|---|
| **Barioth** | Bareosu | Flying Wyvern | Tigrex | Agile quadruped wyvern; ice/wall-cling, no water. |
| **Uragaan** | Uragankin | Brute Wyvern | Gravios | Chin-ball roller, heavy chassis. |
| **Duramboros** | Doboruberuku | Brute Wyvern | Uragaan / Barroth | Club-tail spin; large rig. |
| **Deviljho** | Ibirujo | Brute Wyvern | Akantor | Apex invader; large complex rig; aggressive. Invasion = quest-injection concern. |
| **Alatreon** | Arubatorion | Elder Dragon | Teostra / Chameleos | Multi-element cycle; large, complex, land+air. |
| **Qurupeco** | Kurupekko | Bird Wyvern | Gypceros | Mimicry/monster-summon mechanic = novel behavior system. |
| **Crimson Qurupeco** | Kurupekko Ashu | Bird Wyvern | Qurupeco (shares rig) | Subspecies. |
| **Baleful Gigginox** | Giginebura Ashu | Leviathan | Gigginox (shares rig) | Subspecies; see base Gigginox arena note. |

## TIER C — hard / risky (water, sand-dive, siege, or extreme novelty)

| Monster | JP (romaji) | Class | Risk |
|---|---|---|---|
| **Royal Ludroth** | Roarudorosu | Leviathan | Aquatic; land-phase-only port loses identity. |
| **Purple Ludroth** | Roarudorosu Ashu | Leviathan | Subspecies; same water risk. |
| **Gigginox** | Giginebura | Leviathan | Ceiling-cling/electric; needs Khezu-style cave ceiling geometry (MHFU Khezu caves have it → arguably TIER B). |
| **Agnaktor** | Agunakotor | Leviathan | Lava-burrow emerge; strong terrain dependency. |
| **Glacial Agnaktor** | Agunakotor Ashu | Leviathan | Ice-burrow subspecies; same. |
| **Nibelsnarf** | Hapurubokka | Leviathan | Sand-swimmer; dive mechanic central to fight. |
| **Jhen Mohran** | Jien Moran | Elder Dragon | Sand-sea siege from a Dragonship; needs a new arena/infrastructure. Hardest. |
| **Amatsu** | Amatsumagatsuchi | Elder Dragon | Serpentine storm dragon; unique vertical arena + wind systems; extreme rig. |

---

## Recommended first target

**Zinogre** (TIER A, marquee) once the new-model pipeline is proven, but the **proving
run** should be the cheapest path:

1. **Proof-of-pipeline:** **Brute Tigrex** or **Green Nargacuga** — base rig already
   resident in MHFU, so it isolates the *injection + AI-scripting + quest-add* path
   from the *new-model conversion* path. Validate the whole live loop first.
2. **First true new-model port:** **Arzuros** (simplest novel rig, clean Congalala/
   Blangonga AI baseline) — exercises the full PMO v102→v1.0 converter.
3. **Flagship:** **Zinogre** — the headline deliverable.

## Open data gaps

- **MHP3rd PAC file indices per monster** are NOT publicly tabled (MHP3rd uses a
  different file numbering than MHFU's `file_06108` scheme). Must be derived by
  extracting MHP3rd DATA.BIN and identifying each em's model PAC (Task group **T1**).
- MHP3rd em-ID ↔ name map: derive from the extracted overlay/PAC set, not from web.

## Sources

MH Wiki (MHP3 / MHFU monster lists), LP Archive MHFU monster enumeration, Kiranico
MH3U, GameFAQs MHP3rd monster data (VioletKIRA), Kurogami2134 MHP3rd-Game-File-List.
Full citation set in the research thread that produced this file.
