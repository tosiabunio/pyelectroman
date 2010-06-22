"""
Global variables module
"""

# pylint: disable-msg=C0103

# PyGame related globals
small_font = None
medium_font = None
large_font = None
display = None # whole window surface
window = None # gameplay window subsurface

# display related globals
SPRITE_X = 48  # size in pixels
SPRITE_Y = 48  # size in pixels
SCREEN_X = 13  # size in sprites
SCREEN_Y = 8   # size in sprites

OFFSET_X = 8   # to center 13x8 sprites screen in 640x480 window
OFFSET_Y = 48  # to center 13x8 sprites screen in 640x480 window

DISPLAY_OFFSET = (OFFSET_X, OFFSET_Y)

show_collisions = False

# data related globals
data_folder = r"data"  # defaul data folder
level_names = ["elek", "koryt", "mieszk", "magaz",
               "fiolet", "10x10", "sluzy", "widok"]
current_level = 0 # current level number
level = None # currently loaded level

# gameplay related globals

screens = None # all level screen defintions
current_screen = 0 # current screen number
screen = None # current screen definition

loop_main_loop = True # loop the main gameplay loop
player = None
active_checkpoint = None

# system related globals

log_filename = "em.log"  # empty string disables logging to file

# global classes

class XY:
    def __init__(self, x=0, y=0):
        if not isinstance(x, int):
            raise ValueError, "x must be int."
        self.x = x
        if not isinstance(y, int):
            raise ValueError, "y must be int."
        self.y = y

    def __getitem__(self, index):
        if index == 0:
            return self.x
        elif index == 1:
            return self.y
        else:
            raise IndexError, "Index out of range!"

    def __len__(self):
        return 2

    def as_tuple(self):
        return (self.x, self.y)

    @classmethod
    def from_tuple(cls, tup):
        obj = cls()
        if len(tup) == 2:
            obj.x = tup[0]
            obj.y = tup[1]
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


def tuple_scale(tuple_in, scale):
    assert isinstance(tuple_in, tuple)
    tuple_out = []
    for elem in tuple_in:
        tuple_out.append(elem * scale)
    return tuple(tuple_out)


def tuple_add(tuple_one, tuple_two):
    assert len(tuple_one) == len(tuple_two)
    tuple_out = []
    for idx in range(len(tuple_one)):
        tuple_out.append(tuple_one[idx] + tuple_two[idx])
    return tuple(tuple_out)

# -----------------------------------------------------------------------------
# test code below

def main():
    position = XY()
    tpos = position.as_tuple()
    tpos = tuple_add(tpos, (1, 1))
    print tpos

if __name__ == "__main__":
    main()
