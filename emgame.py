"""Gameplay module"""

import emglobals as gl
import emdata as da
import pygame
import copy

from emglobals import XY


class Controller:
    """
    Class representing player's input.
    Currently only keyboard is reported.
    Joystick and gamepad controllers planned for the future.
    Singleton by design.
    """
    def __init__(self):
        # pylint complains when those are defined via calling clear()
        self.left = False
        self.right = False
        self.up = False
        self.down = False
        self.fire = False
        self.debug = False

    def clear(self):
        self.left = False
        self.right = False
        self.up = False
        self.down = False
        self.fire = False
        self.debug = False

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
        else:
            self.debug = True


class FSM:
    """Very simple Finite State Machine for entities."""
    def __init__(self):
        self.next_state = None
        self.state = lambda: None

    def switch_state(self, state):
        """Enter a new state immediately."""
        self.state = state
        self.state(True)

    def new_state(self, state):
        """Change to a new state in next frame."""
        self.next_state = state

    def run_fsm(self):
        """Cheange to a new state or run current."""
        if self.next_state:
            state = self.next_state
            self.next_state = None
            self.switch_state(state)
        else:
            self.state()


class Entity:
    def __init__(self, sprites, position):
        assert isinstance(sprites, list)
        self.sprites = sprites
        if not isinstance(position, XY):
            raise ValueError("Entity position must by XY() instance.")
        self.position = position
        self.frame = 0
        self.delay = 0
        self.deferred = None
        self.origin = None

    def set_origin(self, screen):
        self.origin = screen

    def set_position(self, position):
        """Set entity position"""
        if not isinstance(position, XY):
            raise ValueError("Entity position must by XY() instance.")
        # create a copy not just reference
        self.position = XY.from_self(position)

    def get_position(self):
        """
        Return entity's position as XY(x, y).
        May be changed by the referring code!
        """
        return self.position

    def copy_position(self):
        """
        Return a copy of entity's position as XY(x, y).
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
        return self.sprites[self.frame].flag("touchable")

    def get_touch(self):
        return self.sprites[self.frame].touch

    def vanish(self):
        """Remove itself from its original screen"""
        # remove from the current screen first
        gl.screen_manager.get_screen().active.remove(self)
        # remove from the level definition
        gl.screen_manager.delete_object(gl.screen_manager.get_screen_number(),
                                        self.position)

    def update(self):
        """Standard empty update method."""
        pass

    def name(self):
        """Return my class name."""
        return self.__class__.__name__

    def display(self):
        """
        Standard display method.
        Use sprite indicate by self.frame
        """
        sprite = self.sprites[self.frame]
        if not sprite.flag("in_front"):
            gl.display.blit(sprite.image, self.get_position())
            if gl.show_collisions and sprite.flag("active"):
                # show collision box or lines
                self.display_collisions(pygame.Color(255, 255, 0))
            return None
        else:
            return self.display_deferred

    def display_deferred(self):
        """Deferred display method usef for in_front sprites."""
        gl.display.blit(self.sprites[self.frame].image, self.get_position())
        if gl.show_collisions:
            # show collision box or lines
            self.display_collisions(pygame.Color(255, 255, 0))

    def display_collisions(self, color=pygame.Color(255, 0, 255)):
        """Display collision lines depending on collision sides."""
        x, y, w, h = self.sprites[self.frame].bbox
        collide = self.sprites[self.frame].collide
        position = self.get_position()
        if collide["T"]:
            sp = position + (x, y)
            ep = position + (x + w - 1, y)
            pygame.draw.line(gl.display, color, sp, ep)
        if collide["L"]:
            sp = position + (x, y)
            ep = position + (x, y + h - 1)
            pygame.draw.line(gl.display, color, sp, ep)
        if collide["R"]:
            sp = position + (x + w - 1, y)
            ep = position + (x + w - 1, y + h - 1)
            pygame.draw.line(gl.display, color, sp, ep)
        if collide["B"]:
            sp = position + (x, y + h - 1)
            ep = position + (x + w - 1, y + h - 1)
            pygame.draw.line(gl.display, color, sp, ep)

    def check_ground(self, screen):
        """
        Return distance from the bottom of entity's bounding box to the ground.
        Negative value means the entity BB is already in the ground (collides
        at the start).
        Offset moves starting point before check is made.
        """
        result = (gl.SCREEN_Y * (gl.SPRITE_Y + 1))
        if screen:
            bbox = self.get_bbox()
            x = bbox.left + self.get_x()
            y = bbox.top + bbox.height + self.get_y()
            w = bbox.width
            h = (gl.SCREEN_Y * gl.SPRITE_Y) - y
            me = pygame.Rect(x, y, w, h)
            #pygame.draw.rect(gl.display, pygame.Color(255, 255, 255), me, 1)
            collided = []
            for obj in screen.collisions:
                you = obj.get_bbox().copy()
                you.move_ip(obj.get_position())
                if me.colliderect(you):
                    collided.append(obj)
            if collided:
                # sorted by y position - probably not necessary anyway
                collided.sort(key=lambda o: o.get_top())
                for coll in collided:
                    # needs to collide from top
                    if coll.get_sides()["T"]:
                        ctop = coll.get_top()
                        result = ctop - y
                        break
        return result

    def check_collision(self, offset, screen, ignore_ground=False):
        """Check collision at offset."""
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
                    elif (offset[1] > 0) and sides["T"] and not ignore_ground:
                        # move down and top side
                        collided = collided if collided else True
                    elif (offset[1] < 0) and sides["B"]:
                        # move up and bottom side
                        collided = collided if collided else True
        return collided

    def get_touching(self, offset, screen):
        """Return objects touching at offset."""
        touched = []
        if screen:
            me = self.get_bbox().copy()
            me.move_ip(self.get_position() + offset)
            for obj in screen.active:
                you = obj.get_bbox().copy()
                you.move_ip(obj.get_position())
                if me.colliderect(you) and obj.is_touchable():
                    touched.append(obj)
        return touched

    def check_move(self, offset, screen, ignore_ground=False):
        """Check move possibility (offset - move vector)."""
        ox, oy = offset
        touched = []
        assert (ox & oy & 0x01) == 0
        if (ox == 0) and (oy == 0):
            touched.extend(self.get_touching((0, 0), screen))
            return XY(0, 0), touched
        nx, ny = 0, 0
        last_not_colliding = 0, 0
        swap_xy = False
        if abs(ox) < abs(oy):
            swap_xy = True
            oy, ox = ox, oy
        sy = (float(oy) // abs(ox)) * 2
        fy = 0.01
        # pylint: disable-msg=W0612
        # mutilsampling check with step 2 pixels
        for step in range(abs(ox) // 2):
            nx += 2 * ((ox > 0) - (ox < 0))
            fy += sy
            ny = int(fy) & ~0x1
            if swap_xy:
                current_offset = ny, nx
            else:
                current_offset = nx, ny
            touched.extend(self.get_touching(current_offset, screen))
            if self.check_collision(current_offset, screen, ignore_ground):
                break
            last_not_colliding = current_offset
        # pylint: enable-msg=W0612
        return XY.from_tuple(last_not_colliding), touched

    def set_initial_delay(self, mode, param):
        """Set initial delay depending on mode or object's position."""
        pos = self.get_position()
        if mode == 0:
            self.delay = ((pos.x // gl.SPRITE_X)
                          + (pos.y // gl.SPRITE_Y)) % (param + 1)
        elif mode == 1:
            self.delay = (pos.x // gl.SPRITE_X) % (param + 1)
        elif mode == 2:
            self.delay = (pos.y // gl.SPRITE_Y) % (param + 1)
        elif mode == 3:
            self.delay = 0
        elif mode == 4:
            self.delay = gl.random(param + 1)
        elif mode == 5:
            self.delay = gl.screen_randoms[pos.x // gl.SPRITE_X] % (param + 1)
        elif mode == 6:
            self.delay = gl.screen_randoms[pos.y // gl.SPRITE_Y] % (param + 1)
        elif mode == 7:
            self.frame = gl.random(len(self.sprites))
            self.delay = 0

class ScreenManager:
    """
    Screen manager class.
    Manages rooms (screens) from loaded level.
    Singleton by design.
    """
    def __init__(self):
        self.current_screen = 0  # current screen
        self.screens = None  # all screens
        self.screen = None  # current screen definition
        self.new_objects = [] # new objects created for current frame

    def add_screens(self, screens):
        self.screens = screens

    def get_screen(self):
        """
        Return active screen definition.
        """
        return self.screen

    def get_screens(self):
        """
        Return all screen definitions.
        """
        return self.screens

    def get_screen_number(self):
        return self.current_screen

    def inspect_screen(self, screen_number):
        """
        Return screen definition for inspection.
        Don't initialize it (the current screen won't change.
        """
        if (screen_number < 0) or (screen_number > 255):
            raise ValueError("Screen number out of range (0, 255).")
        if self.screens:
            return self.screens[screen_number]

    def change_screen(self, screen_number):
        if (screen_number < 0) or (screen_number > 255):
            raise ValueError("Screen number out of range (0, 255).")
        if self.screens:
            gl.init_screen_randoms(screen_number)
            self.current_screen = screen_number
            # changing screen reinitializes its content
            self.screen = da.Screen()
            cs = self.screens[self.current_screen]
            if cs:
                self.screen.background = copy.copy(cs.background)
                self.screen.collisions = copy.copy(cs.collisions)
                self.screen.active = copy.copy(cs.active)
            else:
                self.screen = None

    def delete_object(self, screen, position):
        cs = self.screens[screen]
        for obj in cs.active:
            if obj.position == position:
                cs.active.remove(obj)

    def add_active(self, object):
        """
        Add new objects to waiting queue.
        They will be displayed but not updated in this frame.
        """
        self.new_objects.append(object)

    def update_active(self):
        """
        Update list of active objects with objects from new objects queue.
        """
        if self.new_objects:
            self.screen.active.extend(self.new_objects)
            self.new_objects = []

class ActiveCheckpoint:
    """
    Active checkpoint class.
    References currently active checkpoint.
    Singleton by design.
    """
    def __init__(self):
        self.level = None
        self.screen = None
        self.position = None

    def update(self, level, screen, position):
        self.level = level
        self.screen = screen
        self.position = position

    def get_level(self):
        return self.level

    def get_screen(self):
        return self.screen

    def get_position(self):
        return self.position


class Cycle(Entity):
    def __init__(self, sprites, position):
        Entity.__init__(self, sprites, position)

    def update(self):
        if self.delay > 0:
            self.delay -= 1
        else:
            self.frame = (self.frame + 1) % len(self.sprites)
            self.delay = self.sprites[self.frame].param


class CyclePlus(Entity):
    def __init__(self, sprites, position):
        Entity.__init__(self, sprites, position)
        self.show = False
        self.empty_delay = 0

    def update(self):
        if self.delay > 0:
            self.delay -= 1
        else:
            if not self.show:
                self.show = True
            self.frame = (self.frame + 1) % len(self.sprites)
            if self.frame == 0:
                self.show = False
            if self.show:
                self.delay = self.sprites[self.frame].param
            else:
                self.delay = self.empty_delay

    def display(self):
        if self.show:
            Entity.display(self)

    def is_touchable(self):
        if self.show:
            return Entity.is_touchable(self)

    def get_touch(self):
        if self.show:
            return Entity.get_touch(self)
        else:
            return 0

class Pulse(Entity):
    def __init__(self, sprites, position):
        Entity.__init__(self, sprites, position)
        self.direction = 1  # 1 up -1 down

    def update(self):
        if self.delay > 0:
            self.delay -= 1
        else:
            self.frame += self.direction
            if self.frame < 0:
                self.frame = 0
                self.direction *= -1
            elif self.frame == len(self.sprites):
                self.frame -= 1
                self.direction *= -1
            self.delay = self.sprites[self.frame].param


class PulsePlus(Entity):
    def __init__(self, sprites, position):
        Entity.__init__(self, sprites, position)
        self.direction = 1  # 1 up -1 down
        self.show = False
        self.empty_delay = 0

    def update(self):
        if self.delay > 0:
            self.delay -= 1
        else:
            if not self.show:
                self.show = True
            self.frame += self.direction
            if self.frame < 0:
                self.show = False
                self.frame = 0
                self.direction *= -1
            elif self.frame == len(self.sprites):
                self.frame -= 1
                self.direction *= -1
            if self.show:
                self.delay = self.sprites[self.frame].param
            else:
                self.delay = self.empty_delay

    def display(self):
        if self.show:
            Entity.display(self)

    def is_touchable(self):
        if self.show:
            return Entity.is_touchable(self)

    def get_touch(self):
        if self.show:
            return Entity.get_touch(self)
        else:
            return 0

class Flash(Entity):
    def __init__(self, sprites, position):
        Entity.__init__(self, sprites, position)
        self.show = False

    def display(self):
        if self.show:
            Entity.display(self)

    def update(self):
        if self.delay > 0:
            self.delay -= 1
        else:
            self.show = not self.show
            self.delay = self.sprites[self.frame].param


class FlashPlus(Entity):
    def __init__(self, sprites, position):
        Entity.__init__(self, sprites, position)
        self.show = False

    def display(self):
        if self.show:
            Entity.display(self)

    def update(self):
        if self.delay > 0:
            self.delay -= 1
        else:
            self.show = not self.show
            self.delay = self.sprites[self.frame].param

    def get_touch(self):
        if self.show:
            return Entity.get_touch(self)
        else:
            return 0


class FlashSpecial(Entity):
    def __init__(self, sprites, position):
        Entity.__init__(self, sprites, position)
        self.show = False

    def display(self):
        if self.show:
            Entity.display(self)

    def update(self):
        if self.delay > 0:
            self.delay -= 1
        else:
            self.show = not self.show
            self.delay = 2


class RocketUp(Entity):
    def __init__(self, sprites, position):
        Entity.__init__(self, sprites, position)


class RocketDown(Entity):
    def __init__(self, sprites, position):
        Entity.__init__(self, sprites, position)


class KillingFloor(Entity):
    def __init__(self, sprites, position):
        Entity.__init__(self, sprites, position)


class Monitor(Entity):
    def __init__(self, sprites, position):
        Entity.__init__(self, sprites, position)


class Display(Entity):
    def __init__(self, sprites, position):
        Entity.__init__(self, sprites, position)


class Checkpoint(Entity):
    def __init__(self, sprites, position):
        Entity.__init__(self, sprites, position)


class Teleport(Entity):
    def __init__(self, sprites, position):
        Entity.__init__(self, sprites, position)


class TeleportBase(Entity):
    def __init__(self, sprites, position):
        Entity.__init__(self, sprites, position)


class Exit(Entity):
    def __init__(self, sprites, position):
        Entity.__init__(self, sprites, position)


class CannonLeft(Entity):
    def __init__(self, sprites, position):
        Entity.__init__(self, sprites, position)


class CannonRight(Entity):
    def __init__(self, sprites, position):
        Entity.__init__(self, sprites, position)


class CannonUp(Entity):
    def __init__(self, sprites, position):
        Entity.__init__(self, sprites, position)


class CannonDown(Entity):
    def __init__(self, sprites, position):
        Entity.__init__(self, sprites, position)


class EnemyPlatform(Entity):
    def __init__(self, sprites, position):
        Entity.__init__(self, sprites, position)
        self.shoots = False
        self.anims = None
        self.frames = 0
        self.frame = 0
        self.anim = "MLEFT"

    def update(self):
        pass

    def display(self):
        gl.display.blit(self.anims[self.anim][self.frame].image,
                        self.get_position())

class EnemyFlying(Entity):
    def __init__(self, sprites, position):
        Entity.__init__(self, sprites, position)
        self.shoots = False
        self.anims = None
        self.frames = 0
        self.frame = 0
        self.anim = "MLEFT"

    def update(self):
        pass

    def display(self):
        gl.display.blit(self.anims[self.anim][self.frame].image,
                        self.get_position())

# -----------------------------------------------------------------------------
# test code below

def main():
    pass

if __name__ == "__main__":
    main()
