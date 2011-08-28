"""Hero's (player's character) code"""

import emglobals as gl
from emglobals import XY
import emdisplay as di
import emdata as da
import emgame as ga
import pygame
import copy
import logging

# horizontal move vector
MOVE_STEP = 8
# jump vectors LUT based on the PC version
JUMP_STEPS = [20, 18, 16, 12, 10, 8, 6, 4, 2, 0]
FALL_STEPS = [2, 4, 6, 8, 10, 12, 16, 18, 20, 22, 24,
              26, 28, 32, 34, 36, 38, 40, 42, 44, 48]

# touch procedure names
touch_procs = {0 : "none", 1 : "battery", 2 : "teleport", 3 :"checkpoint",
               4 : "killer", 5 : "floppy", 6 :  "exit",
               7 : "special good", 8 : "special bad"}


#noinspection PySimplifyBooleanCheck,PyArgumentEqualDefault
class PlayerEntity(ga.FSM, ga.Entity):
    """
    Player's entity class, extends ga.Entity.
    Only single instance is allowed.
    Uses Finite State Machine.
    Requires supplying ga.Controller class for player's input.
    Singleton by design.
    """
    def __init__(self, controller):
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
        self.teleport_target = None  # tuple holding teleport destination target
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
        self.keys = 0  # keys needed to open the exit
        self.power = 0  # weapon's battery power
        self.temp = 0  # weapons's temperature increase
        self.fired = False  # to disable repeated shots
        self.ammo = 0  # current ammo left
        self.magazine = [0, 20, 15, 25, 10, 15] # # of shots for each weapon level
        self.heat = [0,  1,  2,  1,  4,  3] # temperature increase for each level
        self.cooldown = 0  # cooldown counter

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
        if gl.show_collisions:
            # show collision box and ground testing point
            self.display_collisions()

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
        up = XY(0, -JUMP_STEPS[self.jump])
        pup, touched = self.check_move(up, self.screen)
        self.touched.extend(touched)  # touch will be handled later
        pos = self.get_position()
        pos += pup
        self.set_position(pos)
        if (pup.y > up.y) or up.y == 0:
            # collided or reached max point, switch to fall next frame
            self.new_state(self.state_fall)
        # then horizontal movement
        side = XY(self.move_vector.x, 0)
        pside, touched = self.check_move(side, self.screen)
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
            if self.to_ground < self.move_vector.y:
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
        """
        Handle standing state.
        """
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

    def state_teleport_out(self, init=False):
        """
        Teleport fade out state (teleport out)
        """
        if init:
            self.anim = "TELE"
            self.counter = self.frames[self.anim] - 1
            self.frame = 0
        if not init:
            if self.counter == 0:
                return self.new_state(self.state_teleport_in)
            self.frame += 1
            self.counter -= 1

    def state_teleport_in(self, init=False):
        """
        Teleport fade in state (teleport in)
        """
        if self.teleport_target:
            if self.teleport_target[0] != gl.screen_manager.get_screen_number():
                gl.screen_manager.change_screen(self.teleport_target[0])
            self.set_position(self.teleport_target[1] + XY(0, -gl.SPRITE_Y * 2))
        if init:
            self.anim = "TELE"
            self.counter = self.frames[self.anim] - 1
            self.frame = self.frames[self.anim] - 1
        if not init:
            if self.counter == 0:
                return self.new_state(self.state_stand)
            self.frame -= 1
            self.counter -= 1

    def find_teleport_target(self, start_pos):
        """
        Find a suitable teleport target.
        The first one above the current one on the same X position qualifies.
        If not present on current level, check all levels above wrapping around
        map boundary and continuing from the bottom.
        """
        sp = copy.copy(start_pos)
        self.teleport_target = None
        sn = gl.screen_manager.get_screen_number()
        while not self.teleport_target:
            tp = {}
            screen = gl.screen_manager.inspect_screen(sn)
            if screen:
                for obj in screen.active:
                    if isinstance(obj, ga.Teleport):
                        if obj.get_position().x == sp.x:
                            tp[obj.get_position().y] = obj
            if tp:
                for y in range(sp.y, 0, -gl.SPRITE_Y):
                    if y in tp:
                        self.teleport_target = (sn, XY(sp.x, y))
                        break
            sp.y = (gl.SCREEN_Y + 1) * gl.SPRITE_Y
            sn = (sn - 16) % 256

    def select_weapon(self, power):
        self.power = power
        self.ammo = self.magazine[power]

    def inc_power(self):
        """
        Increase available power.
        """
        if self.power < 6:
            self.select_weapon(self.power + 1)
            di.info_lines.add("battery collected")

    def power_and_cooldown(self):
        """
        Handle power usage and weapon cooldown.
        Display indicators.
        """
        if self.power == 0:
            self.temp = 0
        if self.power > 0 and self.temp == 0:
            self.temp = 1
        if self.temp > 1:
            if self.cooldown:
                self.cooldown -= 1
            else:
                self.temp -= 1
                self.cooldown = 4

    def show_hud(self):
        # display disks if collected
        if not gl.counter % 20:
            gl.disks += 1
        di.indicators.disks.set_value(gl.disks)
        # display LED indicators
        di.indicators.left.set_value(self.temp)
        if self.ammo < 3 and self.power:
            # handle low ammo warning blinking
            if gl.counter & 0x02:
                di.indicators.right.set_value(self.power - 1)
            else:
                di.indicators.right.set_value(self.power)
        else:
            di.indicators.right.set_value(self.power)

    def handle_touch(self):
        if self.touched:
            # remove duplicates
            s = set(self.touched)
            self.touched = list(s)
            # process touch
            names = ""
            for obj in self.touched:
                # inform touched entity about the touch event
                touch_type = obj.get_touch()
                names += touch_procs[touch_type] + " "
                # handle touch according to its type
                if touch_type == 1:
                    # battery
                    self.inc_power()
                    obj.vanish()  # remove battery from the map
                elif touch_type == 2:
                    if self.controller.down:
                        self.find_teleport_target(obj.get_position())
                        self.new_state(self.state_teleport_out)
                    # teleport
                    pass
                elif touch_type == 3:
                    # checkpoint
                    pass
                elif touch_type == 4:
                    # killer
                    pass
                elif touch_type == 5:
                    # floppy
                    obj.vanish()  # remove floppy from the map
                    pass
                elif touch_type == 6:
                    # exit
                    pass
                elif touch_type == 7:
                    # special good
                    pass
                elif touch_type == 8:
                    # special bad
                    pass
            di.message(XY(8, 20), "touch: %s" % names)

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
        cs = gl.screen_manager.get_screen_number()
        if below > 0:
            cs += 16 if cs < 240 else -240
            gl.screen_manager.change_screen(cs)
            pos.y = - (bbox.y + bbox.h - below)
            self.set_position(pos)
        center = bbox.centerx + pos.x
        cs = gl.screen_manager.get_screen_number()
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
        self.to_ground = self.check_ground(self.screen)
        di.message(XY(8, 8), "to ground: %d" % self.to_ground)
        # run FSM for the player's entity
        if not self.controller.debug:
            self.run_fsm()
        # handle shooting
        if self.controller.fire:
            if self.state in [self.state_jump,
                              self.state_fall,
                              self.state_land,
                              self.state_move,
                              self.state_stand]:
                if not self.fired:
                    self.fire_weapon()
                    self.fired = True
        else:
            self.fired = False
        # check for screen boundaries (thus screen change)
        self.check_bounds()
        # handle objects touched
        self.handle_touch()
        # handle weapon's power usage and cooldown
        self.power_and_cooldown()
        # display HUD
        self.show_hud()
        # display some status information
        di.status_line.add("%s" % str(self.position))
        di.status_line.add(" | screen: %d" %
                           gl.screen_manager.get_screen_number())
        di.status_line.add(" | running state: %s " % self.state.__name__)
        if self.touched:
            di.status_line.add(" | touching: %d" % len(self.touched))
        di.status_line.add(" | ammo: %d" % self.ammo)

    projectile_offset = {
        "1_L" : XY(-48, 0),
        "1_R" : XY(48, 0),
        "2_L" : XY(-48, 0),
        "2_R" : XY(48, 0),
        "3_L" : XY(-48, 0),
        "3_R" : XY(48, 0),
        "4_L" : XY(-48, 0),
        "4_R" : XY(48, 0),
        "5_L" : XY(-48, 0),
        "5_R" : XY(48, 0),
    }

    def fire_weapon(self):
        """
        Fire the weapon!
        """
        def add_projectile(type, pos=None):
            if not pos:
                ppos = self.get_position().copy() + self.projectile_offset[type]
            else:
                ppos = pos
            projectile = Projectile(type)
            projectile.set_position(ppos)
            gl.screen_manager.add_active(projectile)
            return projectile

        if self.power:
            t = self.heat[self.power]
            if self.temp + t <= 6:
                self.temp += t
                self.cooldown = 4
                self.ammo -= 1
                di.info_lines.add("shot fired")
                if 1 <= self.power <= 5:
                    types = ["%d_L" % self.power, "%d_R" % self.power]
                    add_projectile(types[self.orientation])
                if not self.ammo:
                    self.select_weapon(self.power - 1)


#noinspection PyArgumentEqualDefault
class Projectile(ga.Entity):
    def __init__(self, type):
        ga.Entity.__init__(self, [da.EmptySprite()], XY(0, 0))
        self.type = type
        self.sprites = gl.weapons.weapon[type].anims
        self.frames = gl.weapons.weapon[type].frames
        self.step = (-1 if type[2] == "L" else 1) * gl.SPRITE_X / 4

    def update(self):
        self.frame = (self.frame + 1) % len(self.sprites)
        self.position.x += self.step
        if self.position.x > gl.SCREEN_X * gl.SPRITE_X or self.position.x < - gl.SPRITE_X:
            self.vanish()

    def display(self):
        if self.type[0] != "5":
            ga.Entity.display(self)
        else:
            sprite = self.sprites[0]
            gl.display.blit(sprite.image, self.get_position())
            sprite = self.sprites[1]
            gl.display.blit(sprite.image, self.get_position() + XY(0, gl.SPRITE_Y))

# -----------------------------------------------------------------------------
# test code below


def main():
    pass

if __name__ == "__main__":
    main()
