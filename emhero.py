"""Hero (player character) code"""

import emglobals as gl
from emglobals import XY, tuple_add
import emdisplay as di
import emdata as da
import emgame as ga
import logging
import pygame

class PlayerEntity(ga.FSM, ga.Entity):
    __single = None
    def __init__(self, controller):
        if PlayerEntity.__single:
            raise TypeError, "Only one instance is allowed!"
        PlayerEntity.__single = self
        # sigleton protection code ends here
        ga.Entity.__init__(self, [da.EmptySprite()], XY(0, 0))
        ga.FSM.__init__(self)
        self.controller = controller
        self.data = da.SpriteSet()
        self.sprites = {}
        self.frames = {}
        self.bbox = pygame.Rect(18, 12, 12, 84)
        self.vstate = "RSTAND"
        self.orientation = 1 # 0 left, 1 right
        self.move_vector = [0, 0]

    def load(self):
        # load hero sprites
        self.data.load("hero")
        # prepare animation table
        # standing facing left
        self.sprites["LSTAND"] = [(0, 1)]
        self.frames["LSTAND"] = len(self.sprites["LSTAND"])
        # standing facing right
        self.sprites["RSTAND"] = [(2, 3)]
        self.frames["RSTAND"] = len(self.sprites["RSTAND"])
        # walking left
        self.sprites["LWALK"] = [(4, 5), (4, 6), (4, 7), (4, 8),
                                 (4, 9), (4, 10), (4, 11), (4, 12),
                                 (4, 13), (4, 14)]
        self.frames["LWALK"] = len(self.sprites["LWALK"])
        # walking right
        self.sprites["RWALK"] = [(15, 16), (15, 17), (15, 18), (15, 19),
                                 (15, 20), (15, 21), (15, 22), (15, 23),
                                 (15, 24), (15, 25)]
        self.frames["RWALK"] = len(self.sprites["RWALK"])
        # turning left to right (play in reverse for right to left turn)
        self.sprites["TURN"] = [(26, 29), (27, 30), (28, 31)]
        self.frames["TURN"] = len(self.sprites["TURN"])
        # crouching left after jump
        self.sprites["LCROUCH"] = [(32, 33)]
        self.frames["LCROUCH"] = len(self.sprites["LCROUCH"])
        # crouching right after jump
        self.sprites["RCROUCH"] = [(34, 35)]
        self.frames["RCROUCH"] = len(self.sprites["RCROUCH"])
        # entering teleport (reverse for leaving)
        self.sprites["TELE"] = [(36, 42), (37, 43), (38, 44),
                                 (39, 45), (40, 46), (41, 47)]
        self.frames["TELE"] = len(self.sprites["TELE"])
        self.enter_state(self.state_stand)

    def display(self):
        position = self.get_position()
        # display top sprite
        sprite = self.sprites[self.vstate][self.frame][0]
        sprite = self.data.get_sprite(sprite)
        gl.display.blit(sprite.image, position)
        # display bottom sprite
        position = tuple_add(position, (0, gl.SPRITE_Y))
        sprite = self.sprites[self.vstate][self.frame][1]
        sprite = self.data.get_sprite(sprite)
        gl.display.blit(sprite.image, position)

    def display_collisions(self, color=pygame.Color(255, 128, 255)):
        rect = self.bbox.copy()
        rect.move_ip(self.get_position())
        pygame.draw.rect(gl.display, color, rect, 1)

    def get_bbox(self):
        """Overrides Entity.get_bbox() - single bbox for all hero sprites"""
        return self.bbox

    def get_sides(self):
        """Overrides Entity.get_sides() - collides from all sides"""
        return {"L" : True, "R": True, "T" : True, "B" : True}

    def get_top(self):
        """Overrides Entity.get_top() - single bbox for all hero sprites"""
        return self.bbox.top + self.get_x()

    def get_bottom(self):
        """Overrides Entity.get_bottom() - single bbox for all hero sprites"""
        return self.get_x() + self.bbox.top + self.bbox.height

    def is_touchable(self):
        """Overrides Entity.is_touchable() - no touch handler"""
        return False

    def state_fall(self, init=False):
        if init:
            self.vstate = ("LSTAND", "RSTAND")[self.orientation]
            self.frame = 0
            self.move_vector[1] = -2
        else:
            self.exit_state(self.state_stand)

    def state_move(self, init=False):
        if init:
            self.vstate = ("LWALK", "RWALK")[self.orientation]
            self.frame = 0
        if self.controller.left or self.controller.right:
            pass
        else:
            self.exit_state(self.state_stand)

    def state_stand(self, init=False):
        to_ground = self.check_ground((0, 0), gl.screen)
        if init:
            if to_ground > 0:
                self.enter_state(self.state_fall)
        else:
            if to_ground > 0:
                self.enter_state(self.state_fall)
            self.vstate = ("LSTAND", "RSTAND")[self.orientation]
            self.frame = 0
            if self.controller.left or self.controller.right:
                self.enter_state(self.state_move)

    def update(self):
        self.run_fsm()

# -----------------------------------------------------------------------------
# test code below

def main():
    pass

if __name__ == "__main__":
    main()
