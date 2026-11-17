# Enchant QoL — enchanting table datapack (26.2)

Server-side datapack for Minecraft **26.2**. No mod, no resource pack: it only edits
`data/minecraft/enchantment/*.json` and the `#minecraft:in_enchanting_table` tag, which live entirely on the
server. Vanilla clients need nothing.

Ready-to-use file: `build/enchant-qol-1.0.0.zip` (see Releases) → drop into `<world>/datapacks/`.
Datapacks from that folder are picked up **only when the server starts** — `/reload` does not rescan the folder.

## What it changes

1. **Treasure enchantments reach the table.** The vanilla `in_enchanting_table` tag is exactly
   `#minecraft:non_treasure`, so Mending, Frost Walker, Soul Speed, Swift Sneak and Wind Burst could never be
   rolled. Now they can. Curses are deliberately **not** added, although they are treasure too.
2. **Top levels become reachable at level 30.** The table cap is hardcoded: 15 bookshelves → power 30
   (`EnchantmentHelper.getEnchantmentCost`, `if (bookshelves > 15) bookshelves = 15`) and no datapack can raise
   it. What a datapack can do is lower an enchantment's `min_cost` so its maximum level fits into the 30–38
   power range.
3. **Quick Charge III is fixed.** In vanilla `min_cost` (52) is greater than `max_cost` (50), so the third level
   could never be rolled at all.
4. **Mending is more common.** `weight` 2 → 8, so a Mending book shows up in a dozen rolls instead of a hundred.

## Exact `min_cost` edits (base, per_level_above_first)

| enchantment | before | after | min_cost at max level |
|---|---|---|---|
| sharpness | 1, 11 | 6, 7 | 45 → 34 |
| smite | 1, 9 | 6, 7 | 37 → 34 |
| bane_of_arthropods | 1, 9 | 6, 7 | 37 → 34 |
| efficiency | 1, 10 | 1, 8 | 41 → 33 |
| power | 1, 10 | 1, 8 | 41 → 33 |
| quick_charge | 12, 20 | 12, 6 | 52 (min > max, never rolled) → 24 |
| thorns | 10, 20 | 10, 10 | 50 → 30 |
| swift_sneak | 25, 25 | 15, 9 | 75 → 33 |
| mending | 25, 25 | 20, 0 | 25 → 20 (also reachable from the 2nd button) |

## Measured odds

Simulation of the vanilla algorithm (20 000 rolls, 15 bookshelves), replicated from the bytecode of
`EnchantmentHelper.getEnchantmentCost` / `selectEnchantment` / `getAvailableEnchantmentResults` in
`server-26.2.jar`:

| what | before | after |
|---|---|---|
| Mending on a diamond pickaxe (3rd button) | 10.2 % | 31.7 % |
| Mending on a diamond chestplate | 8.1 % | 26.4 % |
| Mending on a diamond sword | 5.3 % | 18.3 % |
| Mending book (3rd button) | 1.3 % | 5.5 % |
| Efficiency V on a pickaxe | 0.3 % | 27.6 % |
| Sharpness V on a sword | 0 % | 12.7 % |
| Quick Charge III book | 0 % | 3.7 % |
| Swift Sneak III book | 0 % | 0.2 % |

## Rebuild / retune

`build.py` reads the vanilla `data/minecraft/enchantment/*.json` straight out of the 26.2 server jar, patches
the fields listed above, writes the pack next to the script and zips it, then prints a before/after table.

```
MC_SERVER_JAR=/path/to/server-26.2.jar python3 build.py
```

Tweak `COST_PATCH`, `WEIGHT_PATCH` and `TREASURE_IN_TABLE` at the top of the script.

## 26.2 gotchas (verified)

- `pack.mcmeta` must **not** contain `supported_formats`: the server logs
  `Pack key supported_formats is deprecated starting from pack format 82` and falls back to the legacy reader.
  Correct form: `"min_format": [107, 0]`, `"max_format": [108, 0]`, `"pack_format": 107`.
- A datapack in `<world>/datapacks` does not appear after `/reload` — restart the server.
- The pack must live in the `datapacks` folder of the **level name** from `server.properties`.
- A datapack overwrites an enchantment file **whole** — the pack carries full copies of the vanilla JSONs.

## What a datapack cannot do

Raise the power cap above 30 (bookshelves beyond 15), reroll offers for free, guarantee a "useful" slot, or add
any custom screen — that needs a mixin or a client mod.

## License

MIT.
