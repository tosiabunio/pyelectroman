"""
Global variables module
"""

import copy

# pylint: disable-msg=C0103

# PyGame related globals

font = {"xsmall": None,
        "small": None,
        "normal": None,
        "large": None}

small_font = None
medium_font = None
large_font = None
display = None  # whole window (screen) surface
window = None  # gameplay window subsurface

# display related globals
SPRITE_X = 48  # size in pixels
SPRITE_Y = 48  # size in pixels
SCREEN_X = 13  # size in sprites
SCREEN_Y = 8   # size in sprites
MAX_X = SPRITE_X * SCREEN_X  # screen size in pixels
MAX_Y = SPRITE_Y * SCREEN_Y  # screen size in pixels

OFFSET_X = 8  # to center 13x8 sprites screen in 640x480 window
OFFSET_Y = 48  # to center 13x8 sprites screen in 640x480 window

DISPLAY_OFFSET = (OFFSET_X, OFFSET_Y)

show_collisions = False

# data related globals
data_folder = r"data"  # defaul data folder
level_names = ["elek", "koryt", "mieszk", "magaz",
               "fiolet", "10x10", "sluzy", "widok"]
current_level = 0  # current level number
level = None  # currently loaded level

# gameplay related globals

screen_manager = None  # screen manager

loop_main_loop = True  # loop the main gameplay loop
player = None
active_checkpoint = None

# system related globals

log_filename = "em.log"  # empty string disables logging to file

# global classes


class XY:
    """Class to keep x, y positions."""
    def __init__(self, x=0, y=0):
        if not isinstance(x, int):
            raise ValueError("x must be an int.")
        self.x = x
        if not isinstance(y, int):
            raise ValueError("y must be an int.")
        self.y = y

    def __getitem__(self, index):
        """Return x as [0] and y as [1]."""
        if index == 0:
            return self.x
        elif index == 1:
            return self.y
        else:
            raise IndexError("Index out of range!")

    def __setitem__(self, index, value):
        """Set x from [0] and y from [1]."""
        if index == 0:
            self.x = value
        elif index == 1:
            self.y = value
        else:
            raise IndexError("Index out of range!")

    def __len__(self):
        """Always return 2 as length."""
        return 2

    def __add__(self, other):
        """Add another XY() or (x, y) tuple."""
        if isinstance(other, tuple) and len(other) == 2:
            other = XY.from_tuple(other)
        if not isinstance(other, XY):
            raise NotImplementedError(
                "Only XY() or (x, y) addition implemented.")
        x = self.x + other.x
        y = self.y + other.y
        return XY(x, y)

    def __str__(self):
        """Return human-readable representation."""
        return "XY(%d, %d)" % (self.x, self.y)

    def _repr__(self):
        return "<XY(%d, %d)>" % (self.x, self.y)

    def copy(self):
        """Return copy of self."""
        return copy.copy(self)

    @classmethod
    def from_tuple(cls, tup):
        """Initialize XY object from (x, y) tuple."""
        obj = cls()
        if len(tup) == 2:
            obj.x = tup[0]
            obj.y = tup[1]
        return obj

    @classmethod
    def from_self(cls, xy):
        """Initialize XY object from other XY object."""
        if not isinstance(xy, XY):
            raise ValueError("XY() object required.")
        obj = xy.copy()
        return obj

# other global functions

# Borland C 3.1 rand()

MULTIPLIER = 0x015a4e35
INCREMENT = 1
rand_seed = 1


def srand(seed):
    global rand_seed
    rand_seed = seed


def rand():
    """
    int rand(void)
    {
        Seed = MULTIPLIER * Seed + INCREMENT;
        return((int)(Seed >> 16) & 0x7fff);
    }
    """
    global rand_seed
    rand_seed = MULTIPLIER * rand_seed + INCREMENT
    return (rand_seed >> 16) & 0x7FFFF


def random(num):
    """ #define random(num)(int)(((long)rand()*(num))/(RAND_MAX+1)) """
    return int((rand() * num) / (0x80000))

# -----------------------------------------------------------------------------
# test code below


def main():
    p1 = XY()
    p2 = XY(1, 2)
    p1 += p2
    print p1

if __name__ == "__main__":
    main()
