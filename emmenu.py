"""Main menu module for PyElectroMan"""

import emglobals as gl
from emglobals import XY
import emdata as da
import emsound as snd
import pygame
import os
import json
import logging


class Letters:
    """
    Class to load and render text using the letters sprite set.
    Provides authentic DOS-style text rendering for the menu.
    """

    # Character to sprite index mapping (verified from letters sprite set)
    # Sprites 1-26: A-Z
    # Sprites 27-36: 0-9
    # Sprites 37-50: Punctuation
    CHAR_MAP = {
        'A': 1,  'B': 2,  'C': 3,  'D': 4,  'E': 5,  'F': 6,  'G': 7,
        'H': 8,  'I': 9,  'J': 10, 'K': 11, 'L': 12, 'M': 13, 'N': 14,
        'O': 15, 'P': 16, 'Q': 17, 'R': 18, 'S': 19, 'T': 20, 'U': 21,
        'V': 22, 'W': 23, 'X': 24, 'Y': 25, 'Z': 26,
        '0': 27, '1': 28, '2': 29, '3': 30, '4': 31,
        '5': 32, '6': 33, '7': 34, '8': 35, '9': 36,
        ' ': 0,   # No sprite, just spacing
        '*': 37,  # Asterisk
        '.': 38,  # Period
        ':': 39,  # Colon
        '-': 40,  # Hyphen/dash
        '/': 41,  # Slash
        '!': 42,  # Exclamation
        '?': 43,  # Question mark
        ',': 44,  # Comma
        '(': 45,  # Left paren
        ')': 46,  # Right paren
        '+': 47,  # Plus
        '=': 48,  # Equals
        '%': 49,  # Percent
        '>': 50,  # Greater than (arrow indicator)
    }

    # Character set in sprite index order, as used by the original print()
    # (EB.C:319-321): index 0 = space, 1-26 = a-z, 27-34 = Polish accented
    # letters, 35-44 = digits, 45-50 = punctuation. Verified against the
    # converted sprite PNGs. (Note: CHAR_MAP above maps digits differently
    # and is kept only for the menu's own legacy layout.)
    PRINT_CHARS = " abcdefghijklmnopqrstuvwxyząćęłńóśż0123456789:|?()_"

    # Sprite width for spacing (original size, will be scaled)
    CHAR_WIDTH = 24
    CHAR_HEIGHT = 22

    def __init__(self):
        self.sprites = {}
        self.loaded = False

    def load(self):
        """Load the letters sprite set (all 50 sprites)."""
        if self.loaded:
            return True

        try:
            set_name = "letters"
            set_file_path = os.path.join(gl.data_folder, set_name)

            for idx in range(1, 51):
                image_file_path = os.path.join(
                    set_file_path,
                    f"{set_name}_{idx:02d}.png"
                )

                if os.path.exists(image_file_path):
                    image = pygame.image.load(image_file_path).convert_alpha()
                    # Scale 2x to match game display
                    self.sprites[idx] = pygame.transform.scale2x(image)
                else:
                    logging.warning("Letters sprite not found: %s", image_file_path)

            self.loaded = True
            logging.info("Letters sprite set loaded: %d sprites", len(self.sprites))
            return True

        except Exception as e:
            logging.error("Failed to load letters sprite set: %s", e)
            return False

    def _sprite_4x(self, idx):
        """Letter sprite at 4x original size (matches in-game pixel scale)."""
        if not hasattr(self, "_sprites_4x"):
            self._sprites_4x = {}
        if idx not in self._sprites_4x:
            sprite = self.sprites.get(idx)  # already 2x
            self._sprites_4x[idx] = (pygame.transform.scale2x(sprite)
                                     if sprite else None)
        return self._sprites_4x[idx]

    def print_text(self, surface, text, origin, area=(320, 200)):
        """
        Port of the original print() (EB.C:319-350) at 4x scale (the
        in-game pixel scale), for the title/level-completed/
        congratulations screens and in-game prompts. '*' in text is a
        line separator. origin is the XY of the target area's top-left
        corner on the window, area its size in original pixels
        (1 original pixel = 4 window pixels).

        Deviation: the C px=py=255 mode centers on the bordered game
        playfield (center 180,120 of the 320x200 screen). The port shows
        the bare bitmap without the playfield border, so text is centered
        on the given area instead.
        """
        text = text.lower()
        if not text:
            return
        lines = text.split('*')
        # center the text block vertically on the area
        y = (area[1] - 24 * len(lines)) // 2
        for line in lines:
            # center each line horizontally on the area
            x = (area[0] - 24 * len(line)) // 2
            for char in line:
                idx = self.PRINT_CHARS.find(char)
                if idx <= 0:
                    x += 24
                    continue
                sprite = self._sprite_4x(idx)
                if sprite:
                    surface.blit(sprite,
                                 (origin.x + x * 4, origin.y + y * 4))
                x += 24
            y += 24

    def get_text_width(self, text):
        """Calculate width of rendered text (in pixels, scaled 2x)."""
        return len(text) * self.CHAR_WIDTH * 2

    def render_text(self, surface, text, position, color_mod=None):
        """
        Render a string using letter sprites.

        Args:
            surface: pygame surface to draw on
            text: string to render (uppercase letters, numbers, some punctuation)
            position: XY position for top-left of text
            color_mod: optional tuple (r, g, b) to modulate color (for graying out)

        Returns:
            XY position after the rendered text
        """
        text = text.upper()
        x, y = position.x, position.y

        for char in text:
            idx = self.CHAR_MAP.get(char, 0)

            if idx == 0:
                # Space or unknown character - just advance position
                x += self.CHAR_WIDTH * 2
                continue

            if idx in self.sprites:
                sprite = self.sprites[idx]

                # Apply color modulation if specified (for grayed out text)
                if color_mod:
                    sprite = sprite.copy()
                    sprite.fill(color_mod, special_flags=pygame.BLEND_MULT)

                surface.blit(sprite, (x, y))

            x += self.CHAR_WIDTH * 2

        return XY(x, y)

    def render_text_centered(self, surface, text, y, color_mod=None):
        """
        Render text centered horizontally on the surface.

        Args:
            surface: pygame surface to draw on
            text: string to render
            y: vertical position
            color_mod: optional color modulation

        Returns:
            XY position after the rendered text
        """
        text_width = self.get_text_width(text)
        surface_width = surface.get_width()
        x = (surface_width - text_width) // 2
        return self.render_text(surface, text, XY(x, y), color_mod)


class SaveGame:
    """
    Handles save and load game functionality.
    Saves checkpoint data to a JSON file.
    """

    SAVE_FILE = "pyelectroman.sav"

    def __init__(self):
        self.data = None

    def get_save_path(self):
        """Get full path to save file (same directory as em.py)."""
        # Save file is in the pyelectroman directory
        return os.path.join(os.path.dirname(__file__), self.SAVE_FILE)

    def exists(self):
        """Check if a save file exists."""
        return os.path.exists(self.get_save_path())

    def _calculate_checksum(self, data):
        """Calculate simple checksum for save data integrity."""
        checksum = 0
        checksum += data.get('level', 0)
        checksum += data.get('screen', 0)
        checksum += data.get('position_x', 0)
        checksum += data.get('position_y', 0)
        checksum += data.get('disks', 0)
        checksum += data.get('power', 0)
        for disk_pos in data.get('disk_positions', []):
            checksum += sum(disk_pos) if isinstance(disk_pos, (list, tuple)) else 0
        return checksum % 256

    def save(self):
        """
        Save current game state to file.
        Called when player activates a checkpoint.

        Returns:
            True if save successful, False otherwise
        """
        try:
            # Get current checkpoint data
            checkpoint = gl.checkpoint
            if checkpoint is None:
                logging.warning("Cannot save - no checkpoint set")
                return False

            # Build save data structure (matches original EB.C:920-948)
            position = checkpoint.get_position()
            self.data = {
                'level': checkpoint.get_level(),
                'screen': checkpoint.get_screen(),
                'position_x': position.x if position else 0,
                'position_y': position.y if position else 0,
                'disks': gl.disks,
                'disk_positions': [
                    [pos[0], pos[1].x, pos[1].y]
                    for pos in gl.disk_positions
                ] if gl.disk_positions else [],
                'power': gl.player.power if gl.player else 0,
            }

            # Add checksum
            self.data['checksum'] = self._calculate_checksum(self.data)

            # Write to file
            save_path = self.get_save_path()
            with open(save_path, 'w') as f:
                json.dump(self.data, f, indent=2)

            logging.info("Game saved to %s", save_path)
            return True

        except Exception as e:
            logging.error("Failed to save game: %s", e)
            return False

    def load(self):
        """
        Load game state from file.

        Returns:
            True if load successful, False otherwise
        """
        try:
            save_path = self.get_save_path()

            if not os.path.exists(save_path):
                logging.info("No save file found at %s", save_path)
                return False

            with open(save_path, 'r') as f:
                self.data = json.load(f)

            # Validate checksum
            saved_checksum = self.data.get('checksum', -1)
            data_copy = dict(self.data)
            data_copy.pop('checksum', None)
            calculated_checksum = self._calculate_checksum(data_copy)

            if saved_checksum != calculated_checksum:
                logging.warning("Save file checksum mismatch - file may be corrupt")
                return False

            logging.info("Game loaded from %s", save_path)
            return True

        except Exception as e:
            logging.error("Failed to load game: %s", e)
            return False

    def apply_to_game(self):
        """
        Apply loaded save data to game globals.
        Must call load() first.

        Returns:
            True if applied successfully, False otherwise
        """
        if self.data is None:
            logging.error("No save data loaded")
            return False

        try:
            # Set level
            gl.current_level = self.data.get('level', 0)

            # Set checkpoint
            level = self.data.get('level', 0)
            screen = self.data.get('screen', 0)
            pos_x = self.data.get('position_x', 0)
            pos_y = self.data.get('position_y', 0)
            gl.checkpoint.update(level, screen, XY(pos_x, pos_y))

            # Set disk count
            gl.disks = self.data.get('disks', 0)

            # Restore disk positions
            gl.disk_positions = []
            for disk_data in self.data.get('disk_positions', []):
                if len(disk_data) == 3:
                    screen_num, dx, dy = disk_data
                    gl.disk_positions.append((screen_num, XY(dx, dy)))

            logging.info("Save data applied: level=%d, screen=%d, disks=%d",
                        gl.current_level, screen, gl.disks)
            return True

        except Exception as e:
            logging.error("Failed to apply save data: %s", e)
            return False


class MainMenu:
    """
    Main menu screen controller.
    Displays CONTINUE, NEW GAME, QUIT options with authentic sprite font.
    """

    # Menu options
    OPTIONS = ["CONTINUE", "NEW GAME", "QUIT"]

    # Colors
    COLOR_NORMAL = None  # No modification - full brightness
    COLOR_DISABLED = (100, 100, 100)  # Gray for disabled options
    COLOR_ARROW = (255, 255, 0)  # Yellow for selection arrow

    # Layout constants (positions at 2x scale)
    TITLE_Y = 150
    OPTIONS_START_Y = 350
    OPTIONS_SPACING = 80
    INSTRUCTIONS_Y = 700

    def __init__(self):
        self.letters = Letters()
        self.save_game = SaveGame()
        self.selected = 0
        self.running = True
        self.result = None
        self.arrow_visible = True
        self.arrow_timer = 0

    def init(self):
        """Initialize the menu (load sprites, check save state)."""
        self.letters.load()
        self.has_save = self.save_game.exists()

        # If no save, start with NEW GAME selected
        if not self.has_save:
            self.selected = 1

    def handle_input(self):
        """Handle keyboard input."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.result = "quit"
                self.running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    self.move_selection(-1)
                elif event.key == pygame.K_DOWN:
                    self.move_selection(1)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self.select_option()
                elif event.key == pygame.K_ESCAPE:
                    self.result = "quit"
                    self.running = False

    def move_selection(self, direction):
        """Move selection up or down."""
        new_selected = self.selected + direction

        # Wrap around
        if new_selected < 0:
            new_selected = len(self.OPTIONS) - 1
        elif new_selected >= len(self.OPTIONS):
            new_selected = 0

        # Skip disabled options (CONTINUE when no save)
        if new_selected == 0 and not self.has_save:
            # Skip to next valid option
            new_selected = 1 if direction > 0 else len(self.OPTIONS) - 1

        if self.selected != new_selected:
            snd.play_sound('ask')
        self.selected = new_selected

    def select_option(self):
        """Handle option selection."""
        snd.play_sound('ask')
        option = self.OPTIONS[self.selected]

        if option == "CONTINUE":
            if self.has_save:
                self.result = "continue"
                self.running = False
        elif option == "NEW GAME":
            self.result = "new_game"
            self.running = False
        elif option == "QUIT":
            self.result = "quit"
            self.running = False

    def update(self):
        """Update menu state (animations, etc)."""
        # Arrow blink animation (10 frame cycle at 20 FPS = 0.5 sec)
        self.arrow_timer += 1
        if self.arrow_timer >= 10:
            self.arrow_timer = 0
            self.arrow_visible = not self.arrow_visible

    def render(self, surface):
        """Render the menu screen."""
        # Draw dark blue gradient background
        self.draw_background(surface)

        # Draw title
        self.letters.render_text_centered(surface, "PYELECTROMAN", self.TITLE_Y)

        # Draw subtitle
        subtitle_y = self.TITLE_Y + 60
        self.letters.render_text_centered(surface, "PYTHON PORT", subtitle_y)

        # Draw menu options
        for i, option in enumerate(self.OPTIONS):
            y = self.OPTIONS_START_Y + i * self.OPTIONS_SPACING

            # Determine color based on state
            if option == "CONTINUE" and not self.has_save:
                color_mod = self.COLOR_DISABLED
            else:
                color_mod = self.COLOR_NORMAL

            # Draw option text centered
            self.letters.render_text_centered(surface, option, y, color_mod)

            # Draw selection arrow
            if i == self.selected and self.arrow_visible:
                # Calculate position for arrow (left of text)
                text_width = self.letters.get_text_width(option)
                text_x = (surface.get_width() - text_width) // 2
                arrow_x = text_x - 60  # 60 pixels left of text
                self.letters.render_text(surface, ">", XY(arrow_x, y))

        # Draw instructions using system font (for clarity)
        self.draw_instructions(surface)

    def draw_background(self, surface):
        """Draw dark blue gradient background."""
        width = surface.get_width()
        height = surface.get_height()

        # Create gradient from dark blue to darker blue
        for y in range(height):
            # Gradient from (0, 0, 40) at top to (0, 0, 20) at bottom
            blue = int(40 - (y / height) * 20)
            color = (0, 0, blue)
            pygame.draw.line(surface, color, (0, y), (width, y))

    def draw_instructions(self, surface):
        """Draw instruction text at bottom of screen."""
        font = gl.font["small"] if gl.font["small"] else pygame.font.SysFont("tahoma", 20)

        instructions = "UP/DOWN: Select   ENTER: Confirm   ESC: Quit"
        text_surface = font.render(instructions, True, (150, 150, 150))
        text_rect = text_surface.get_rect(center=(surface.get_width() // 2, self.INSTRUCTIONS_Y))
        surface.blit(text_surface, text_rect)

    def run(self):
        """
        Main menu loop.

        Returns:
            str: "continue", "new_game", or "quit"
        """
        self.init()
        self.running = True
        self.result = None

        clock = pygame.time.Clock()

        while self.running:
            # Handle input
            self.handle_input()

            # Update
            self.update()

            # Render
            gl.window.fill((0, 0, 0))  # Clear screen
            self.render(gl.window)

            # Show
            pygame.display.flip()

            # Maintain 20 FPS to match game
            clock.tick(20)

        return self.result


class MusicScreen:
    """
    Full-screen bitmap + looping pattern music, port of play_music
    (EB.C:1204-1295). Used by the title page, the level-completed screen
    and the congratulations screen.

    Bitmaps are the original 320x200 screens scaled 4x to 1280x800 (the
    in-game pixel scale) and centered in the 1280x960 window. On the title
    screen the two bitmaps alternate every 4 song patterns, synced to the
    music position exactly like the original. Fire (Space/Enter) ends the
    screen; Esc brings up the original "exit to dos? (y or n)" confirmation.
    """

    # 320x200 bitmap scaled 4x, centered in the 1280x960 window
    BMP_W, BMP_H = 1280, 800
    ORIGIN = XY((1280 - BMP_W) // 2, (960 - BMP_H) // 2)

    def __init__(self, bmp1, bmp2, message, song):
        self.letters = Letters()
        self.letters.load()
        self.message = message
        self.scr1 = self._load_bmp(bmp1)
        self.scr2 = self._load_bmp(bmp2) if bmp2 != bmp1 else self.scr1
        self.music = snd.MusicPlayer()
        self.music.load_song(song)
        self.overlay_tile = _load_info_sprite(6)  # filler tile (EB.C:1231)
        self.esc_flag = False
        self.result = None

    @staticmethod
    def _load_bmp(name):
        path = os.path.join(gl.data_folder, name)
        try:
            image = pygame.image.load(path).convert()
            return pygame.transform.scale(
                image, (MusicScreen.BMP_W, MusicScreen.BMP_H))
        except (pygame.error, FileNotFoundError) as e:
            logging.error("Failed to load bitmap %s: %s", path, e)
            surface = pygame.Surface((MusicScreen.BMP_W, MusicScreen.BMP_H))
            surface.fill((0, 0, 64))
            return surface

    def current_image(self):
        """
        Pick scr1/scr2 from the music position. The original redraws at
        every 4th pattern, alternating the bitmap (EB.C:1222-1240):
        patterns 0-2 show scr1, 3-6 scr2, 7-10 scr1, ...
        """
        return self.scr2 if ((self.music.song_pos + 1) // 4) % 2 else self.scr1

    def render(self):
        gl.window.fill((0, 0, 0))
        origin = self.ORIGIN
        gl.window.blit(self.current_image(), (origin.x, origin.y))
        if self.esc_flag:
            # Cover the screen with filler tiles + confirmation (EB.C:1227-1234).
            # Deviation: the original grid covers the bordered playfield
            # (24,24 onward, edge clipped); the port has no border, so the
            # whole bitmap is tiled symmetrically instead.
            if self.overlay_tile:
                gl.window.set_clip(pygame.Rect(origin.x, origin.y,
                                               self.BMP_W, self.BMP_H))
                tile_size = self.overlay_tile.get_width()
                for x in range(0, self.BMP_W, tile_size):
                    for y in range(0, self.BMP_H, tile_size):
                        gl.window.blit(self.overlay_tile,
                                       (origin.x + x, origin.y + y))
                gl.window.set_clip(None)
            self.letters.print_text(gl.window, "exit to dos?*(y or n)", origin)
        else:
            self.letters.print_text(gl.window, self.message, origin)
        pygame.display.flip()

    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.result = "quit"
            elif event.type == pygame.KEYDOWN:
                if self.esc_flag:
                    if event.key == pygame.K_y:
                        self.result = "quit"
                    elif event.key == pygame.K_n:
                        self.esc_flag = False
                elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    self.result = "done"
                elif event.key == pygame.K_ESCAPE:
                    self.esc_flag = True

    def run(self):
        """Show the screen until fire is pressed. Returns "done" or "quit"."""
        clock = pygame.time.Clock()
        self.music.start()
        while self.result is None:
            self.handle_input()
            self.music.update()
            self.render()
            clock.tick(20)
        self.music.stop()
        return self.result


def _load_info_sprite(idx):
    """Load a single info-set sprite scaled 4x (24px -> 96px, in-game scale)."""
    path = os.path.join(gl.data_folder, "info", f"info_{idx:02d}.png")
    try:
        image = pygame.image.load(path).convert_alpha()
        return pygame.transform.scale2x(pygame.transform.scale2x(image))
    except (pygame.error, FileNotFoundError) as e:
        logging.warning("Failed to load info sprite %s: %s", path, e)
        return None


def show_loading_animation(frames=8):
    """
    The original loading screen (EB.C:460-472): a row of info sprites with
    a blinking indicator light, redrawn after each asset load. Loads are
    near-instant in the port, so it is displayed briefly for fidelity.
    """
    tiles = {n: _load_info_sprite(n) for n in (12, 13, 14, 15)}
    if not all(tiles.values()):
        return
    origin = MusicScreen.ORIGIN
    clock = pygame.time.Clock()
    for b in range(frames):
        gl.window.fill((0, 0, 0))
        for i in range(24, 14 * 24, 24):
            gl.window.blit(tiles[15], (origin.x + i * 4,
                                       origin.y + 8 * 24 * 4))
        gl.window.blit(tiles[14], (origin.x + (13 * 24 - 6) * 4,
                                   origin.y + 8 * 24 * 4))
        gl.window.blit(tiles[13] if b & 1 else tiles[12],
                       (origin.x + (12 * 24 - 6) * 4,
                        origin.y + 8 * 24 * 4))
        pygame.display.flip()
        pygame.event.pump()
        clock.tick(20)


def ask_confirmation(message):
    """
    In-game Y/N confirmation prompt (EB.C:1103-1129): plays ask_s, covers
    the 13x8 playfield with filler tiles over the current frame, prints the
    message ('*' = newline) and blocks until Y or N is pressed.
    Used for "quit (y or n)" and "restart level? (y or n)".
    Returns True on Y (or window close), False on N.
    """
    letters = Letters()
    letters.load()
    tile = _load_info_sprite(6)
    snd.play_sound('ask')
    # gameplay playfield rect on the window (13x8 tiles of 96px)
    origin = XY(gl.OFFSET_X * 2, gl.OFFSET_Y * 2)
    area = (gl.SCREEN_X * 24, gl.SCREEN_Y * 24)  # in original pixels
    if tile:
        for x in range(gl.SCREEN_X):
            for y in range(gl.SCREEN_Y):
                gl.window.blit(tile, (origin.x + x * 96, origin.y + y * 96))
    letters.print_text(gl.window, message, origin, area)
    pygame.display.flip()
    clock = pygame.time.Clock()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return True
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_y:
                    return True
                if event.key == pygame.K_n:
                    return False
        clock.tick(20)


def show_title_screen():
    """
    Title page (EB.C:1475): tit1/tit2 bitmaps alternating to tit_song.
    Returns "done" (fire pressed) or "quit".
    """
    show_loading_animation()
    screen = MusicScreen("tit1.bmp", "tit2.bmp", "", snd.TIT_SONG)
    return screen.run()


def show_level_completed(level_number):
    """
    "Well done" screen after each completed level (EB.C:1532):
    back.bmp + cod_song + completion message (MESSAGES.H:25 MELEVCMP).
    Returns "done" or "quit".
    """
    message = "good job* *level %d*completed* *press fire" % level_number
    screen = MusicScreen("back.bmp", "back.bmp", message, snd.COD_SONG)
    return screen.run()


def show_congratulations():
    """
    Game-completed screen (EB.C:1556): over.bmp + end_song.
    Returns "done" or "quit".
    """
    screen = MusicScreen("over.bmp", "over.bmp", "", snd.END_SONG)
    return screen.run()


# Convenience function for use in em.py
def show_main_menu():
    """
    Show the main menu and return the result.

    Returns:
        str: "continue", "new_game", or "quit"
    """
    menu = MainMenu()
    return menu.run()


def load_saved_game():
    """
    Load saved game and apply to globals.

    Returns:
        True if successful, False otherwise
    """
    save_game = SaveGame()
    if save_game.load():
        return save_game.apply_to_game()
    return False


def save_current_game():
    """
    Save current game state.

    Returns:
        True if successful, False otherwise
    """
    save_game = SaveGame()
    return save_game.save()


# -----------------------------------------------------------------------------
# test code below

def main():
    """Test the menu system."""
    import emdisplay as di

    # Initialize display
    di.init_display()

    # Show menu
    result = show_main_menu()
    print(f"Menu result: {result}")

    # Cleanup
    di.quit_display()


if __name__ == "__main__":
    main()
