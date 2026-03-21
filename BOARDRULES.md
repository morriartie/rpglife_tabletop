### OVERWORLD: RULE SHEET v1.0

#### 1. GAME SETUP
1.  **Determine Player Count (N):** Gather all players.
2.  **Generate Cities:** A number of cities are generated on the map.
    - **Formula:** `CITIES = N + |N * (2/3)|` (Rounded to the nearest whole number).
    - *Example: With 4 players, you generate 4 + |2.66| = 7 Cities.*
3.  **Generate Roads:** One city acts as the primary hub. All other cities branch out from it or other connected cities to form a web. A few extra cross-roads are added to create traversal loops.
4.  **Divide Roads:** The path between two connected cities is divided into a number of spaces called **Tiles**.
    - The number of tiles per road is randomized (typically 2 to 5), representing different travel distances.
5.  **Assign Biomes:** Each Tile inherits its Biome from the nearest city.
6.  **Populate Encounters:** For each Road, create a specific "Encounter Roster."
    - This roster is a subset of the "Encounters by Biome" list.
    - The "Encounters by Biome" list is itself a subset of the game's total bestiary.
7.  **Player Starts:** Each player is randomly assigned a unique starting city. No two players start in the same city.
8.  **City Bounties:** Place fixed reward tokens on each city. The first player to reach that city claims the reward.

#### 2. THE PLAYER MAT
This represents your character's inventory and combat readiness.

- **Equipment List:** A list of your equipped gear.
    - *Gear Rule:* Each piece of equipment has **two dice** associated with it. These are pre-defined on the item card (e.g., a Sword might have [Attack D8] and [Attack D6]).
- **Dice Pool:** This area is empty at the start of the game. It fills up during combat.
- **Bag:** A storage area for items that are not currently equipped (consumables, quest items, etc.).

#### 3. COMBAT - THE DICE POOL
Combat uses a "First-In, First-Out" (FIFO) system.

1.  **Building the Pool:** At the start of combat, each combatant secretly chooses **1 die from each of their equipped items** and places them into their personal Dice Pool in any order.
2.  **Resolution:** The dice at the *front* of the pool are rolled and resolved first.
3.  **Single-Use Rule:** Dice with the `[SingleUse]` keyword are returned to their original equipment **after being used** and cannot be used again in this combat.
4.  **Persistent Dice:** All other dice remain in the pool. After the first set resolves, the next dice in line move to the front and are rolled on the following turn.
5.  **Temporary Effects:** Any effects or modifiers granted by a die last only until the end of the current combat.

#### 4. TURN STRUCTURE
Each player's turn is divided into the following phases:

**1. Movement Phase**
- Declare a direction you wish to travel along the roads.
- Roll 2d6.
- You may choose to use the result of **either** of the two dice for your movement.
- Move your token that many tiles in your chosen direction.

**2. Tile Resolution Phase**
- Resolve the effect of the tile you landed on.
- This could be: an Encounter, discovering a City Reward, finding a hidden item, or a special event.

**3. Combat Phase (If applicable)**
- This phase begins if an encounter is triggered or if you land on a space with another player.
- **Initiative:**
    1.  Compare the number of dice with the `[Initiative]` keyword in each combatant's pool.
    2.  The combatant with the most `[Initiative]` dice acts first this turn.
    3.  **Tie:** If the number is equal, the player with the *fewer* total dice in their pool starts.
    4.  **Double Tie:** If the total dice count is also equal, initiative is determined randomly (e.g., a die roll).
- Combat then proceeds by resolving the Dice Pools as described in Section 3.

**4. Reward Phase (Combat Only)**
- The winner of the combat (player or monster) rolls on the defeated foe's loot table to determine the reward.

**5. Punishment Phase (Combat Only)**
- The loser of the combat suffers a consequence.
- *Player Consequence:* The defeated player loses their **next turn**.

#### 5. WINNING THE GAME
The game has a two-stage victory condition.

1.  **The Final Hour:** When a predetermined turn number (Turn X) is reached, the game enters its final chapter.
2.  **The Boss Fight:** A final Boss monster is randomly selected. All surviving players must cooperate to fight it as a group.
3.  **The Duel:** After the Boss is defeated, the alliance ends. The surviving players immediately enter a free-for-all Player-vs-Player combat.
4.  **Victory:** The last player standing after the final duel is the winner of *Overworld*.
