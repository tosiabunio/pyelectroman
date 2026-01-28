"""Main menu module for PyElectroMan"""

import emglobals as gl
from emglobals import XY
import emdata as da
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

    # Sprite width for spacing (original size, will be scaled)
    CHAR_WIDTH = 24
    CHAR_HEIGHT = 22

    def __init__(self):
        self.sprites = {}
        self.loaded = False

    def load(self):
        """Load the letters sprite set."""
        if self.loaded:
            return True

        try:
            set_name = "letters"
            set_file_path = os.path.join(gl.data_folder, set_name)

            # Load each used sprite
            for char, idx in self.CHAR_MAP.items():
                if idx == 0:  # Space - no sprite
                    continue

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

        self.selected = new_selected

    def select_option(self):
        """Handle option selection."""
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
