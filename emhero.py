"""Hero's (player's character) code"""

import emglobals as gl
from emglobals import XY
import emdisplay as di
import emdata as da
import emgame as ga
import pygame
import logging

# horizontal move vector
MOVE_STEP = 8
# jump vectors LUT based on the PC version
JUMP_STEPS = [20, 18, 16, 12, 10, 8, 6, 4, 2, 0]
FALL_STEPS = [2, 4, 6, 8, 10, 12, 16, 18, 20, 22, 24,
              26, 28, 32, 34, 36, 38, 40, 42, 44, 48]

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
        # single very narrow bounding box for all anims
        self.bbox = pygame.Rect(16, 12, 16, 84)
        self.anim = "RSTAND"  # current anim
        self.frame = 0  # current anim frame
        self.orientation = 1  # 0 left, 1 right
        self.move_vector = XY(0, 0)  # move vectors
        self.to_ground = 0  # distance to ground
        self.jump = 0  # index to jump and fall vectors LUT
        self.counter = 0  # used to time some states
        self.screen = None  # current screen definition
        self.touched = None  # objects touched during recent move

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
        """
        Override Entity.is_touchable()
        I'm not sure what can touch the hero
        """
        return False

    def state_init(self, init=False):
        """Handle state initialization."""
        if init:
            self.switch_state(self.state_stand)

    def state_jump(self, init=False):
        """Handle jumping state."""
        if init:
            if self.controller.left:
                self.move_vector.x = -MOVE_STEP
                self.orientation = 0
            if self.controller.right:
                self.move_vector.x = MOVE_STEP
                self.orientation = 1
            self.jump = 0
            self.anim = ("LJUMP", "RJUMP")[self.orientation]
            self.frame = 0
        # vertical movement first
        up = XY(0,-JUMP_STEPS[self.jump])
        pup, touched = self.check_move(up, gl.screen_manager.get_screen(), False)
        self.touched.extend(touched)  # touch will be handled later
        pos = self.get_position()
        pos += pup
        self.set_position(pos)
        if (pup.y > up.y) or up.y == 0:
            # collided or reached max point, switch to fall next frame
            self.new_state(self.state_fall)
        # then horizontal movement
        side = XY(self.move_vector.x, 0)
        pside, touched = self.check_move(side, gl.screen_manager.get_screen(), False)
        self.touched.extend(touched) # touch will be handled later
        pos = self.get_position()
        pos += pside
        self.set_position(pos)
        self.jump += 1

    def state_fall(self, init=False):
        """Handle falling state."""
        if init:
            self.anim = ("LJUMP", "RJUMP")[self.orientation]
            self.frame = 0
            self.move_vector.y = 0
            self.jump = 0
        if self.to_ground == 0:
            return self.switch_state(self.state_land)
        else:
            self.move_vector.y = FALL_STEPS[self.jump]
            if (self.to_ground < self.move_vector.y):
                self.move_vector.y = self.to_ground
            moved = self.move()
            # reset horizontal vector if wall hit while falling
            self.move_vector.x = moved.x
            self.jump += 1
            if self.jump == len(FALL_STEPS):
                # limit max vertical speed and cancel horizontal then
                self.move_vector.x = 0
                self.jump -= 1

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
            if self.controller.up:
                return self.new_state(self.state_jump)
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
            moved = self.move()
            if moved.x != 0:
                self.frame = (self.frame + 1) % self.frames[self.anim]
            else:
                # cannot move farter, play stand animation
                self.anim = ("LSTAND", "RSTAND")[self.orientation]
                self.frame = 0
                self.move_vector.x = 0


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

    def handle_touch(self):
        if self.touched:
            # remove duplicates
            s = set(self.touched)
            self.touched = list(s)
            # process touch
            names = ""
            for obj in self.touched:
                names += " | " + obj.touch()
            di.message((8, 20), "touching: %s" % names)

    def stand(self, position):
        """Place player's model feet at position"""
        rect = self.get_bbox()
        x = position.x - rect.centerx
        y = position.y - rect.bottom
        self.set_position(XY(x, y))

    def move(self):
        """Move player's entitu"""
        move, touched = self.check_move(self.move_vector, self.screen, True)
        self.touched.extend(touched)  # touch will be handled later
        pos = self.get_position()
        move_to = pos + move
        self.set_position(move_to)
        return move

    def check_touch(self):
        self.touched.extend(self.get_touching((0, 0), self.screen))

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
        # intialize some variables
        self.screen = gl.screen_manager.get_screen()
        self.touched = []
        # check for touching objects at current position
        self.check_touch()
        # keep track of to ground distance
        self.to_ground = self.check_ground((0, 0), self.screen)
        di.message((8, 8), "to ground: %d" % self.to_ground)
        # run FSM for the player's entity
        if not self.controller.debug:
            self.run_fsm()
        # check for screen boundaries (thus screen change)
        self.check_bounds()
        # handle objects touched
        self.handle_touch()
        # display some status information
        di.status_line.add("%s" % str(self.position))
        di.status_line.add(" | screen: %d" %
                           gl.screen_manager.get_current_screen())
        di.status_line.add(" | running state: %s " % self.state.__name__)
        if self.touched:
            di.status_line.add("| touching: %d" % len(self.touched))


# -----------------------------------------------------------------------------
# test code below


def main():
    pass

if __name__ == "__main__":
    main()
