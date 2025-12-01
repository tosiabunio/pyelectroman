"""Display module"""

import emglobals as gl
from emglobals import XY
import pygame
import logging
import time


#noinspection PyArgumentEqualDefault
def init_display():
    pygame.init()
    # Use 2x scaling for better visibility on high-res monitors
    gl.window = pygame.display.set_mode((1280, 960), 0, 32)
    pygame.display.set_caption("Electro Man - Python Version")
    # Larger fonts for 2x scaling
    gl.font["xsmall"] = pygame.font.SysFont("tahoma", 16)
    gl.font["small"] = pygame.font.SysFont("tahoma", 20)
    gl.font["normal"] = pygame.font.SysFont("tahoma", 24)
    gl.font["large"] = pygame.font.SysFont("tahoma", 32)
    # Create a subsurface at 2x the original offset
    subsrect = pygame.Rect(gl.OFFSET_X * 2, gl.OFFSET_Y * 2, gl.MAX_X * 2, gl.MAX_Y * 2)
    gl.display = gl.window.subsurface(subsrect)


def quit_display():
    pygame.quit()


def clear_screen():
    gl.window.fill(pygame.Color(0, 0, 0))


def show():
    info_lines.show()
    pygame.display.flip()


def message(position, txt, font=None, antialias=True,
            color=pygame.Color(255, 255, 255)):
    """
    Display message on the screen. Uses entire surface.

    position - XY(x, y)
    txt - string (can contain newlines)
    font - pygame.Font
    antialias - True or False
    color - pygame.Color

    Return position of next line as XY(x, y).
    """
    font = gl.font["small"] if font is None else font
    lines = txt.split('\n')
    cpos = XY.from_self(position)
    for line in lines:
        lsurf = font.render(line, antialias, color)
        gl.window.blit(lsurf, cpos)
        cpos.y += int(font.get_height() * 1.05)
    return cpos

class InfoLines:
    """
    Several information lines.
    Autoscrolling up.
    Limited visibility time.
    """
    def __init__(self, position, max_lines, max_time):
        self.lines = []
        self.max_time = max_time
        self.max_lines = max_lines
        self.position = position
        self.font = gl.font["xsmall"]
        self.update = 0

    def add(self, text):
        if len(self.lines) == self.max_lines:
            self.lines.pop(0)
        self.lines.append(text)
        self.update = time.perf_counter()

    def show(self):
        pos = self.position.copy()
        for line in self.lines:
            pos = message(pos, line)
        if (time.perf_counter() - self.update > self.max_time) and self.lines:
            self.lines.pop(0)
            self.update = time.perf_counter()

info_lines = InfoLines(XY(180 * 2, 8), 4, 5) #default info lines buffer (scaled 2x)

class DiskInfo:
    def __init__(self, position):
        sprite = gl.info.get_sprite(3) # disk segments
        self.disk = sprite.image.subsurface(pygame.Rect(0, 0, 18, 16))
        self.position = position
        self.disks = 0

    def set_value(self, disks):
        self.disks = min(disks, 3)  # cap at 3 disks max

    def display(self):
        # Blink when 3 disks collected (EB.C:784)
        # if ((disk_num < 3) || (main_cntr & 0x04))
        if self.disks and (self.disks < 3 or (gl.counter & 0x04)):
            position = XY.from_self(self.position)
            scaled_disk = pygame.transform.scale2x(self.disk)
            for d in range(self.disks):
                gl.display.blit(scaled_disk, XY(position.x * 2, position.y * 2))
                position.x += 22

class LEDBar:
    """
    LED bar display
    """
    def __init__(self, position, mapping):
        self.value = 0
        sprite = gl.info.get_sprite(4) # LED indication segments
        self.leds = [sprite.image.subsurface(pygame.Rect(0, 0, 16, 16)),
                     sprite.image.subsurface(pygame.Rect(16, 0, 16, 16)),
                     sprite.image.subsurface(pygame.Rect(32, 0, 16, 16)),
                     sprite.image.subsurface(pygame.Rect(0, 16, 16, 16)),
                     sprite.image.subsurface(pygame.Rect(16, 16, 16, 16))]
        self.position = position
        self.mapping = mapping

    def set_value(self, value):
        self.value = value % 7

    def display(self):
        #self.value = int(time.perf_counter()) % 7
        position = XY.from_self(self.position)
        for led in range(6):
            scaled_led = pygame.transform.scale2x(self.leds[self.mapping[self.value][led]])
            gl.display.blit(scaled_led, XY(position.x * 2, position.y * 2))
            position.x += 16
        scaled_led = pygame.transform.scale2x(self.leds[4])
        gl.display.blit(scaled_led, XY(position.x * 2, position.y * 2))

class Indicators:
    def __init__(self):
        self.left = LEDBar(XY(16, 352),
                           [[2, 3, 3, 3, 3, 3],
                            [0, 3, 3, 3, 3, 3],
                            [0, 0, 3, 3, 3, 3],
                            [0, 0, 1, 3, 3, 3],
                            [0, 0, 1, 2, 3, 3],
                            [0, 0, 1, 2, 2, 3],
                            [0, 0, 1, 2, 2, 2]])
        self.right = LEDBar(XY(512, 352),
                           [[2, 3, 3, 3, 3, 3],
                            [2, 1, 3, 3, 3, 3],
                            [2, 1, 0, 3, 3, 3],
                            [2, 1, 0, 0, 3, 3],
                            [2, 1, 0, 0, 0, 3],
                            [2, 1, 0, 0, 0, 0],
                            [2, 1, 0, 0, 0, 0]]
        )
        self.disks = DiskInfo(XY(144, 352))

    def display(self):
        self.left.display()
        self.right.display()
        self.disks.display()

class StatusLine:
    """
    Handle status line display.
    Singleton by design.
    """
    def __init__(self):
        self.message = ""
        self.font = gl.font["xsmall"]
        self.position = XY(8 * 2, 465 * 2)  # Scale 2x for larger window

    def add(self, text):
        self.message += text

    def show(self):
        global message
        message(self.position, self.message, self.font)
        self.message = ""

status_line = StatusLine()
indicators = None

# -----------------------------------------------------------------------------
# test code below


def main():
    logging.basicConfig(level=logging.DEBUG,
                        format='%(levelname)s: %(funcName)s(): %(message)s')
    init_display()
    loop = True
    while loop:
        clear_screen()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                loop = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    loop = False
        nextp = message(XY(0, 0), "message1\nmessage2")
        message(nextp, "message3\nmessage4")
        show()
    quit_display()


if __name__ == "__main__":
    main()
