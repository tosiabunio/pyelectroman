"""
Generate test level for weapon testing.

This script creates a test level that uses the ORIGINAL elek1/elek2 sprite sets
without modification, so sprites behave exactly as they do in the real game.

The level spans two screens horizontally with:
- Floor and walls from elek1
- Shootable objects from elek2 (sprites that already have shootable flag)
- A checkpoint at the start

Run this script once to generate test.ebl, then use Shift+9 in game to load.
Use Shift+1 through Shift+5 to set weapon power level for testing.
"""

import json
import os


def create_test_level():
    """Create the test level file using original elek1/elek2 sprites."""
    data_dir = os.path.join(os.path.dirname(__file__), "data")

    # Level structure - uses original elek1 and elek2 sprite sets
    level = {
        "names": ["elek1", "elek2"],
        "screens": [None] * 256
    }

    # Create two connected screens (17 and 18, horizontally adjacent)
    # Screen 17 is at grid position (1, 1) - left screen
    # Screen 18 is at grid position (2, 1) - right screen (17 + 1)
    level["screens"][17] = create_screen_left()
    level["screens"][18] = create_screen_right()

    # Save level file
    level_path = os.path.join(data_dir, "test.ebl")
    with open(level_path, "w") as f:
        json.dump(level, f, indent=2)

    print(f"Created {level_path}")
    print()
    print("Test level uses ORIGINAL elek1/elek2 sprites:")
    print("- Floor/walls from elek1 (sprites 3-7)")
    print("- Shootable objects from elek2 (sprites 0, 16, 17, 24, 25)")
    print("- Checkpoint from elek2 (sprites 56, 57)")
    print()
    print("Level spans 2 screens (17 and 18) connected horizontally.")


def idx(row, col):
    """Convert row, col to array index."""
    return row * 13 + col


def create_screen_left():
    """
    Create left screen (screen 17) - starting area with checkpoint.

    Layout (13 cols x 8 rows):
    Row 0: Walls
    Row 1: Open area with shootables
    Row 2: More shootables
    Row 3: Open
    Row 4: Shootables
    Row 5: Open
    Row 6: Checkpoint
    Row 7: Floor
    """
    # 4 layers, 104 sprites each
    bg = [0] * 104      # Layer 0: background
    col = [0] * 104     # Layer 1: collision tiles
    act = [0] * 104     # Layer 2: active sprites
    front = [0] * 104   # Layer 3: in-front

    # Sprite indices from elek1 (set 1, indices 1-63)
    FLOOR = 3       # Solid floor tile (flags=0x80, action=0)
    WALL = 4        # Solid wall tile

    # Sprite indices from elek2 (set 2, add 64 for level index)
    # These sprites have shootable flag (0x20) in original elek2.ebs
    SHOOT1 = 64 + 0    # Shootable sprite (flags=0xAB)
    SHOOT2 = 64 + 16   # Shootable sprite (flags=0xA9) - cannon-like
    SHOOT3 = 64 + 17   # Shootable sprite (flags=0xA8)
    SHOOT4 = 64 + 24   # Shootable sprite (flags=0xA9)
    SHOOT5 = 64 + 25   # Shootable sprite (flags=0xAA)

    # Checkpoint from elek2 (sprites 56, 57 have checkpoint action)
    CHECKPOINT = 64 + 56  # Checkpoint sprite

    # Row 0: Wall tiles across top
    for x in range(13):
        col[idx(0, x)] = WALL

    # Row 1: Side walls + shootable objects
    col[idx(1, 0)] = WALL
    col[idx(1, 12)] = WALL
    act[idx(1, 3)] = SHOOT1
    act[idx(1, 6)] = SHOOT1
    act[idx(1, 9)] = SHOOT1

    # Row 2: Side walls + different shootables
    col[idx(2, 0)] = WALL
    col[idx(2, 12)] = WALL
    act[idx(2, 2)] = SHOOT2
    act[idx(2, 5)] = SHOOT3
    act[idx(2, 8)] = SHOOT2
    act[idx(2, 10)] = SHOOT3

    # Row 3: Side walls only (open space)
    col[idx(3, 0)] = WALL
    col[idx(3, 12)] = WALL

    # Row 4: Side walls + more shootables
    col[idx(4, 0)] = WALL
    col[idx(4, 12)] = WALL
    act[idx(4, 3)] = SHOOT4
    act[idx(4, 6)] = SHOOT5
    act[idx(4, 9)] = SHOOT4

    # Row 5: Left wall only (right side open for passage)
    col[idx(5, 0)] = WALL
    # No wall at col 12 - open passage to next screen

    # Row 6: Left wall + checkpoint (player spawns here, above floor)
    col[idx(6, 0)] = WALL
    # No wall on right side (col 12) - open passage to next screen
    # Checkpoint at column 1 (safe - nothing above it)
    act[idx(6, 1)] = CHECKPOINT

    # Row 7: Floor tiles (walkable surface) - extends to edge for screen transition
    for x in range(13):
        col[idx(7, x)] = FLOOR

    return [bg, col, act, front]


def create_screen_right():
    """
    Create right screen (screen 18) - more shootables to test.

    Layout (13 cols x 8 rows):
    Row 0: Walls
    Row 1-5: Various shootable objects at different heights
    Row 6: Open
    Row 7: Floor
    """
    bg = [0] * 104
    col = [0] * 104
    act = [0] * 104
    front = [0] * 104

    # Sprite indices
    FLOOR = 3
    WALL = 4
    SHOOT1 = 64 + 0
    SHOOT2 = 64 + 16
    SHOOT3 = 64 + 17
    SHOOT4 = 64 + 24
    SHOOT5 = 64 + 25

    # Row 0: Walls
    for x in range(13):
        col[idx(0, x)] = WALL

    # Row 1: Shootables spread across
    # No wall on left (col 0) - open passage from previous screen
    col[idx(1, 12)] = WALL
    act[idx(1, 2)] = SHOOT1
    act[idx(1, 4)] = SHOOT2
    act[idx(1, 6)] = SHOOT3
    act[idx(1, 8)] = SHOOT4
    act[idx(1, 10)] = SHOOT5

    # Row 2: More shootables
    col[idx(2, 12)] = WALL
    act[idx(2, 3)] = SHOOT5
    act[idx(2, 5)] = SHOOT4
    act[idx(2, 7)] = SHOOT3
    act[idx(2, 9)] = SHOOT2

    # Row 3: Shootables at mid height
    col[idx(3, 12)] = WALL
    act[idx(3, 2)] = SHOOT2
    act[idx(3, 6)] = SHOOT1
    act[idx(3, 10)] = SHOOT2

    # Row 4: More variety
    col[idx(4, 12)] = WALL
    act[idx(4, 4)] = SHOOT3
    act[idx(4, 8)] = SHOOT3

    # Row 5: Low shootables (easy to hit from ground)
    col[idx(5, 12)] = WALL
    act[idx(5, 3)] = SHOOT4
    act[idx(5, 6)] = SHOOT5
    act[idx(5, 9)] = SHOOT4

    # Row 6: Open passage
    col[idx(6, 12)] = WALL

    # Row 7: Floor (extends to left edge for screen transition)
    for x in range(13):
        col[idx(7, x)] = FLOOR

    return [bg, col, act, front]


def main():
    print("=" * 60)
    print("PyElectroMan Test Level Generator")
    print("=" * 60)
    print()

    create_test_level()

    print()
    print("=" * 60)
    print("Test level created successfully!")
    print()
    print("To use:")
    print("1. Run the game: python em.py")
    print("2. Press Shift+9 to load test level")
    print("3. Use Shift+1 through Shift+5 to set weapon power")
    print("4. Test shooting the various objects!")
    print()
    print("The level uses ORIGINAL sprite definitions, so objects")
    print("behave exactly as they do in the real game.")
    print("=" * 60)


if __name__ == "__main__":
    main()
