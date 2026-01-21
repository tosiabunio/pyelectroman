"""Gameplay module"""

import emglobals as gl
import emdata as da
from emglobals import XY
import pygame
import copy
import logging


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
        # Original sprite index in level data (for broken sprite lookup)
        self.sprite_index = None

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
        logging.debug("vanish() called for %s at %s", self.name(), self.position)
        # remove from the current screen first
        try:
            gl.screen_manager.get_screen().active.remove(self)
            logging.debug("  Removed from current screen.active")
        except ValueError:
            logging.debug("  NOT in current screen.active")
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
            # Scale sprite 2x and position 2x for larger window
            scaled_image = pygame.transform.scale2x(sprite.image)
            scaled_pos = XY(self.get_position().x * 2, self.get_position().y * 2)
            gl.display.blit(scaled_image, scaled_pos)
            if gl.show_collisions and sprite.flag("active"):
                # show collision box or lines
                self.display_collisions(pygame.Color(255, 255, 0))
            return None
        else:
            return self.display_deferred

    def display_deferred(self):
        """Deferred display method usef for in_front sprites."""
        # Scale sprite 2x and position 2x for larger window
        scaled_image = pygame.transform.scale2x(self.sprites[self.frame].image)
        scaled_pos = XY(self.get_position().x * 2, self.get_position().y * 2)
        gl.display.blit(scaled_image, scaled_pos)
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
        sy = (float(oy) / abs(ox)) * 2
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
                logging.debug("change_screen(%d): Loaded %d active entities from level data",
                             screen_number, len(cs.active))
            else:
                self.screen = None

    def delete_object(self, screen, position):
        cs = self.screens[screen]
        found = False
        for obj in cs.active:
            if obj.position == position:
                cs.active.remove(obj)
                logging.debug("delete_object: Removed %s at %s from screen %d level data",
                             obj.name(), position, screen)
                found = True
                break
        if not found:
            logging.debug("delete_object: No object found at %s in screen %d level data",
                         position, screen)

    def add_to_level_data(self, screen, entity):
        """Add an entity to the level definition so it persists across screen changes."""
        cs = self.screens[screen]
        if cs:
            cs.active.append(entity)
            logging.debug("add_to_level_data: Added %s at %s to screen %d",
                         entity.name(), entity.position, screen)

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

    def reset_level(self):
        """
        Reset level to pristine state on player death.
        Matches C code init_level() (EB.C:1382-1405):
        - memcpy(map, level_map, sizeof(map)) - restore all screens
        - Remove already collected disks from restored screens
        """
        # Recreate all screens from level data (EB.C:1390)
        self.screens = gl.level.reset_screens()

        # Remove collected disks from the restored level (EB.C:1391-1395)
        # In C: for (i = 0; i < disk_num; i++) MAP_REMOVE(disk_x[i], disk_y[i])
        for screen_num, position in gl.disk_positions:
            cs = self.screens[screen_num]
            if cs:
                for obj in cs.active[:]:  # iterate over copy to allow removal
                    if obj.position == position:
                        cs.active.remove(obj)
                        logging.debug("reset_level: Removed collected disk at %s from screen %d",
                                     position, screen_num)
                        break

        logging.info("reset_level: Level reset, %d collected disks preserved", len(gl.disk_positions))

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
        self.position = copy.copy(position)  # copy to avoid reference issues
        logging.info("Checkpoint updated: level=%d, screen=%d, pos=%s",
                     level, screen, position)

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
    """
    Rocket that fires upward when player passes below.
    Based on EB_ENEM.C:400-484 (rocket_proc).
    """
    def __init__(self, sprites, position):
        Entity.__init__(self, sprites, position)
        self.state = "waiting"
        self.speed = 0
        self.initialized = False

    def update(self):
        if not self.initialized:
            # Get speed from sprite param
            sprite = self.sprites[0] if self.sprites else None
            self.speed = sprite.param if sprite and sprite.param > 0 else 4
            self.initialized = True

        if self.state == "waiting":
            self.check_trigger()
        else:
            self.fly()

    def check_trigger(self):
        """Fire when player is aligned below - EB_ENEM.C:422-441"""
        if not gl.player:
            return

        player_pos = gl.player.get_position()
        my_pos = self.get_position()
        bbox = self.get_bbox()

        # Player center X
        player_cx = player_pos.x + 24  # Approximate player center
        player_top = player_pos.y

        # Check horizontal alignment (XB-8 to XE+8)
        xb = my_pos.x + bbox.x - 8
        xe = my_pos.x + bbox.x + bbox.width + 8
        my_bottom = my_pos.y + bbox.y + bbox.height

        # Player must be BELOW rocket (player top > rocket bottom)
        if xb < player_cx < xe and player_top > my_bottom:
            # 1/8 chance per frame to fire (EB_ENEM.C:436)
            if gl.random(8) == 0:
                self.state = "flying"
                logging.debug("RocketUp triggered at %s", my_pos)

    def fly(self):
        """Move upward until collision - EB_ENEM.C:442-448"""
        self.position.y -= self.speed

        # Animate
        self.frame = (self.frame + 1) % len(self.sprites) if self.sprites else 0

        # Wall collision
        screen = gl.screen_manager.get_screen()
        if screen and self.check_collision(XY(0, -self.speed), screen):
            from emhero import put_explosion
            put_explosion(self.position.x, self.position.y)
            self.vanish()
            return

        # Off-screen
        if self.position.y < -gl.SPRITE_Y:
            self.vanish()


class RocketDown(Entity):
    """
    Rocket that fires downward when player passes above.
    Based on EB_ENEM.C:400-484 (rocket_proc).
    """
    def __init__(self, sprites, position):
        Entity.__init__(self, sprites, position)
        self.state = "waiting"
        self.speed = 0
        self.initialized = False

    def update(self):
        if not self.initialized:
            # Get speed from sprite param
            sprite = self.sprites[0] if self.sprites else None
            self.speed = sprite.param if sprite and sprite.param > 0 else 4
            self.initialized = True

        if self.state == "waiting":
            self.check_trigger()
        else:
            self.fly()

    def check_trigger(self):
        """Fire when player is aligned above - EB_ENEM.C:422-441"""
        if not gl.player:
            return

        player_pos = gl.player.get_position()
        my_pos = self.get_position()
        bbox = self.get_bbox()

        # Player center X
        player_cx = player_pos.x + 24  # Approximate player center
        player_bottom = player_pos.y + 96  # Approximate player bottom (2 sprites tall)

        # Check horizontal alignment (XB-8 to XE+8)
        xb = my_pos.x + bbox.x - 8
        xe = my_pos.x + bbox.x + bbox.width + 8
        my_top = my_pos.y + bbox.y

        # Player must be ABOVE rocket (player bottom < rocket top)
        if xb < player_cx < xe and player_bottom < my_top:
            # 1/8 chance per frame to fire (EB_ENEM.C:436)
            if gl.random(8) == 0:
                self.state = "flying"
                logging.debug("RocketDown triggered at %s", my_pos)

    def fly(self):
        """Move downward until collision"""
        self.position.y += self.speed

        # Animate
        self.frame = (self.frame + 1) % len(self.sprites) if self.sprites else 0

        # Wall collision
        screen = gl.screen_manager.get_screen()
        if screen and self.check_collision(XY(0, self.speed), screen):
            from emhero import put_explosion
            put_explosion(self.position.x, self.position.y)
            self.vanish()
            return

        # Off-screen
        if self.position.y > gl.SCREEN_Y * gl.SPRITE_Y:
            self.vanish()


class KillingFloor(Entity):
    """
    One-time trigger that removes bottom row collisions.
    Based on EB_ENEM.C:486-492.
    When activated, player will die if they fall to the bottom of the screen.
    """
    def __init__(self, sprites, position):
        Entity.__init__(self, sprites, position)
        self.activated = False

    def update(self):
        if not self.activated:
            self.activated = True
            gl.killing_floor = True

            # Remove bottom row collisions (EB_ENEM.C:491)
            screen = gl.screen_manager.get_screen()
            if screen:
                bottom_y = (gl.SCREEN_Y - 1) * gl.SPRITE_Y
                # Filter out collision objects at the bottom row
                screen.collisions = [c for c in screen.collisions
                                     if c.get_y() < bottom_y]
            logging.debug("KillingFloor activated - bottom collisions removed")
            self.vanish()


class Monitor(Entity):
    def __init__(self, sprites, position):
        Entity.__init__(self, sprites, position)


class Display(Entity):
    def __init__(self, sprites, position):
        Entity.__init__(self, sprites, position)


class Checkpoint(Entity):
    def __init__(self, sprites, position):
        Entity.__init__(self, sprites, position)
        self.activated = False
        # Load activation cross sprite from info set
        self.cross_sprite = None
        if gl.info:
            self.cross_sprite = gl.info.get_sprite(5)  # small cross sprite

    def activate(self):
        """Visual indication checkpoint is now active"""
        self.activated = True
        # Change to last frame if multiple frames available
        if len(self.sprites) > 1:
            self.frame = len(self.sprites) - 1

    def display(self):
        """Display checkpoint with cross overlay if activated"""
        Entity.display(self)
        # Display cross sprite overlay when activated
        if self.activated and self.cross_sprite:
            pos = self.get_position()
            scaled_cross = pygame.transform.scale2x(self.cross_sprite.image)
            scaled_pos = XY(pos.x * 2, pos.y * 2)
            gl.display.blit(scaled_cross, scaled_pos)


class Teleport(Entity):
    def __init__(self, sprites, position):
        Entity.__init__(self, sprites, position)


class TeleportBase(Entity):
    def __init__(self, sprites, position):
        Entity.__init__(self, sprites, position)


class Exit(Entity):
    def __init__(self, sprites, position):
        Entity.__init__(self, sprites, position)
        # The indicator sprite (yellow triangle) will be set by emdata.__init_exit()
        # It loads the sprite at index (exit_index + 1) from the level sprite set
        self.indicator_sprite = None
        self.indicator_entity = None

    def update(self):
        """Create indicator entity when 3 disks collected"""
        if gl.disks >= 3 and self.indicator_sprite and not self.indicator_entity:
            # Create a touchable indicator entity above the exit
            pos = self.get_position()
            indicator_pos = XY(pos.x, pos.y - gl.SPRITE_Y)
            self.indicator_entity = ExitIndicator([self.indicator_sprite], indicator_pos)
            # Add to active entities so it can be touched
            gl.screen.active.append(self.indicator_entity)
            self.indicator_entity.set_origin(gl.screen)


class ExitIndicator(Entity):
    """The touchable indicator sprite that appears above the exit"""
    def __init__(self, sprites, position):
        Entity.__init__(self, sprites, position)

    def get_touch(self):
        """Exit indicators should return touch type 6 for exit handling"""
        return 6

    def display(self):
        """Display indicator only when blinking"""
        if gl.counter & 0x04:
            Entity.display(self)


class CannonBase(Entity):
    """
    Base class for cannons - matches cannon_proc (EB_ENEM.C:645-679)
    Fires projectiles at regular intervals with randomization.
    """
    def __init__(self, sprites, position, direction):
        Entity.__init__(self, sprites, position)
        self.direction = direction  # XY for projectile direction
        self.fire_timer = 0
        self.fire_interval = 0
        self.projectile_speed = 8  # Default, overridden by sprite param
        self.projectile_sprite = None  # Set by emdata.py - last sprite in animation
        self.initialized = False

    def update(self):
        if not self.initialized:
            # Get timing and speed from sprite param (EB_ENEM.C:690-691)
            # PARAMB is used for BOTH firing interval AND projectile speed
            sprite = self.sprites[0] if self.sprites else None
            param = sprite.param if sprite and sprite.param > 0 else 8
            self.fire_interval = param
            self.projectile_speed = param  # Speed = param (EB_ENEM.C:668-671)
            # Initial random delay: random(param) - EB_ENEM.C:690
            self.fire_timer = gl.random(param) if param > 0 else 0
            self.initialized = True
            logging.debug("Cannon init: interval=%d, speed=%d, initial_timer=%d",
                         self.fire_interval, self.projectile_speed, self.fire_timer)
            return

        if self.fire_timer > 0:
            self.fire_timer -= 1
        else:
            self.fire_projectile()
            # Reset: param + random(param) - EB_ENEM.C:653
            self.fire_timer = self.fire_interval + gl.random(self.fire_interval)

    def fire_projectile(self):
        """Fire a projectile in the cannon's direction"""
        # Get cannon and projectile bounding boxes for spawn position calculation
        cannon_pos = self.get_position()
        cannon_bbox = self.get_bbox()

        # Projectile uses projectile_sprite set during init (last sprite in cannon's animation)
        proj_sprites = []
        proj_bbox = pygame.Rect(0, 0, 24, 24)  # Default
        if self.projectile_sprite:
            proj_sprites = [self.projectile_sprite]
            proj_bbox = self.projectile_sprite.bbox
        else:
            logging.warning("Cannon has no projectile_sprite set!")

        # Calculate spawn position based on direction (EB_ENEM.C:688, 703, 718, 733)
        # Projectile spawns at cannon edge in firing direction
        pos = cannon_pos.copy()
        if self.direction.x < 0:  # Left: X = X + cannon_left - proj_right - 1
            pos.x = cannon_pos.x + cannon_bbox.x - (proj_bbox.x + proj_bbox.width) - 1
        elif self.direction.x > 0:  # Right: X = X + cannon_right - proj_left + 1
            pos.x = cannon_pos.x + cannon_bbox.x + cannon_bbox.width - proj_bbox.x + 1
        elif self.direction.y < 0:  # Up: Y = Y + cannon_top - proj_bottom - 1
            pos.y = cannon_pos.y + cannon_bbox.y - (proj_bbox.y + proj_bbox.height) - 1
        elif self.direction.y > 0:  # Down: Y = Y + cannon_bottom - proj_top + 1
            pos.y = cannon_pos.y + cannon_bbox.y + cannon_bbox.height - proj_bbox.y + 1

        # Velocity based on direction and speed (EB_ENEM.C:668-671)
        velocity = XY(self.direction.x * self.projectile_speed,
                     self.direction.y * self.projectile_speed)

        proj = EnemyProjectile(proj_sprites, pos, velocity)
        gl.screen_manager.add_active(proj)
        logging.debug("Cannon fired projectile at %s with velocity %s", pos, velocity)


class CannonLeft(CannonBase):
    def __init__(self, sprites, position):
        CannonBase.__init__(self, sprites, position, XY(-1, 0))


class CannonRight(CannonBase):
    def __init__(self, sprites, position):
        CannonBase.__init__(self, sprites, position, XY(1, 0))


class CannonUp(CannonBase):
    def __init__(self, sprites, position):
        CannonBase.__init__(self, sprites, position, XY(0, -1))


class CannonDown(CannonBase):
    def __init__(self, sprites, position):
        CannonBase.__init__(self, sprites, position, XY(0, 1))


class EnemyPlatform(Entity):
    """
    Platform enemy - patrols left/right on platforms.
    Based on EB_ENEM.C:867-944 (platform_creature_init/proc).
    """
    def __init__(self, sprites, position):
        Entity.__init__(self, sprites, position)
        self.shoots = False
        self.anims = None
        self.frames = 0
        self.frame = 0
        self.anim = "MLEFT"
        # AI state
        self.state = "init"
        self.x_step = -2  # Movement speed/direction
        self.shoot_timer = 0  # Shoot countdown timer
        self.left_boundary = 0   # Left patrol boundary
        self.right_boundary = 0  # Right patrol boundary
        self.anim_delay = 0     # Animation delay counter
        self.initialized = False

    def update(self):
        if not self.initialized:
            self.initialize_patrol()
            return

        if self.state == "patrol":
            self.update_patrol()
        elif self.state == "shoot":
            self.update_shoot()

    def initialize_patrol(self):
        """Find platform boundaries - EB_ENEM.C:867-944"""
        pos = self.get_position()
        screen = gl.screen_manager.get_screen()

        # Scan right for boundary (platform edge or wall)
        x = pos.x
        for _ in range(12):  # Max 12 tiles (576 pixels)
            # Check wall collision to right
            if self.would_collide_at(XY(x + gl.SPRITE_X // 2, pos.y), XY(1, 0), screen):
                break
            # Check if ground continues
            if not self.has_ground_at(x + gl.SPRITE_X // 2, pos.y, screen):
                break
            x += gl.SPRITE_X // 2
        self.right_boundary = x

        # Scan left for boundary
        x = pos.x
        for _ in range(12):
            if self.would_collide_at(XY(x - gl.SPRITE_X // 2, pos.y), XY(-1, 0), screen):
                break
            if not self.has_ground_at(x - gl.SPRITE_X // 2, pos.y, screen):
                break
            x -= gl.SPRITE_X // 2
        self.left_boundary = x

        # Face player (EB_ENEM.C:903-912)
        if gl.player and gl.player.get_x() > pos.x:
            self.x_step = abs(self.x_step)
            self.anim = "MRIGHT"
        else:
            self.x_step = -abs(self.x_step)
            self.anim = "MLEFT"

        # Init shoot timer if enemy shoots (EB_ENEM.C:917-920)
        if self.shoots:
            self.shoot_timer = 32 + gl.random(64)

        self.anim_delay = gl.random(16)
        self.initialized = True
        self.state = "patrol"
        logging.debug("EnemyPlatform initialized: pos=%s, bounds=[%d, %d]",
                     pos, self.left_boundary, self.right_boundary)

    def would_collide_at(self, pos, direction, screen):
        """Check if there's a wall collision at position in direction"""
        if not screen:
            return False
        me = self.get_bbox().copy()
        me.move_ip(pos)
        for obj in screen.collisions:
            you = obj.get_bbox().copy()
            you.move_ip(obj.get_position())
            if me.colliderect(you):
                sides = obj.get_sides()
                if direction.x > 0 and sides["L"]:
                    return True
                elif direction.x < 0 and sides["R"]:
                    return True
        return False

    def has_ground_at(self, x, y, screen):
        """Check if there's ground below a position"""
        if not screen:
            return False
        # Check for collision block below
        check_y = y + gl.SPRITE_Y
        for obj in screen.collisions:
            obj_pos = obj.get_position()
            obj_bbox = obj.get_bbox()
            obj_top = obj_pos.y + obj_bbox.y
            obj_left = obj_pos.x + obj_bbox.x
            obj_right = obj_pos.x + obj_bbox.x + obj_bbox.w
            if (obj.get_sides()["T"] and
                obj_top >= check_y and obj_top < check_y + gl.SPRITE_Y and
                obj_left <= x < obj_right):
                return True
        return False

    def update_patrol(self):
        """Patrol movement - EB_ENEM.C:814-865"""
        if self.anim_delay > 0:
            self.anim_delay -= 1
            return

        # Shooting countdown
        if self.shoots and self.shoot_timer > 0:
            self.shoot_timer -= 1
            if self.shoot_timer == 0 and self.frame == 0:
                self.anim_delay = 16
                self.shoot_timer = 32 + gl.random(64)
                self.state = "shoot"
                return

        # Move
        self.position.x += self.x_step

        # Animate
        anim_sprites = self.anims.get(self.anim, []) if self.anims else []
        max_frames = len(anim_sprites) if anim_sprites else 1
        self.frame = (self.frame + 1) % max_frames

        # Boundary check - reverse direction at edges
        if self.x_step < 0 and self.position.x <= self.left_boundary:
            self.x_step = -self.x_step
            self.anim = "MRIGHT"
            self.frame = 0
        elif self.x_step > 0 and self.position.x >= self.right_boundary:
            self.x_step = -self.x_step
            self.anim = "MLEFT"
            self.frame = 0

    def update_shoot(self):
        """Fire projectile - EB_ENEM.C:770-812"""
        if self.anim_delay > 0:
            self.anim_delay -= 1
            return

        # Fire horizontal projectile toward facing direction
        pos = self.get_position()
        if self.x_step < 0:
            velocity = XY(-4, 0)
        else:
            velocity = XY(4, 0)

        # Get projectile sprite if available
        proj_sprites = []
        if gl.enemies and hasattr(gl.enemies, 'get_projectile_sprites'):
            proj_sprites = gl.enemies.get_projectile_sprites()

        proj = EnemyProjectile(proj_sprites, pos.copy(), velocity)
        gl.screen_manager.add_active(proj)
        logging.debug("EnemyPlatform fired projectile at %s", pos)

        self.state = "patrol"

    def _get_current_sprite(self):
        """Helper to get current animation sprite safely"""
        if self.anims and self.anim in self.anims:
            anim_sprites = self.anims[self.anim]
            if anim_sprites:
                frame = self.frame % len(anim_sprites)
                return anim_sprites[frame]
        return None

    def get_bbox(self):
        """Override to use anims instead of sprites for bounding box"""
        sprite = self._get_current_sprite()
        if sprite:
            return sprite.bbox
        return pygame.Rect(0, 0, gl.SPRITE_X, gl.SPRITE_Y)

    def get_sides(self):
        """Override to use anims instead of sprites"""
        sprite = self._get_current_sprite()
        if sprite:
            return sprite.collide
        return {"L": False, "R": False, "T": False, "B": False}

    def is_touchable(self):
        """Enemies are not touchable (they kill on collision instead)"""
        return False

    def get_touch(self):
        """Enemies don't have touch type"""
        return 0

    def take_damage(self, damage):
        """Enemy hit by projectile - instant kill (EB_ENEM.C:70-89)"""
        self.die()

    def die(self):
        """Enemy destruction - matches xplode() from EB_ENEM.C:70-89"""
        bbox = self.get_bbox()
        pos = self.get_position()
        center_x = pos.x + bbox.x + bbox.w // 2 - 12
        center_y = pos.y + bbox.y + bbox.h // 2 - 12
        from emhero import put_explosion
        logging.debug("Enemy destroyed at pos %s, explosion at (%d,%d)",
                     pos, center_x, center_y)
        put_explosion(center_x, center_y)
        self.vanish()

    def display(self):
        # Scale enemy sprite 2x
        if self.anims and self.anim in self.anims:
            anim_sprites = self.anims[self.anim]
            if anim_sprites and self.frame < len(anim_sprites):
                scaled_image = pygame.transform.scale2x(anim_sprites[self.frame].image)
                scaled_pos = XY(self.get_position().x * 2, self.get_position().y * 2)
                gl.display.blit(scaled_image, scaled_pos)

class EnemyFlying(Entity):
    """
    Flying enemy - patrols left/right in the air (doesn't need platforms).
    Based on EB_ENEM.C:867-944 with flying creature modifications.
    Fires DOWNWARD projectiles (unlike platform enemies).
    """
    def __init__(self, sprites, position):
        Entity.__init__(self, sprites, position)
        self.shoots = False
        self.anims = None
        self.frames = 0
        self.frame = 0
        self.anim = "MLEFT"
        # AI state
        self.state = "init"
        self.x_step = -2  # Movement speed/direction
        self.shoot_timer = 0  # Shoot countdown timer
        self.left_boundary = 0   # Left patrol boundary
        self.right_boundary = 0  # Right patrol boundary
        self.anim_delay = 0     # Animation delay counter
        self.initialized = False

    def update(self):
        if not self.initialized:
            self.initialize_patrol()
            return

        if self.state == "patrol":
            self.update_patrol()
        elif self.state == "shoot":
            self.update_shoot()

    def initialize_patrol(self):
        """Find patrol boundaries - EB_ENEM.C:867-944 (no ground check for flying)"""
        pos = self.get_position()
        screen = gl.screen_manager.get_screen()

        # Scan right for boundary (wall only - no ground check for flying enemies)
        x = pos.x
        for _ in range(12):  # Max 12 tiles
            if self.would_collide_at(XY(x + gl.SPRITE_X // 2, pos.y), XY(1, 0), screen):
                break
            x += gl.SPRITE_X // 2
        self.right_boundary = x

        # Scan left for boundary
        x = pos.x
        for _ in range(12):
            if self.would_collide_at(XY(x - gl.SPRITE_X // 2, pos.y), XY(-1, 0), screen):
                break
            x -= gl.SPRITE_X // 2
        self.left_boundary = x

        # Face player
        if gl.player and gl.player.get_x() > pos.x:
            self.x_step = abs(self.x_step)
            self.anim = "MRIGHT"
        else:
            self.x_step = -abs(self.x_step)
            self.anim = "MLEFT"

        # Init shoot timer if enemy shoots
        if self.shoots:
            self.shoot_timer = 32 + gl.random(64)

        self.anim_delay = gl.random(16)
        self.initialized = True
        self.state = "patrol"
        logging.debug("EnemyFlying initialized: pos=%s, bounds=[%d, %d]",
                     pos, self.left_boundary, self.right_boundary)

    def would_collide_at(self, pos, direction, screen):
        """Check if there's a wall collision at position in direction"""
        if not screen:
            return False
        me = self.get_bbox().copy()
        me.move_ip(pos)
        for obj in screen.collisions:
            you = obj.get_bbox().copy()
            you.move_ip(obj.get_position())
            if me.colliderect(you):
                sides = obj.get_sides()
                if direction.x > 0 and sides["L"]:
                    return True
                elif direction.x < 0 and sides["R"]:
                    return True
        return False

    def update_patrol(self):
        """Patrol movement"""
        if self.anim_delay > 0:
            self.anim_delay -= 1
            return

        # Shooting countdown
        if self.shoots and self.shoot_timer > 0:
            self.shoot_timer -= 1
            if self.shoot_timer == 0 and self.frame == 0:
                self.anim_delay = 16
                self.shoot_timer = 32 + gl.random(64)
                self.state = "shoot"
                return

        # Move
        self.position.x += self.x_step

        # Animate
        anim_sprites = self.anims.get(self.anim, []) if self.anims else []
        max_frames = len(anim_sprites) if anim_sprites else 1
        self.frame = (self.frame + 1) % max_frames

        # Boundary check - reverse direction at edges
        if self.x_step < 0 and self.position.x <= self.left_boundary:
            self.x_step = -self.x_step
            self.anim = "MRIGHT"
            self.frame = 0
        elif self.x_step > 0 and self.position.x >= self.right_boundary:
            self.x_step = -self.x_step
            self.anim = "MLEFT"
            self.frame = 0

    def update_shoot(self):
        """Fire projectile DOWNWARD (unlike platform enemy)"""
        if self.anim_delay > 0:
            self.anim_delay -= 1
            return

        # Fire DOWNWARD projectile (flying enemies shoot down)
        pos = self.get_position()
        velocity = XY(0, 4)  # Always fires down

        # Get projectile sprite if available
        proj_sprites = []
        if gl.enemies and hasattr(gl.enemies, 'get_projectile_sprites'):
            proj_sprites = gl.enemies.get_projectile_sprites()

        proj = EnemyProjectile(proj_sprites, pos.copy(), velocity)
        gl.screen_manager.add_active(proj)
        logging.debug("EnemyFlying fired projectile at %s (downward)", pos)

        self.state = "patrol"

    def _get_current_sprite(self):
        """Helper to get current animation sprite safely"""
        if self.anims and self.anim in self.anims:
            anim_sprites = self.anims[self.anim]
            if anim_sprites:
                frame = self.frame % len(anim_sprites)
                return anim_sprites[frame]
        return None

    def get_bbox(self):
        """Override to use anims instead of sprites for bounding box"""
        sprite = self._get_current_sprite()
        if sprite:
            return sprite.bbox
        return pygame.Rect(0, 0, gl.SPRITE_X, gl.SPRITE_Y)

    def get_sides(self):
        """Override to use anims instead of sprites"""
        sprite = self._get_current_sprite()
        if sprite:
            return sprite.collide
        return {"L": False, "R": False, "T": False, "B": False}

    def is_touchable(self):
        """Enemies are not touchable (they kill on collision instead)"""
        return False

    def get_touch(self):
        """Enemies don't have touch type"""
        return 0

    def take_damage(self, damage):
        """Enemy hit by projectile - instant kill (EB_ENEM.C:70-89)"""
        self.die()

    def die(self):
        """Enemy destruction - matches xplode() from EB_ENEM.C:70-89"""
        bbox = self.get_bbox()
        pos = self.get_position()
        center_x = pos.x + bbox.x + bbox.w // 2 - 12
        center_y = pos.y + bbox.y + bbox.h // 2 - 12
        from emhero import put_explosion
        logging.debug("EnemyFlying destroyed at pos %s, explosion at (%d,%d)",
                     pos, center_x, center_y)
        put_explosion(center_x, center_y)
        self.vanish()

    def display(self):
        # Scale enemy sprite 2x
        if self.anims and self.anim in self.anims:
            anim_sprites = self.anims[self.anim]
            if anim_sprites and self.frame < len(anim_sprites):
                scaled_image = pygame.transform.scale2x(anim_sprites[self.frame].image)
                scaled_pos = XY(self.get_position().x * 2, self.get_position().y * 2)
                gl.display.blit(scaled_image, scaled_pos)


class EnemyProjectile(Entity):
    """
    Projectile fired by enemies (cannons, platform/flying enemies).
    Matches cannon_miss from EB_ENEM.C:581-642
    """
    def __init__(self, sprites, position, velocity):
        Entity.__init__(self, sprites, position)
        self.velocity = velocity  # XY(x_speed, y_speed)
        self.frame = 0

    def update(self):
        # Move projectile
        self.position.x += self.velocity.x
        self.position.y += self.velocity.y

        # Animate
        if self.sprites:
            self.frame = (self.frame + 1) % len(self.sprites)

        # Off-screen check
        if (self.position.x < -gl.SPRITE_X or
            self.position.x > gl.SCREEN_X * gl.SPRITE_X or
            self.position.y < -gl.SPRITE_Y or
            self.position.y > gl.SCREEN_Y * gl.SPRITE_Y):
            self.vanish()
            return

        # Wall collision check - only stop on SOLID walls (EB_ENEM.C:581-642)
        # Original uses cave_test which checks tile solidity, not object overlap
        # Only collide with objects that have ALL collision sides (solid blocks)
        screen = gl.screen_manager.get_screen()
        if screen and self.check_solid_wall_collision(screen):
            self.vanish()

    def check_solid_wall_collision(self, screen):
        """
        Check collision with solid walls only (not decorative sprites).
        Matches original cave_test behavior - only solid blocks stop projectiles.
        """
        if not screen:
            return False

        me = self.get_bbox().copy()
        me.move_ip(self.get_position())

        for obj in screen.collisions:
            you = obj.get_bbox().copy()
            you.move_ip(obj.get_position())
            if me.colliderect(you):
                sides = obj.get_sides()
                # Only stop on objects that block from the direction we're moving
                # AND are actual solid walls (have multiple collision sides)
                num_sides = sum([sides["L"], sides["R"], sides["T"], sides["B"]])
                if num_sides >= 2:  # Solid walls typically have 2+ collision sides
                    if self.velocity.x > 0 and sides["L"]:
                        return True
                    elif self.velocity.x < 0 and sides["R"]:
                        return True
                    elif self.velocity.y > 0 and sides["T"]:
                        return True
                    elif self.velocity.y < 0 and sides["B"]:
                        return True
        return False

    def get_bbox(self):
        """Return projectile's actual bounding box from sprite data"""
        if self.sprites and len(self.sprites) > 0:
            sprite = self.sprites[self.frame % len(self.sprites)]
            if sprite and hasattr(sprite, 'bbox'):
                return sprite.bbox
        # Fallback if no sprite
        return pygame.Rect(0, 0, gl.SPRITE_X, gl.SPRITE_Y)

    def get_sides(self):
        """Projectiles don't block movement"""
        return {"L": False, "R": False, "T": False, "B": False}

    def is_touchable(self):
        """Projectiles are not touchable (they kill via collision check)"""
        return False

    def get_touch(self):
        """Projectiles don't have touch type"""
        return 0

    def display(self):
        """Display projectile sprite at 2x scale"""
        pos = self.get_position()
        scaled_pos = (pos.x * 2, pos.y * 2)

        if self.sprites and len(self.sprites) > 0:
            sprite = self.sprites[self.frame % len(self.sprites)]
            if sprite and hasattr(sprite, 'image') and sprite.image:
                scaled_image = pygame.transform.scale2x(sprite.image)
                gl.display.blit(scaled_image, scaled_pos)
                return

        # Draw placeholder circle when no valid sprites available
        # Red filled circle to make projectiles visible
        rect = pygame.Rect(scaled_pos[0] + 16, scaled_pos[1] + 16, 32, 32)
        pygame.draw.circle(gl.display, pygame.Color(255, 0, 0), rect.center, 12)
        pygame.draw.circle(gl.display, pygame.Color(255, 255, 0), rect.center, 8)

    def name(self):
        return "EnemyProjectile"


class Explosion(Entity):
    """
    Explosion animation entity.
    Plays explosion animation once then removes itself.
    Matches original explosion_proc from EB_ENEM.C:51-56
    """
    def __init__(self, sprites, position):
        Entity.__init__(self, sprites, position)
        self.frame = 0

    def update(self):
        """Cycle through explosion animation frames"""
        self.frame += 1
        if self.frame >= len(self.sprites):
            # Animation complete - remove explosion
            gl.screen.active.remove(self)

    def name(self):
        return "Explosion"


class BrokenSprite(Entity):
    """
    Static broken sprite entity.
    Shows the broken state of a destroyed object.
    """
    def __init__(self, sprites, position, frame_num):
        Entity.__init__(self, sprites, position)
        self.frame = frame_num if frame_num < len(sprites) else 0

    def update(self):
        """Static sprite - no update needed"""
        pass

    def display(self):
        """Display the broken sprite at 2x scale"""
        if self.frame < len(self.sprites):
            scaled_image = pygame.transform.scale2x(self.sprites[self.frame].image)
            scaled_pos = XY(self.get_position().x * 2, self.get_position().y * 2)
            gl.display.blit(scaled_image, scaled_pos)

    def name(self):
        return "BrokenSprite"


class ExplosionWithBroke(Entity):
    """
    Explosion animation that leaves a broken sprite behind.
    Matches original explosion_with_broke_proc from EB_ENEM.I:3461-3483
    """
    def __init__(self, explosion_sprites, position, broken_entity):
        Entity.__init__(self, explosion_sprites, position)
        self.frame = 0
        self.broken_entity = broken_entity
        self.broken_sprite_spawned = False

    def update(self):
        """Cycle through explosion animation"""
        # Note: In the original C code, AUX_1++ at frame 2 advances to the next
        # shape_num (broken sprite). We now handle this in hit_object() by
        # getting the broken sprite directly from level data at sprite_index + len(sprites).
        self.frame += 1

        # When explosion completes, spawn the broken sprite entity (EB_ENEM.I:3472-3481)
        if self.frame >= len(self.sprites):
            if not self.broken_sprite_spawned and self.broken_entity:
                # Add broken sprite to current screen
                if gl.screen:
                    gl.screen.active.append(self.broken_entity)
                    logging.debug("ExplosionWithBroke: Added BrokenSprite to current screen at %s",
                                 self.broken_entity.position)
                # ALSO add to level data so it persists across screen changes
                screen_num = gl.screen_manager.get_screen_number()
                gl.screen_manager.add_to_level_data(screen_num, self.broken_entity)
                self.broken_sprite_spawned = True
            # Remove explosion from current screen (not from level data - it was never there)
            try:
                gl.screen.active.remove(self)
            except ValueError:
                logging.debug("ExplosionWithBroke: Already removed from screen")

    def name(self):
        return "ExplosionWithBroke"


# -----------------------------------------------------------------------------
# test code below

def main():
    pass

if __name__ == "__main__":
    main()
