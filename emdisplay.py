"""Display module"""

import emglobals as gl
from emglobals import XY
import pygame
import logging

def init_display():
    pygame.init()
    gl.window = pygame.display.set_mode((640, 480), 0, 32)
    pygame.display.set_caption("Electro Man - Python Version")
    gl.font["xsmall"] = pygame.font.SysFont("tahoma", 8)
    gl.font["small"] = pygame.font.SysFont("tahoma", 10)
    gl.font["normal"] = pygame.font.SysFont("tahoma", 12)
    gl.font["large"] = pygame.font.SysFont("tahoma", 16)
    subsrect = pygame.Rect(gl.OFFSET_X, gl.OFFSET_Y,
                           gl.SCREEN_X * gl.SPRITE_X,
                           gl.SCREEN_Y * gl.SPRITE_Y)
    gl.display = gl.window.subsurface(subsrect)


def quit_display():
    pygame.quit()


def clear_screen():
    gl.window.fill(pygame.Color(0, 0, 0))


def show():
    pygame.display.flip()


def message(position, txt, font=None, antialias=False,
            color=pygame.Color(255, 255, 255)):
    """
    Display message on the screen. Uses entire surface.

    position - (x, y) (also XY(x, y))
    txt - string (can contain newlines)
    font - pygame.Font
    antialias - True or False
    color - pygame.Color

    Return position of next line as XY(x, y).
    """
    if isinstance(position, XY):
        cpos = position.as_tuple()
    else:
        cpos = position
    font = gl.font["small"] if font is None else font
    lines = txt.split('\n')
    for line in lines:
        lsurf = font.render(line, antialias, color)
        gl.window.blit(lsurf, cpos)
        cpos = XY(cpos[0], cpos[1] + int (font.get_height() * 1.05))
    return cpos

class StatusLine:
    """
    Handle status line display.
    """
    __single = None
    def __init__(self):
        if StatusLine.__single:
            raise TypeError, "Only one instance is allowed!"
        StatusLine.__single = self
        self.message = ""
        self.font = gl.font["xsmall"]
        self.position = XY(8, 465)

    def add(self, text):
        self.message += text

    def show(self):
        message(self.position, self.message, self.font)
        self.message = ""

status_line = StatusLine()

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
        nextp = message((0, 0), "message1\nmessage2")
        message(nextp, "message3\nmessage4")
        show()
    quit_display()


if __name__ == "__main__":
    main()
