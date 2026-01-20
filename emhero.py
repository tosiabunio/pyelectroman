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


def put_explosion(x, y):
    """
    Spawn an explosion at the given position.
    Matches original put_explosion from EB_ENEM.C:59-67
    """
    # Get explosion sprites from weapons set (sprites 0-7)
    explosion_sprites = gl.weapons.weapon["EXPLOSION"].anims

    # Create explosion entity at position
    explosion = ga.Explosion(explosion_sprites, XY(x, y))

    # Add to current screen's active entities
    if gl.screen:
        gl.screen.active.append(explosion)

    logging.debug("Explosion spawned at (%d, %d)", x, y)


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
        # Don't display player during death animation
        if self.state == self.state_death:
            return

        try:
            position = self.get_position()
            # display top sprite (scaled 2x)
            sprite = self.sprites[self.anim][self.frame][0]
            sprite = self.data.get_sprite(sprite)
            scaled_image = pygame.transform.scale2x(sprite.image)
            scaled_pos = XY(position.x * 2, position.y * 2)
            gl.display.blit(scaled_image, scaled_pos)
            # display bottom sprite (scaled 2x)
            position += (0, gl.SPRITE_Y)
            sprite = self.sprites[self.anim][self.frame][1]
            sprite = self.data.get_sprite(sprite)
            scaled_image = pygame.transform.scale2x(sprite.image)
            scaled_pos = XY(position.x * 2, position.y * 2)
            gl.display.blit(scaled_image, scaled_pos)
            if gl.show_collisions:
                # show collision box and ground testing point
                self.display_collisions()
        except (KeyError, IndexError) as e:
            logging.error("Display error: anim=%s, frame=%d, state=%s, error=%s",
                         self.anim, self.frame, self.state.__name__, e)

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
                # Check if this is a level exit (EB_HERO.C:853)
                # If exit_level_flag is set, don't transition to teleport_in
                # The main loop will handle the level transition
                if gl.exit_level_flag:
                    # Stay in this state, level transition will happen in main loop
                    pass
                else:
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

    def state_death(self, init=False):
        """
        Handle player death sequence.
        Matches original hero_before_kill_proc -> hero_kill_proc -> hero_after_kill_proc
        """
        if init:
            # Initial death state (hero_before_kill_proc)
            self.death_timer = 0
            pos = self.get_position()

            # Spawn initial explosions (EB_HERO.C:932-933)
            put_explosion(int(pos.x - 2), int(pos.y))
            put_explosion(int(pos.x + 1), int(pos.y + 23))

            logging.info("Player death - position: %s", pos)
            di.info_lines.add("Player died!")

        self.death_timer += 1

        if self.death_timer < 10:
            # Death animation phase (hero_kill_proc)
            # Spawn random explosions around player for 10 frames (EB_HERO.C:920)
            pos = self.get_position()

            # Random offset: X - 12 + random(24), Y + random(24)
            offset_x = -12 + gl.random(24)
            offset_y = gl.random(24)
            put_explosion(int(pos.x + offset_x), int(pos.y + offset_y))

            # TODO: PLAY_SAMPLE(blast_s) - sound effect
        elif self.death_timer < 70:
            # After-death countdown phase (hero_after_kill_proc)
            # Wait for ~3 seconds (60 frames at 20fps)
            pass
        else:
            # Timer expired - trigger respawn
            self.respawn()

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
        Matches original: gun_power = (++gun_power > 5) ? 5 : gun_power
        """
        if self.power < 5:
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
        # update disk display
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
                    # battery - only collect if not at max power
                    if self.power < 5:
                        self.inc_power()
                        obj.vanish()  # remove battery from the map
                elif touch_type == 2:
                    if self.controller.down:
                        self.find_teleport_target(obj.get_position())
                        self.new_state(self.state_teleport_out)
                    # teleport
                    pass
                elif touch_type == 3:
                    # checkpoint - activate if different from current
                    current_screen = gl.screen_manager.get_screen_number()
                    current_pos = obj.get_position()

                    # Only activate if different checkpoint (EB_HERO.C:514)
                    if (gl.checkpoint.get_screen() != current_screen or
                        gl.checkpoint.get_position() != current_pos):
                        # Update checkpoint
                        gl.checkpoint.update(gl.current_level, current_screen, current_pos)

                        # Reset weapon stats to 0 (EB_HERO.C:519)
                        self.power = 0
                        self.temp = 0
                        self.temperature = 0
                        self.select_weapon(0)

                        # Visual feedback
                        if hasattr(obj, 'activate'):
                            obj.activate()
                        di.info_lines.add("Checkpoint activated")
                        # TODO: PLAY_SAMPLE(checkp_s) - sound effect
                elif touch_type == 4:
                    # killer - trigger death (only if not already dying)
                    if self.state != self.state_death:
                        self.new_state(self.state_death)
                elif touch_type == 5:
                    # floppy - collect disk
                    gl.disks += 1
                    obj.vanish()  # remove floppy from the map
                    di.info_lines.add("Disk collected (%d/3)" % gl.disks)
                    # TODO: PLAY_SAMPLE(disk_s) - sound effect
                elif touch_type == 6:
                    # exit - check disk requirement (EB_HERO.C:548-560)
                    if gl.disks >= 3:
                        # Get next level code from sprite param
                        # NOTE: The param seems to be encoded, for now just advance to next level
                        next_level = gl.current_level + 1
                        di.info_lines.add("Level complete!")
                        # Set exit flag for level transition
                        gl.exit_level_flag = True
                        gl.next_level_code = next_level
                        # Trigger teleport out animation (EB_HERO.C:555-558)
                        # teleport_flag++, teleport_x=0, teleport_y=0
                        self.new_state(self.state_teleport_out)
                        # TODO: PLAY_SAMPLE(exit_s) - sound effect
                    else:
                        di.info_lines.add("Need %d more disk(s)" % (3 - gl.disks))
                elif touch_type == 7:
                    # special good
                    pass
                elif touch_type == 8:
                    # special bad
                    pass
            di.message(XY(16, 40), "touch: %s" % names)

    def respawn(self):
        """
        Respawn player at checkpoint after death.
        Matches original init_level() - unlimited retries.
        """
        # Get checkpoint position and screen
        checkpoint_screen = gl.checkpoint.get_screen()
        checkpoint_pos = gl.checkpoint.get_position()

        # If no checkpoint is set (shouldn't happen but safety check)
        if checkpoint_pos is None:
            logging.warning("No checkpoint set, using default spawn")
            checkpoint_screen = 0
            checkpoint_pos = XY(0, 0)

        # Change to checkpoint screen
        if checkpoint_screen != gl.screen_manager.get_screen_number():
            gl.screen_manager.change_screen(checkpoint_screen)
            # Update global screen reference immediately
            gl.screen = gl.screen_manager.get_screen()

        # Position player at checkpoint using stand() method (same as level load)
        respawn_pos = checkpoint_pos + XY(gl.SPRITE_X // 2, gl.SPRITE_Y)
        self.stand(respawn_pos)

        # Reset player stats
        self.temperature = 0
        self.death_timer = 0
        self.touched = []  # Clear touched objects to prevent immediate re-death

        # Recalculate to_ground before state switch
        self.to_ground = self.check_ground(gl.screen)

        # Return to standing state
        self.switch_state(self.state_stand)

        logging.info("Respawned at checkpoint: screen=%d, pos=%s",
                     checkpoint_screen, self.get_position())
        di.info_lines.add("Respawned at checkpoint")

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
        # check for touching objects at current position (but not during death)
        if self.state != self.state_death:
            self.check_touch()
        # keep track of to ground distance
        self.to_ground = self.check_ground(self.screen)
        di.message(XY(16, 8), "to ground: %d" % self.to_ground)
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

    projectiles = {
        "1_L" : { "offset" : XY(-38, 32), "step" : -28 },
        "1_R" : { "offset" : XY(38, 32), "step" : 28 },
        "2_L" : { "offset" : XY(-46, 32), "step" : -32 },
        "2_R" : { "offset" : XY(46, 32), "step" : 32 },
        "3_L" : { "offset" : XY(-46, 32), "step" : -28 },
        "3_R" : { "offset" : XY(46, 32), "step" : 28 },
        "4_L" : { "offset" : XY(-46, 32), "step" : -24 },
        "4_R" : { "offset" : XY(46, 32), "step" : 24 },
        "5_L" : { "offset" : XY(-36, 8), "step" : -32 },
        "5_R" : { "offset" : XY(36, 8), "step" : 32 },
    }

    def fire_weapon(self):
        """
        Fire the weapon!
        """
        def add_projectile(type, pos=None):
            if not pos:
                ppos = self.get_position().copy() + self.projectiles[type]["offset"]
            else:
                ppos = pos
            projectile = Projectile(type)
            projectile.set_position(ppos)
            projectile.step = self.projectiles[type]["step"]
            gl.screen_manager.add_active(projectile)
            return projectile

        if self.power:
            t = self.heat[self.power]
            if self.temp + t <= 5:  # Max temperature is 5 (EB_HERO.C:324)
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
    """
    Projectile entity for weapon shots.

    Behavior varies by weapon level (from EB_HERO.C:337-479):
    - Level 1: short_miss_proc - limited range (removes after animation cycle)
    - Level 2-3: long_miss_proc - infinite range, no penetration
    - Level 4: long_miss_proc with AUX_2=1 - infinite range, PENETRATES enemies
    - Level 5: bow_proc - double-height sprite, triple explosion on wall hit
    """

    def __init__(self, type):
        ga.Entity.__init__(self, [da.EmptySprite()], XY(0, 0))
        self.type = type
        self.sprites = gl.weapons.weapon[type].anims
        self.frames = gl.weapons.weapon[type].frames
        self.step = 0
        self.power_level = int(type[0])
        self.animation_cycles = 0  # Track animation cycles for Level 1 range limit
        self.hit_count = 0  # Track number of enemies hit this frame

    def update(self):
        # Store previous frame for animation cycle detection
        prev_frame = self.frame

        # Animate projectile
        self.frame = (self.frame + 1) % len(self.sprites)

        # Detect animation cycle completion (frame wrapped to 0)
        if self.frame < prev_frame:
            self.animation_cycles += 1
            # Level 1: Limited range - remove after animation cycle (EB_HERO.C:245)
            if self.power_level == 1:
                logging.debug("Level 1 projectile removed after animation cycle")
                self.vanish()
                return

        # Move projectile
        self.position.x += self.step

        # Check screen boundaries
        if self.position.x > gl.SCREEN_X * gl.SPRITE_X or self.position.x < -gl.SPRITE_X:
            logging.debug("Projectile exited screen at x=%d", self.position.x)
            # Level 5: Triple explosion on wall/screen exit (EB_HERO.C:214-216)
            if self.power_level == 5:
                self.bow_end_explosion()
            self.vanish()
            return

        # Check collision with all enemies and shootable objects (EB_HERO.C:167-193)
        # Original code checks ALL enemies in a loop, not just the first hit
        self.hit_count = 0
        should_remove = self.check_all_collisions()

        if should_remove:
            self.vanish()

    def check_all_collisions(self):
        """
        Check collision with all entities.
        Returns True if projectile should be removed.

        Based on miss_enem_test() from EB_HERO.C:167-193 which loops through
        ALL enemies and can hit multiple in one frame.
        """
        screen = gl.screen_manager.get_screen()
        if not screen:
            return False

        # Create a copy of the list to avoid issues if entities are removed during iteration
        entities_to_check = list(screen.active)
        hit_enemy_this_frame = False
        hit_object = False

        for entity in entities_to_check:
            # Skip the projectile itself
            if entity == self:
                continue

            # Check if entity is an enemy
            if isinstance(entity, (ga.EnemyPlatform, ga.EnemyFlying)):
                if self.collides_with(entity):
                    logging.debug("Projectile hit enemy: %s at %s", type(entity).__name__, entity.get_position())
                    self.hit_enemy(entity)
                    hit_enemy_this_frame = True
                    # Continue checking other enemies (multi-hit support)

            # Check if entity is shootable (destructible objects)
            # Original C code (EB_HERO.C:178-180) checks the CURRENT animation frame's
            # SHOT_MASK, not frame 0. The sprite index is calculated as:
            # st = STAT_BUFF + 8 * (FIRST_SHAPE + SHAPE_CNTR)
            # Batteries are NOT shootable (only touchable), so they won't be hit
            elif hasattr(entity, 'sprites') and entity.sprites:
                # Use current animation frame, not frame 0 (EB_HERO.C:178)
                current_frame = getattr(entity, 'frame', 0)
                current_frame = min(current_frame, len(entity.sprites) - 1)
                sprite = entity.sprites[current_frame]
                is_shootable = sprite.flag('shootable')

                if is_shootable:
                    if self.collides_with(entity):
                        entity_name = entity.name() if hasattr(entity, 'name') else type(entity).__name__
                        logging.debug("Projectile hit shootable object: %s at %s (flags=0x%02X)",
                                    entity_name, entity.get_position(), sprite.flags)
                        self.hit_object(entity)
                        hit_object = True
                        # Objects always stop projectile
                        break

        # Determine if projectile should be removed
        if hit_object:
            return True  # Objects always stop projectile

        if hit_enemy_this_frame:
            # Level 4 penetrates enemies (AUX_2=1 in original code)
            # EB_HERO.C:258: if (!AUX_2) REMOVE_OBJ;
            if self.power_level == 4:
                logging.debug("Level 4 projectile penetrating (not removed)")
                return False  # Continue through enemies
            else:
                return True  # Remove on hit

        return False  # No hit, continue

    def collides_with(self, entity):
        """Check if projectile collides with an entity using AABB."""
        # Get relative bounding boxes and convert to absolute world coordinates
        proj_rel_bbox = self.get_bbox()
        entity_rel_bbox = entity.get_bbox()

        # Create absolute bounding boxes by adding entity positions
        proj_x = self.position.x + proj_rel_bbox.x
        proj_y = self.position.y + proj_rel_bbox.y
        proj_w = proj_rel_bbox.w
        proj_h = proj_rel_bbox.h

        # Level 5: Extended vertical collision box (EB_HERO.C:286, 464-465)
        if self.power_level == 5:
            # Original: os[UPB] = 6; os[DWB] = 24 + 18; (covers both sprites)
            proj_h = gl.SPRITE_Y * 2 - 12  # Extended to cover both sprites (scaled)

        entity_x = entity.position.x + entity_rel_bbox.x
        entity_y = entity.position.y + entity_rel_bbox.y
        entity_w = entity_rel_bbox.w
        entity_h = entity_rel_bbox.h

        # AABB collision detection
        collision = (proj_x < entity_x + entity_w and
                    proj_x + proj_w > entity_x and
                    proj_y < entity_y + entity_h and
                    proj_y + proj_h > entity_y)

        return collision

    def hit_enemy(self, enemy):
        """Projectile hit an enemy."""
        logging.debug("Projectile dealing %d damage to enemy", self.power_level)

        # Enemy takes damage
        enemy.take_damage(self.power_level)

        # Spawn explosion at hit location
        pos = self.get_position()
        put_explosion(pos.x, pos.y)

        self.hit_count += 1

    def hit_object(self, obj):
        """Projectile hit a shootable object (EB_HERO.C:528-534)."""
        # Check if object has "breakable" flag (BROKE_MASK in C code)
        # Must use current animation frame, same as shootable check (EB_HERO.C:178)
        current_frame = getattr(obj, 'frame', 0)
        current_frame = min(current_frame, len(obj.sprites) - 1)
        is_breakable = obj.sprites[current_frame].flag('destroyable')

        logging.debug("hit_object: %s at %s, frame=%d, destroyable=%s, sprite_index=%s",
                     obj.name(), obj.get_position(), current_frame, is_breakable,
                     getattr(obj, 'sprite_index', None))

        if is_breakable:
            logging.debug("  Creating explosion with broken sprite")
            # Explosion position is at object position (C code: NEW_X = ob->x, NEW_Y = ob->y)
            obj_pos = obj.get_position()
            exp_x = obj_pos.x
            exp_y = obj_pos.y

            # Get explosion sprites
            explosion_sprites = gl.weapons.weapon["EXPLOSION"].anims

            # Calculate grid position for broken sprite (EB_ENEM.I:3511-3512)
            grid_x = obj_pos.x // gl.SPRITE_X
            grid_y = obj_pos.y // gl.SPRITE_Y
            broken_pos = XY(grid_x * gl.SPRITE_X, grid_y * gl.SPRITE_Y)

            # Get broken sprite from level data (C code: AUX_1++ increments shape_num)
            # The broken sprite is the NEXT sprite in the level's sprite set
            broken_sprite = None
            broken_sidx = None
            if hasattr(obj, 'sprite_index') and obj.sprite_index is not None:
                # Calculate broken sprite index: original + animation length
                broken_sidx = obj.sprite_index + len(obj.sprites)
                try:
                    broken_sprite = gl.level.get_sprite(broken_sidx)
                    logging.debug("  Broken sprite from level: sidx=%d -> %d",
                                 obj.sprite_index, broken_sidx)
                except (IndexError, AssertionError):
                    logging.debug("  Broken sprite index %d out of range", broken_sidx)
                    broken_sprite = None

            if broken_sprite:
                # Use the broken sprite from level data
                broken_entity = ga.BrokenSprite([broken_sprite], broken_pos, 0)
                logging.debug("  BrokenSprite using level sprite at index %d", broken_sidx)
            else:
                # Fallback: use next frame of current animation (may be same sprite)
                current_frame = obj.frame if hasattr(obj, 'frame') else 0
                broken_entity = ga.BrokenSprite(obj.sprites, broken_pos, current_frame + 1)
                logging.debug("  BrokenSprite fallback: frame %d, num_sprites=%d",
                             current_frame + 1, len(obj.sprites))

            # In C code, the broken sprite is displayed IMMEDIATELY during explosion
            # (PUT_SPRITE in explosion_with_broke_proc), not after explosion finishes.
            # Add broken sprite to screen and level data NOW, then show explosion on top.
            obj.vanish()  # Remove original object first

            if gl.screen:
                # Add broken sprite immediately (it will be drawn before the explosion)
                gl.screen.active.append(broken_entity)
            # Persist to level data so it survives screen changes
            screen_num = gl.screen_manager.get_screen_number()
            gl.screen_manager.add_to_level_data(screen_num, broken_entity)

            # Create explosion (will be drawn on top of broken sprite)
            explosion = ga.Explosion(explosion_sprites, XY(exp_x, exp_y))
            if gl.screen:
                gl.screen.active.append(explosion)
        else:
            # Non-breakable: explosion only, no broken sprite left behind
            # But object is STILL removed (xplode in C code removes the object)
            # Explosion at object position (C code: NEW_X = ob->x, NEW_Y = ob->y)
            logging.debug("  Non-breakable - explosion only, removing object")
            obj_pos = obj.get_position()
            put_explosion(obj_pos.x, obj_pos.y)
            obj.vanish()  # Remove the object!

    def bow_end_explosion(self):
        """
        Create triple explosion for Level 5 bow on wall hit.
        From EB_HERO.C:214-216 (bow_end_proc):
            put_explosion(X-b,   Y);
            put_explosion(X+b*8, Y+12);
            put_explosion(X+b,   Y+24);
        """
        pos = self.get_position()
        direction = 1 if self.step > 0 else -1

        # Three vertically-spread explosions (scaled 2x)
        put_explosion(pos.x - direction * 2, pos.y)
        put_explosion(pos.x + direction * 16, pos.y + 24)
        put_explosion(pos.x + direction * 2, pos.y + 48)

        logging.debug("Bow triple explosion at x=%d", pos.x)

    def display(self):
        if self.power_level != 5:
            ga.Entity.display(self)
        else:
            # Power level 5 projectiles are 2 sprites tall (scaled 2x)
            sprite = self.sprites[self.frame % len(self.sprites)]
            pos = self.get_position()
            scaled_image = pygame.transform.scale2x(sprite.image)
            scaled_pos = XY(pos.x * 2, pos.y * 2)
            gl.display.blit(scaled_image, scaled_pos)
            # Second sprite below
            if len(self.sprites) > 1:
                sprite2 = self.sprites[(self.frame + 1) % len(self.sprites)]
                pos2 = pos + XY(0, gl.SPRITE_Y)
                scaled_image2 = pygame.transform.scale2x(sprite2.image)
                scaled_pos2 = XY(pos2.x * 2, pos2.y * 2)
                gl.display.blit(scaled_image2, scaled_pos2)

# -----------------------------------------------------------------------------
# test code below


def main():
    pass

if __name__ == "__main__":
    main()
