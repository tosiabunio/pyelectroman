"""Gameplay module"""

import emglobals as gl
from emglobals import XY
import emdisplay as di
import pygame
import logging


class Controller:
    """
    Class representing player's input.
    Currently only keyboard is reported.
    Joystick and gamepad controllers planned for the future.
    """
    __single = None
    def __init__(self):
        if Controller.__single:
            raise TypeError, "Only one instance is allowed!"
        Controller.__single = self
        self.left = False
        self.right = False
        self.up = False
        self.down = False
        self.fire = False

    def clear(self):
        self.left = False
        self.right = False
        self.up = False
        self.down = False
        self.fire = False

    def update(self):
        """Update controller settings"""
        self.clear()
        keys = pygame.key.get_pressed()
        mods = pygame.key.get_mods()
        if not (mods & (pygame.KMOD_CTRL |
                        pygame.KMOD_SHIFT |
                        pygame.KMOD_ALT)):
            if keys[pygame.K_LEFT]:
                self.left = True
            if keys[pygame.K_RIGHT]:
                self.right = True
            if keys[pygame.K_UP]:
                self.up = True
            if keys[pygame.K_DOWN]:
                self.down = True
            if keys[pygame.K_SPACE]:
                self.fire = True


class FSM:
    """Very simple Finite State Machine for entities."""
    def __init__(self):
        self.next_state = None
        self.state = lambda: None

    def enter_state(self, state):
        """Enter a new state immediately."""
        logging.debug("Entering state: %s", state.__name__)
        self.state = state
        self.state(True)

    def exit_state(self, state):
        """Change to a new state in next frame."""
        self.next_state = state

    def run_fsm(self):
        """Cheange to a new state or run current."""
        if self.next_state:
            state = self.next_state
            self.next_state = None
            self.enter(state)
        else:
            self.state()


class Entity:
    def __init__(self, sprites, position, initial=0):
        assert isinstance(sprites, list)
        self.sprites = sprites
        self.initial = initial
        if not isinstance(position, XY):
            raise ValueError, "Entity position must by XY() instance."
        self.position = position
        self.frame = 0
        self.delay = 0
        self.counter = 0

    def set_position(self, position):
        """Set entity position"""
        if not isinstance(position, XY):
            raise ValueError, "Entity position must by XY() instance."
        # create a copy not just reference
        self.position = XY.from_self(position)

    def get_position(self):
        """
        Return entity's position as XY(x, y).
        The copy is returned to prevent overwriting by referring code.
        """
        return self.position.copy()

    def get_x(self):
        return self.position.x

    def get_y(self):
        return self.position.y

    def get_bbox(self):
        """Return bounding box for current sprite frame as pygame.Rect."""
        return self.sprites[self.frame].bbox

    def get_sides(self):
        """Return boolean table with colliding sides for the current sprite."""
        return self.sprites[self.frame].collide

    def get_top(self):
        return self.sprites[self.frame].bbox.top + self.get_y()

    def is_touchable(self):
        return (self.sprites[self.frame].status[0] & 0x40) != 0

    def touch(self):
        """Standard touch handler."""
        pass

    def update(self):
        """Standard update method."""
        pass

    def display(self):
        gl.display.blit(self.sprites[self.frame].image, self.get_position())

    def display_collisions(self, color=pygame.Color(255, 0, 255)):
        x, y, w, h = self.sprites[0].bbox
        collide = self.sprites[0].collide
        position = self.get_position()
        if collide["T"]:
            sp = position + (x, y)
            ep = position + (x + w - 1, y)
            pygame.draw.line(gl.display, color, sp, ep, 1)
        if collide["L"]:
            sp = position + (x, y)
            ep = ep = position + (x, y + h - 1)
            pygame.draw.line(gl.display, color, sp, ep, 1)
        if collide["R"]:
            sp = position + (x + w - 1, y)
            ep = position + (x + w - 1, y + h - 1)
            pygame.draw.line(gl.display, color, sp, ep, 1)
        if collide["B"]:
            sp = position + (x, y + h - 1)
            ep = position + (x + w - 1, y + h - 1)
            pygame.draw.line(gl.display, color, sp, ep, 1)

    def check_ground(self, offset, screen):
        """
        Return distance from the bottom of entity's bounding box to the ground.
        Negative value means the entity BB is already in the ground (collides
        at the start).
        Offset moves starting point before check is made.
        """
        result = (gl.SCREEN_Y * (gl.SPRITE_Y + 1))
        if screen:
            bbox = self.get_bbox()
            x = bbox.left + (bbox.width / 2) + self.get_x() + offset[0]
            # 2 pixels up to always return negative when below ground
            y = bbox.top + bbox.height + self.get_y() + offset[1] - 2
            w = 2
            h = (gl.SCREEN_Y * gl.SPRITE_Y) - y + 2
            me = pygame.Rect(x, y, w, h)
            collided = []
            for obj in screen.collisions:
                you = obj.get_bbox().copy()
                you.move_ip(obj.get_position())
                if me.colliderect(you):
                    collided.append(obj)
            if collided:
                # sorted by y position - probably not necessary anyway
                collided.sort(key=lambda o: o.get_top())
                ctop = collided[0].get_top()
                # corrected for 2 pixels added above
                result = ctop - y - 2
        return result

    def check_collision(self, offset, screen, ignore_ground):
        """Check collision"""
        collided = False
        if screen:
            me = self.get_bbox().copy()
            me.move_ip(self.get_position() + offset)
            for obj in screen.collisions:
                you = obj.get_bbox().copy()
                you.move_ip(obj.get_position())
                if me.colliderect(you):
                    sides = obj.get_sides()
                    if (offset[0] > 0) and sides["L"]:
                        # move right and left side
                        collided = collided if collided else True
                    elif (offset[0] < 0) and sides["R"]:
                        # move left and right side
                        collided = collided if collided else True
                    elif (offset[1] > 0) and sides["T"]:
                        # move down and top side
                        collided = collided if collided else True
                    elif (offset[1] < 0) and sides["B"] and not ignore_ground:
                        # move up and bottom side
                        collided = collided if collided else True
        return collided

    def check_move(self, offset, screen, ignore_ground=False):
        """Check move"""
        ox, oy = offset
        assert (ox & oy & 0x01) == 0
        if (ox == 0) and (oy == 0):
            return (0, 0)
        nx, ny = 0, 0
        last_not_colliding = 0, 0
        swap_xy = False
        if abs(ox) < abs(oy):
            swap_xy = True
            oy, ox = ox, oy
        sy = (float(oy) / abs(ox)) * 2
        fy = 0.01
        # pylint: disable-msg=W0612
        for step in range(abs(ox) / 2):
            nx += 2 * cmp(ox, 0)
            fy += sy
            ny = int(fy) & ~0x1
            if swap_xy:
                current_offset = ny, nx
            else:
                current_offset = nx, ny
            collision = self.check_collision(current_offset, screen,
                                             ignore_ground)
            if not collision:
                last_not_colliding = current_offset
            else:
                break
        # pylint: enable-msg=W0612
        return last_not_colliding


class ActiveCheckpoint:
    __single = None
    def __init__(self):
        if ActiveCheckpoint.__single:
            raise TypeError, "Only one instance is allowed!"
        ActiveCheckpoint.__single = self
        # sigleton protection code ends here
        self.level = 0
        self.position = (0, 0)

    def update(self, level, position):
        self.level = level
        self.position = position

    def get_level(self):
        return self.level

    def get_position(self):
        return self.position


class Cycle(Entity):
    def __init___(self, sprites, position):
        Entity.__init__(self, sprites, position)

    def update(self):
        pass


class CyclePlus(Entity):
    def __init___(self, sprites, position):
        Entity.__init__(self, sprites, position)

    def update(self):
        pass


class Pulse(Entity):
    def __init___(self, sprites, position):
        Entity.__init__(self, sprites, position)

    def update(self):
        pass


class PulsePlus(Entity):
    def __init___(self, sprites, position):
        Entity.__init__(self, sprites, position)

    def update(self):
        pass


class Flash(Entity):
    def __init___(self, sprites, position):
        Entity.__init__(self, sprites, position)

    def update(self):
        pass


class FlashPlus(Entity):
    def __init___(self, sprites, position):
        Entity.__init__(self, sprites, position)

    def update(self):
        pass


class RocketUp(Entity):
    def __init___(self, sprites, position):
        Entity.__init__(self, sprites, position)

    def update(self):
        pass


class RocketDown(Entity):
    def __init___(self, sprites, position):
        Entity.__init__(self, sprites, position)

    def update(self):
        pass


class KillingFloor(Entity):
    def __init___(self, sprites, position):
        Entity.__init__(self, sprites, position)

    def update(self):
        pass


class Monitor(Entity):
    def __init___(self, sprites, position):
        Entity.__init__(self, sprites, position)

    def update(self):
        pass


class Display(Entity):
    def __init___(self, sprites, position):
        Entity.__init__(self, sprites, position)

    def update(self):
        pass


class Checkpoint(Entity):
    def __init___(self, sprites, position):
        Entity.__init__(self, sprites, position)

    def update(self):
        pass


class Teleport(Entity):
    def __init___(self, sprites, position):
        Entity.__init__(self, sprites, position)

    def update(self):
        pass


class Exit(Entity):
    def __init___(self, sprites, position):
        Entity.__init__(self, sprites, position)

    def update(self):
        pass


class CannonLeft(Entity):
    def __init___(self, sprites, position):
        Entity.__init__(self, sprites, position)

    def update(self):
        pass


class CannonRight(Entity):
    def __init___(self, sprites, position):
        Entity.__init__(self, sprites, position)

    def update(self):
        pass


class CannonUp(Entity):
    def __init___(self, sprites, position):
        Entity.__init__(self, sprites, position)

    def update(self):
        pass


class CannonDown(Entity):
    def __init___(self, sprites, position):
        Entity.__init__(self, sprites, position)

    def update(self):
        pass


class FlashSpecial(Entity):
    def __init___(self, sprites, position):
        Entity.__init__(self, sprites, position)

    def update(self):
        pass


# -----------------------------------------------------------------------------
# test code below

def main():
    pass

if __name__ == "__main__":
    main()
