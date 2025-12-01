  - ## Debug Controls

    PyElectroMan includes extensive debug controls for testing and development:

    ### Player Controls

    - **Arrow Keys**: Move left/right, jump (up), duck (down)
    - **Space**: Fire weapon
    - **Esc** or **Alt-X**: Quit game

    ### Level Navigation

    - **Keys 1-8**: Jump to level 1-8 instantly
    - **Ctrl+Left/Right/Up/Down**: Navigate between screens (16x16 grid)
    - **Shift+Left/Right/Up/Down**: Teleport player position within current screen

    ### Weapon & Power-ups

    - **Shift+1 through Shift+5**: Set weapon power level (0-5)
    - **Shift+F**: Give all 3 disks (enables level exit) ✨ NEW

    ### Visual Debug

    - **Tab**: Toggle collision box display (shows AABBs and collision sides)

    ### Gameplay Testing

    - **Shift+D**: Trigger player death (test death/respawn system)

    ### Display Information

    - **Minimap**: Top-right corner shows 16x16 level grid
    - **Performance Stats**: Top-left shows logic/render timing (ms)
    - **Disk Counter**: Bottom center shows collected disks (0-3)
    - **Temperature/Ammo Bars**: Bottom left/right LED indicators

    **Note:** Most debug shortcuts require the Shift or Ctrl modifier to prevent accidental activation during normal gameplay.