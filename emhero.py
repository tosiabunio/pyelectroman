"""Hero's (player's character) code"""

import emglobals as gl
from emglobals import XY
import emdisplay as di
import emdata as da
import emgame as ga
import pygame
import logging

MOVE_STEP = 8
FALL_STEP = 2
MAX_FALL = 24
MAX_JUMP = -21

class PlayerEntity(ga.FSM, ga.Entity):
    """
    Player's entity class, extends ga.Entity.
    Only single instance is allowed.
    Uses Finite State Machine.
    Requires supplying ga.Controller class for player's input.
    """
    __single = None

    def __init__(self, controller):
        if PlayerEntity.__single:
            raise TypeError("Only one instance is allowed!")
        PlayerEntity.__single = self
        # sigleton protection code ends here
        ga.Entity.__init__(self, [da.EmptySprite()], XY(0, 0))
        ga.FSM.__init__(self)
        self.controller = controller
        self.data = da.SpriteSet()
        self.sprites = {}
        self.frames = {}
        self.bbox = pygame.Rect(18, 12, 12, 84)
        self.anim = "RSTAND"
        self.frame = 0
        self.orientation = 1  # 0 left, 1 right
        self.move_vector = XY(0, 0)
        self.to_ground = 0

    def load(self):
        """
        Load player character sprite set and build sprite reference arrays.
        """
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
        self.sprites["LLAND"] = [(32, 33)]
        self.frames["LLAND"] = len(self.sprites["LLAND"])
        # crouching right after jump
        self.sprites["RLAND"] = [(34, 35)]
        self.frames["RLAND"] = len(self.sprites["RLAND"])
        # jumping left
        self.sprites["LJUMP"] = [(4, 8)]
        self.frames["LJUMP"] = len(self.sprites["LJUMP"])
        # jumping right
        self.sprites["RJUMP"] = [(15, 19)]
        self.frames["RJUMP"] = len(self.sprites["RJUMP"])
        # entering teleport (reverse for leaving)
        self.sprites["TELE"] = [(36, 42), (37, 43), (38, 44),
                                 (39, 45), (40, 46), (41, 47)]
        self.frames["TELE"] = len(self.sprites["TELE"])
        self.switch_state(self.state_init)

    def display(self):
        """
        Display player's character at current position using
        calculated sprites taken from the reference arrays.
        """
        position = self.get_position()
        # display top sprite
        sprite = self.sprites[self.anim][self.frame][0]
        sprite = self.data.get_sprite(sprite)
        gl.display.blit(sprite.image, position)
        # display bottom sprite
        position += (0, gl.SPRITE_Y)
        sprite = self.sprites[self.anim][self.frame][1]
        sprite = self.data.get_sprite(sprite)
        gl.display.blit(sprite.image, position)

    def display_collisions(self, color=pygame.Color(255, 128, 255)):
        """Display player's character bounding box."""
        rect = self.get_bbox()
        rect.move_ip(self.get_position())
        pygame.draw.rect(gl.display, color, rect, 1)

    def get_bbox(self):
        """Override Entity.get_bbox() - single bbox for all hero sprites."""
        return self.bbox.copy()

    def get_sides(self):
        """Override Entity.get_sides() - collides from all sides."""
        return {"L": True, "R": True, "T": True, "B": True}

    def get_top(self):
        """Override Entity.get_top() - single bbox for all hero sprites."""
        return self.get_y() + self.bbox.top

    def get_bottom(self):
        """Override Entity.get_bottom() - single bbox for all hero sprites."""
        return self.get_y() + self.bbox.top + self.bbox.height

    def is_touchable(self):
        """Override Entity.is_touchable() - no touching this entity."""
        return False

    def state_init(self, init=False):
        """Handle state initialization."""
        if init:
            self.switch_state(self.state_stand)

    def state_jump(self, init=False):
        """Handle jumping state."""
        if init:
            self.move_vector.y = MAX_JUMP
            self.anim = ("LJUMP", "RJUMP")[self.orientation]
            self.frame = 0
            if self.controller.left and (self.orientation == 0):
                self.move_vector.x = -MOVE_STEP
            if self.controller.right and (self.orientation == 1):
                self.move_vector.x = MOVE_STEP
        self.move_vector.y = min(0, self.move_vector.y + FALL_STEP)
        move = self.check_move(self.move_vector,
                               gl.screen_manager.get_screen(), False)

        if move.y == 0:
            return self.new_state(self.state_fall)
        self.move(False)

    def state_fall(self, init=False):
        """Handle falling state."""
        if init:
            self.anim = ("LJUMP", "RJUMP")[self.orientation]
            self.frame = 0
            self.move_vector.y = 0
        if self.to_ground == 0:
            return self.switch_state(self.state_land)
        else:
            self.move_vector.y = min(MAX_FALL, self.move_vector.y + FALL_STEP)
            if (self.to_ground < self.move_vector.y):
                self.move_vector.y = self.to_ground
            self.move()

    def state_land(self, init=False):
        """Handle landing state."""
        if init:
            self.counter = 2
        self.anim = ("LLAND", "RLAND")[self.orientation]
        self.frame = 0
        self.counter -= 1
        if self.counter == 0:
            return self.new_state(self.state_stand)

    def state_move(self, init=False):
        """Handle moving state."""
        if init:
            self.anim = ("LWALK", "RWALK")[self.orientation]
            self.frame = 0
        if self.to_ground > 0:
            return self.switch_state(self.state_fall)
        else:
            if self.controller.left:
                if self.orientation == 1:
                    return self.switch_state(self.state_turn)
                self.move_vector.x = -MOVE_STEP
            elif self.controller.right:
                if self.orientation == 0:
                    return self.switch_state(self.state_turn)
                self.move_vector.x = MOVE_STEP
            else:
                return self.switch_state(self.state_stand)
            if self.move():
                self.frame = (self.frame + 1) % self.frames[self.anim]
            else:
                self.anim = ("LSTAND", "RSTAND")[self.orientation]
                self.frame = 0
                self.move_vector.x = 0
            if self.controller.up:
                return self.switch_state(self.state_jump)


    def state_turn(self, init=False):
        """Handle turning state."""
        if init:
            self.orientation = 1 - self.orientation
            self.anim = "TURN"
            if self.orientation == 1:
                self.frame = 0
                self.counter = 2
            else:
                self.frame = 2
                self.counter = 2
        else:
            self.counter -= 1
            if self.orientation == 1:
                self.frame += 1
            else:
                self.frame -= 1
            return self.new_state(self.state_move)

    def state_stand(self, init=False):
        """Handle standing state."""
        if init:
            self.move_vector = XY(0, 0)
            if self.to_ground > 0:
                self.switch_state(self.state_fall)
            self.anim = ("LSTAND", "RSTAND")[self.orientation]
            self.frame = 0
        if self.to_ground > 0:
            return self.switch_state(self.state_fall)
        if self.controller.left or self.controller.right:
            return self.switch_state(self.state_move)
        if self.controller.up:
            return self.switch_state(self.state_jump)

    def move(self, reset_x=True):
        """Move player's entitu"""
        move = self.check_move(self.move_vector,
                               gl.screen_manager.get_screen(), True)
        pos = self.get_position()
        move_to = pos + move
        self.set_position(move_to)
        if abs(move.x) < abs(self.move_vector.x):
            if reset_x:
                self.move_vector.x = 0
            return False
        else:
            return True

    def check_bounds(self):
        """Check screen boundaries and change screens if neccessary."""
        bbox = self.get_bbox()
        pos = self.get_position()
        below = self.get_bottom() - gl.MAX_Y
        cs = gl.screen_manager.get_current_screen()
        if below > 0:
            cs += 16 if cs < 240 else -240
            gl.screen_manager.change_screen(cs)
            pos.y = - (bbox.y + bbox.h - below)
            self.set_position(pos)
        center = bbox.centerx + pos.x
        cs = gl.screen_manager.get_current_screen()
        if center < 0:
            cs -= 1 if cs > 0 else -255
            gl.screen_manager.change_screen(cs)
            pos.x = gl.MAX_X + pos.x
            self.set_position(pos)
        elif center > gl.MAX_X:
            cs += 1 if cs < 255 else -255
            gl.screen_manager.change_screen(cs)
            pos.x = pos.x - gl.MAX_X
            self.set_position(pos)

    def update(self):
        """Update player behaviors."""
        # keep track of to ground distance
        self.to_ground = self.check_ground((0, 0),
                                           gl.screen_manager.get_screen())
        di.message((8, 8), "to ground: %d" % self.to_ground)
        # run FSM for the player's entity
        self.run_fsm()
        self.check_bounds()
        di.status_line.add("%s " % str(self.position))
        di.status_line.add("Running state: %s " % self.state.__name__)

# -----------------------------------------------------------------------------
# test code below


def main():
    pass

if __name__ == "__main__":
    main()
