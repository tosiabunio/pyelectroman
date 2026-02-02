"""
Sound effects manager for PyElectroMan.
Implements sound playback matching original DOS game (EB.H:96-114, EB.C:1410-1428).
"""

import os
import logging
import pygame

import emglobals as gl


class SoundManager:
    """
    Manages sound effects for PyElectroMan.
    Uses pygame.mixer for audio playback with priority system.
    """

    # Sound files mapping (from EB.H:96-114)
    SOUND_FILES = {
        'shoot1': 'wpn_1.wav',
        'shoot2': 'wpn_2.wav',
        'shoot3': 'wpn_3.wav',
        'shoot4': 'wpn_4.wav',
        'shoot5': 'wpn_5.wav',
        'blast': 'xplosion.wav',
        'teleport': 'teleport.wav',
        'jump': 'jump.wav',
        'jumpend': 'jumpend.wav',
        'footstep': 'footstep.wav',
        'warning': 'warning.wav',
        'warning2': 'warning2.wav',
        'battery': 'battery.wav',
        'shoot': 'shoot.wav',      # Enemy shoot
        'laser': 'laser.wav',      # Cannon
        'checkp': 'checkp.wav',
        'disk': 'disk.wav',
        'area': 'area.wav',
        'ask': 'ask.wav',
        'eshoot': 'eshoot.wav',    # Enemy projectile
    }

    # Sound priority (higher = more important, from EB.C:1410-1428)
    PRIORITY = {
        'footstep': 1,
        'jump': 2,
        'jumpend': 2,
        'laser': 3,
        'shoot1': 4, 'shoot2': 4, 'shoot3': 4, 'shoot4': 4, 'shoot5': 4,
        'shoot': 4, 'warning': 4, 'warning2': 4,
        'battery': 6,
        'teleport': 7,
        'blast': 8,
        'checkp': 9, 'disk': 9, 'area': 9, 'ask': 9,
        'eshoot': 4,
    }

    def __init__(self):
        """Initialize pygame mixer and load all sounds."""
        self.sounds = {}
        self.enabled = True
        self.initialized = False

        try:
            # Initialize mixer for 8kHz mono WAV files
            pygame.mixer.init(frequency=8000, size=-16, channels=1, buffer=512)
            self.initialized = True
            self._load_sounds()
        except pygame.error as e:
            logging.warning("Sound initialization failed: %s", e)

    def _load_sounds(self):
        """Load all sound files from data folder."""
        if not self.initialized:
            return

        for name, filename in self.SOUND_FILES.items():
            path = os.path.join(gl.data_folder, filename)
            if os.path.exists(path):
                try:
                    self.sounds[name] = pygame.mixer.Sound(path)
                except pygame.error as e:
                    logging.warning("Failed to load sound %s: %s", filename, e)
            else:
                logging.debug("Sound file not found: %s", path)

        logging.info("Loaded %d/%d sound effects", len(self.sounds), len(self.SOUND_FILES))

    def play(self, sound_name):
        """Play a sound effect by name."""
        if not self.enabled or not self.initialized:
            return
        if sound_name in self.sounds:
            self.sounds[sound_name].play()

    def toggle(self):
        """Toggle sound on/off (F7 key in original)."""
        self.enabled = not self.enabled
        return self.enabled

    def is_enabled(self):
        """Return whether sound is enabled."""
        return self.enabled


def play_sound(name):
    """
    Convenience function to play a sound effect.
    Safe to call even if sound manager is not initialized.
    """
    if gl.sound_manager:
        gl.sound_manager.play(name)
