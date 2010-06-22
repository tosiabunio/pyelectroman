"""Display module"""

import emglobals as gl
import pygame
import logging

def init_display():
    pygame.init()
    gl.window = pygame.display.set_mode((640, 480), 0, 32)
    pygame.display.set_caption("Electro Man - Python Version")
    gl.small_font = pygame.font.SysFont("consolas", 10)
    gl.medium_font = pygame.font.SysFont("consolas", 14)
    gl.large_font = pygame.font.SysFont("consolas", 18)
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
    cpos = position
    font = gl.medium_font if font is None else font
    lines = txt.split('\n')
    for line in lines:
        lsurf = font.render(line, antialias, color)
        gl.window.blit(lsurf, cpos)
        cpos = (cpos[0], cpos[1] + int (font.get_height() * 1.05))
    return cpos

# -----------------------------------------------------------------------------
# test code below

def main():
    logging.basicConfig(level=logging.DEBUG,
                        format='%(levelname)s: %(funcName)s(): %(message)s')
    init_display()
    loop = True
    while loop:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                loop = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    loop = False
        nextp = message((0, 0), "message1\nmessage2")
        message(nextp, "message3\nmessage4")
        clear_screen()
        show()
    quit_display()


if __name__ == "__main__":
    main()
