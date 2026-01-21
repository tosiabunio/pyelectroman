# PyElectroMan Debug Shortcuts

This document lists all keyboard shortcuts available in the Python version of PyElectroMan.

## Player Controls

| Key | Action |
|-----|--------|
| Arrow Left | Move left |
| Arrow Right | Move right |
| Arrow Up | Jump |
| Arrow Down | Duck |
| Space | Fire weapon |

## Game Exit

| Key | Action |
|-----|--------|
| Esc | Quit game |
| Alt+X | Quit game (matches original DOS version) |

## Level Navigation

| Key | Action |
|-----|--------|
| 1 | Jump to Level 1 (elek) |
| 2 | Jump to Level 2 (koryt) |
| 3 | Jump to Level 3 (mieszk) |
| 4 | Jump to Level 4 (magaz) |
| 5 | Jump to Level 5 (fiolet) |
| 6 | Jump to Level 6 (10x10) |
| 7 | Jump to Level 7 (sluzy) |
| 8 | Jump to Level 8 (widok) |

## Screen Navigation

| Key | Action |
|-----|--------|
| Ctrl+Left | Navigate to previous screen (horizontal) |
| Ctrl+Right | Navigate to next screen (horizontal) |
| Ctrl+Up | Navigate to screen above (vertical, -16) |
| Ctrl+Down | Navigate to screen below (vertical, +16) |

Note: The level is arranged in a 16x16 grid of 256 screens.

## Player Teleport

| Key | Action |
|-----|--------|
| Shift+Left | Teleport player left by one sprite width (48px) |
| Shift+Right | Teleport player right by one sprite width (48px) |
| Shift+Up | Teleport player up by one sprite height (48px) |
| Shift+Down | Teleport player down by one sprite height (48px) |

## Weapon Selection

| Key | Action |
|-----|--------|
| Shift+0 | Select weapon level 0 (no weapon) |
| Shift+1 | Select weapon level 1 (short missile) |
| Shift+2 | Select weapon level 2 (long missile) |
| Shift+3 | Select weapon level 3 (long missile variant) |
| Shift+4 | Select weapon level 4 (penetrating missile) |
| Shift+5 | Select weapon level 5 (bow - double height, triple explosion) |

## Visual Debug

| Key | Action |
|-----|--------|
| Tab | Toggle collision box display (shows AABBs and collision sides) |

## Gameplay Testing

| Key | Action |
|-----|--------|
| Shift+D | Trigger player death (test death/respawn system) |
| Shift+F | Give all 3 disks (enables level exit) |

## On-Screen Information

The following debug information is always displayed:

| Location | Information |
|----------|-------------|
| Top-left | Performance stats (logic/render timing in ms) |
| Top-right | Minimap (16x16 level grid, scaled 64x64) |
| Bottom-center | Disk counter (0-3), blinks when 3 disks collected |
| Bottom-left | Temperature LED bar |
| Bottom-right | Ammo LED bar |

## Notes

- Most debug shortcuts require the Shift or Ctrl modifier to prevent accidental activation during normal gameplay.
- Player controls (arrow keys and space) only work when no modifier keys (Ctrl, Shift, Alt) are held.
- The minimap shows the current screen position as a white dot on the level grid.
- Collision display (Tab) shows bounding boxes for all collidable entities.
