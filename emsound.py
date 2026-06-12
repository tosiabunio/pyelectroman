"""
Sound effects manager for PyElectroMan.
Implements sound playback matching original DOS game (EB.H:96-114, EB.C:1410-1428).
"""

import os
import logging
import pygame

import emglobals as gl

# Number of simultaneous mixer channels for sound effects
_NUM_CHANNELS = 8
# Extra dedicated channel for pattern music (channel 0 in the original driver)
_MUSIC_CHANNEL = 8

# Song strings (EB.C:184-202, FULL version).
# First char is the sample file prefix; letters a-z queue sample
# "<prefix><letter>"; modifiers slice the previously queued pattern:
# '<' first half, '>' second half, '1'-'4' quarter N, '!' 1/16.
TIT_SONG = ("t"
            "hhhhaaaabbbbbbbbc<c>c<c>c<c>c<c>bbbbbbbbdddddddd"
            "c<c>c<c>c<c>c<c>e<e>e<e>e<e>e<e>j<j>j<j>j<j>j<j>"
            "ffffffffhhhhdddd"
            "bbbbbbbbc<c>c<c>c<c>c<c>ffffffffbbbbbbbb"
            "c<c>c<c>c<c>c<c>e<e>e<e>e<e>e<e>"
            "ffffffffggggdddd")
COD_SONG = "cbbbbccccddddbbbbaaaaccccddddaaaa"
END_SONG = "eaaaabbbbccccddddbbbbcccceeee"


class SoundManager:
    """
    Manages sound effects for PyElectroMan.
    Uses pygame.mixer for audio playback with priority system.

    Priority enforcement matches the original DOS driver: when all channels are
    busy and a new sound arrives, it preempts the lowest-priority active channel
    if that channel's priority is strictly lower than the new sound's priority.
    If all channels are occupied by sounds of equal or higher priority, the new
    sound is dropped (matches EB.C:1410-1428 LOAD_SAMPLE priority parameter).
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
        # Priority currently assigned to each mixer channel (index = channel id)
        self._channel_priority = [0] * _NUM_CHANNELS

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

        # +1 channel reserved for pattern music (never used by SFX)
        pygame.mixer.set_num_channels(_NUM_CHANNELS + 1)

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
        """
        Play a sound effect by name with priority enforcement.

        Matches original DOS driver behaviour (EB.C:1410-1428):
        - Free channel found  -> play immediately.
        - All channels busy   -> preempt the lowest-priority channel if its
                                 priority is strictly lower than the new sound.
        - No preemption possible -> drop the new sound silently.
        """
        if not self.enabled or not self.initialized:
            return
        if sound_name not in self.sounds:
            return

        new_prio = self.PRIORITY.get(sound_name, 5)
        sound = self.sounds[sound_name]
        n = _NUM_CHANNELS  # SFX never touch the reserved music channel

        # First pass: look for a free channel
        for i in range(n):
            ch = pygame.mixer.Channel(i)
            if not ch.get_busy():
                ch.play(sound)
                self._channel_priority[i] = new_prio
                return

        # All channels busy: find the lowest-priority active channel
        lowest_i = min(range(n), key=lambda i: self._channel_priority[i])
        if new_prio > self._channel_priority[lowest_i]:
            ch = pygame.mixer.Channel(lowest_i)
            ch.stop()
            ch.play(sound)
            self._channel_priority[lowest_i] = new_prio
        # else: all active sounds have equal or higher priority — drop new sound

    def toggle(self):
        """Toggle sound on/off (F7 key in original)."""
        self.enabled = not self.enabled
        return self.enabled

    def is_enabled(self):
        """Return whether sound is enabled."""
        return self.enabled


class MusicPlayer:
    """
    Pattern-based music engine, port of load_music/play_music (EB.C:1139-1295).

    The original has no music format: songs are strings of ~2-4s 8kHz sample
    "patterns" chained gaplessly on a dedicated channel, looping forever.
    Slice modifiers reuse parts of the previous pattern (see song constants).
    song_pos advances once per completed chain entry and drives the title
    screen image flip in the caller.
    """

    # Raw sample data cache, shared between player instances: name -> bytes
    _pattern_cache = {}

    def __init__(self):
        self.playlist = []
        self.song_pos = 0
        self.channel = None
        mgr = gl.sound_manager
        self.initialized = bool(mgr and mgr.initialized)
        if self.initialized:
            self.channel = pygame.mixer.Channel(_MUSIC_CHANNEL)

    def _get_pattern(self, name):
        """Load (and cache) raw sample data for pattern file <name>.wav."""
        if name not in self._pattern_cache:
            path = os.path.join(gl.data_folder, name + ".wav")
            try:
                self._pattern_cache[name] = pygame.mixer.Sound(path).get_raw()
            except (pygame.error, FileNotFoundError) as e:
                logging.warning("Failed to load music pattern %s: %s", path, e)
                self._pattern_cache[name] = None
        return self._pattern_cache[name]

    def load_song(self, song):
        """
        Parse a song string into the playlist (EB.C:1143 load_music).
        Each letter a-z appends one playback of sample <prefix><letter>;
        modifiers slice the previously appended entry. Slices stay 2-byte
        aligned (mixer samples are 16-bit; C lengths were 8-bit bytes).
        """
        self.playlist = []
        if not self.initialized:
            return False
        prefix = song[0]
        entries = []  # [raw, offset, length]
        for c in song[1:]:
            if 'a' <= c <= 'z':
                raw = self._get_pattern(prefix + c)
                if raw is not None:
                    entries.append([raw, 0, len(raw)])
            elif entries:
                entry = entries[-1]
                if c == '<':
                    entry[2] //= 2
                elif c == '>':
                    entry[2] //= 2
                    entry[1] += entry[2]
                elif c in '1234':
                    entry[2] //= 4
                    entry[1] += entry[2] * (ord(c) - ord('1'))
                elif c == '!':
                    entry[2] //= 16
                entry[1] &= ~1
                entry[2] &= ~1
        for raw, off, length in entries:
            self.playlist.append(
                pygame.mixer.Sound(buffer=raw[off:off + length]))
        return len(self.playlist) > 0

    def start(self):
        """Start playing the loaded song from the beginning."""
        if not self.playlist or not self.initialized:
            return
        if not gl.sound_manager.enabled:
            return
        self.song_pos = 0
        self.channel.play(self.playlist[0])
        if len(self.playlist) > 1:
            self.channel.queue(self.playlist[1])

    def update(self):
        """
        Call once per frame. Keeps the channel queue filled and advances
        song_pos when the driver moves to the next pattern (the equivalent
        of C's get_next_flag(0) change). The chain loops endlessly.
        """
        if not self.playlist or not self.initialized:
            return
        if not self.channel.get_busy():
            # underrun (or sound was toggled) - restart current pattern
            if gl.sound_manager.enabled:
                self.channel.play(self.playlist[self.song_pos %
                                                len(self.playlist)])
        if self.channel.get_queue() is None:
            self.song_pos = (self.song_pos + 1) % len(self.playlist)
            nxt = (self.song_pos + 1) % len(self.playlist)
            self.channel.queue(self.playlist[nxt])

    def stop(self):
        """Stop music playback (EB.C:1293 stop_sounds)."""
        if self.initialized:
            self.channel.stop()


def play_sound(name):
    """
    Convenience function to play a sound effect.
    Safe to call even if sound manager is not initialized.
    """
    if gl.sound_manager:
        gl.sound_manager.play(name)
