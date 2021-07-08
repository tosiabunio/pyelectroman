"""Data loading and preprocessing module"""

import emglobals as gl
from emglobals import XY
import emgame as ga
import json
import os
import logging
import pygame

flag_masks = {"active" : 0x80, "touchable" : 0x40, "shootable" : 0x20,
              "stays_active" : 0x10, "destroyable" : 0x08,
              "in_front" : 0x04, "last_frame" : 0x02, "first_frame" : 0x01}


class SpriteData:
    def __init__(self):
        self.image = None
        self.bbox = None
        self.collide = {}
        self.sidx = 0
        self.index = 0
        # object data retrived from status bytes
        self.flags = 0
        self.action = 0
        self.param = 0
        self.touch = 0
        self.init = 0

    def load(self, set_name, number, status_bytes):
        self.__init__()
        self.sidx = number
        set_file_path = os.path.join(gl.data_folder, set_name)
        image_file_path = os.path.join(set_file_path,
                                       set_name + "_%02d.png" % number)
        self.image = pygame.image.load(image_file_path).convert_alpha()
        self.image = pygame.transform.scale(self.image, (gl.SPRITE_X, gl.SPRITE_Y))
        # set up sprite information from status bytes
        self.flags = status_bytes[0]
        self.action = status_bytes[1] & 0x1F
        self.param = status_bytes[2]
        self.touch = status_bytes[3]
        self.init = (status_bytes[1] & 0xE0) >> 5
        # set up sprite bounding box from status bytes
        x = (status_bytes[4] & 0x7F) * 2
        y = (status_bytes[6] & 0x7F) * 2
        w = ((status_bytes[5] & 0x7F) - (status_bytes[4] & 0x7F)) * 2
        h = ((status_bytes[7] & 0x7F) - (status_bytes[6] & 0x7F)) * 2
        self.bbox = pygame.Rect(x, y, w, h)
        # set up collisins for all sides from status bytes
        for col in range(4):
            self.collide["LRTB"[col]] = (status_bytes[4 + col] & 0x80) == 0

    def flag(self, flag_id):
        if flag_id not in flag_masks:
            raise KeyError("Flag id not found %s", flag_id)
        mask = flag_masks[flag_id]
        return (self.flags & mask) != 0


class EmptySprite(SpriteData):
    def __init__(self):
        SpriteData.__init__(self)
        x = 0
        y = 0
        w = gl.SPRITE_X
        h = gl.SPRITE_Y
        self.bbox = pygame.Rect(x, y, w, h)
        pos = (gl.SPRITE_X, gl.SPRITE_Y)
        # pylint: disable-msg=E1121
        self.image = pygame.Surface(pos)
        # pylint: enable-msg=E1121
        self.image.set_alpha(0)
        for col in range(4):
            self.collide["LRTB"[col]] = True


class SpriteSet:
    def __init__(self):
        self.sprites = []
        self.set = None
        self.index = 0

    def __iter__(self):
        self.index = 0
        return self

    def next(self):
        if self.index == 32:
            raise StopIteration
        while self.sprites[self.index] is None:
            self.index += 1
            if self.index == 32:
                raise StopIteration
        return self.sprites[self.index]

    def load(self, set_name):
        self.__init__()
        set_file_path = os.path.join(gl.data_folder, set_name)
        set_file_path = os.path.join(set_file_path, set_name)
        set_file_path += ".ebs"
        jfile = open(set_file_path, "rt")
        self.set = json.load(jfile)
        for spr in range(64):
            if self.is_used(spr):
                sprite = SpriteData()
                sprite.load(set_name, spr, self.get_status_bytes(spr))
                self.sprites.append(sprite)
            else:
                self.sprites.append(None)
        logging.info("Sprite set '%s' loaded: %d sprites",
                     set_name, 64 - self.sprites.count(None))

    def get_status_bytes(self, sprite):
        return self.set["status table"][sprite * 8:sprite * 8 + 8]

    def is_used(self, sprite):
        return self.set["used table"][sprite]

    def get_sprite(self, number):
        """Return sprite[number] from the set"""
        assert number >= 0 and number < 64
        return self.sprites[number]

    def get_anim(self, ends):
        """Return anim sprites list based on 'ends' tuple"""
        anim = []
        for sidx in range(ends[0], ends[1] + 1):
            anim.append(self.get_sprite(sidx))
        return anim


class Screen:
    def __init__(self):
        self.background = []
        self.collisions = []
        self.active = []


class LevelData:
    def __init__(self):
        self.data = []

    def load(self, filename):
        level_file_path = os.path.join(gl.data_folder, filename)
        level_file_path += ".ebl"
        jfile = open(level_file_path, "rt")
        self.data = json.load(jfile)


#noinspection PyArgumentEqualDefault
class Level(LevelData):
    def __init__(self):
        LevelData.__init__(self)
        self.set1 = SpriteSet()
        self.set2 = SpriteSet()
        self.screens = []
        self.start = None
        self.name = None
        self.init_functions = {1: self.__init_cycle,
                               2: self.__init_pulse,
                               3: self.__init_monitor,
                               4: self.__init_display,
                               5: self.__init_cycleplus,
                               6: self.__init_pulseplus,
                               7: self.__init_flashplus,
                               9: self.__init_rocketup,
                               10: self.__init_rocketdown,
                               11: self.__init_killingfloor,
                               12: self.__init_checkpoint,
                               13: self.__init_teleport,
                               14: self.__init_flash,
                               15: self.__init_exit,
                               16: self.__init_enemy,
                               17: self.__init_cannonleft,
                               18: self.__init_cannonright,
                               19: self.__init_cannonup,
                               20: self.__init_cannondown,
                               21: self.__init_flashspecial}


    def __init_cycle(self, sidx, position):
        ends = self.get_anim_ends(sidx)
        sprites = self.get_anim(ends)
        entity = ga.Cycle(sprites, position)
        entity.frame = sidx - ends[0]
        entity.set_initial_delay(self.get_sprite(sidx).init,
                                 self.get_sprite(sidx).param)
        return entity

    def __init_cycleplus(self, sidx, position):
        ends = self.get_anim_ends(sidx)
        sprites = self.get_anim(ends)
        entity = ga.CyclePlus(sprites, position)
        preceeding = self.get_sprite(ends[0] - 1)
        entity.empty_delay = preceeding.param
        entity.set_initial_delay(self.get_sprite(sidx).init, preceeding.param)
        return entity

    def __init_pulse(self, sidx, position):
        ends = self.get_anim_ends(sidx)
        sprites = self.get_anim(ends)
        entity = ga.Pulse(sprites, position)
        entity.frame = sidx - ends[0]
        entity.set_initial_delay(self.get_sprite(sidx).init,
                                 self.get_sprite(sidx).param)
        return entity

    def __init_pulseplus(self, sidx, position):
        ends = self.get_anim_ends(sidx)
        sprites = self.get_anim(ends)
        entity = ga.PulsePlus(sprites, position)
        preceeding = self.get_sprite(ends[0] - 1)
        entity.empty_delay = preceeding.param
        entity.set_initial_delay(self.get_sprite(sidx).init, preceeding.param)
        return entity

    def __init_flash(self, sidx, position):
        sprite = self.get_sprite(sidx)
        entity = ga.Flash([sprite], position)
        entity.set_initial_delay(sprite.init, sprite.param)
        return entity

    def __init_flashspecial(self, sidx, position):
        sprite = self.get_sprite(sidx)
        entity = ga.FlashSpecial([sprite], position)
        entity.set_initial_delay(sprite.init, sprite.param)
        return entity

    def __init_flashplus(self, sidx, position):
        sprite = self.get_sprite(sidx)
        entity = ga.FlashPlus([sprite], position)
        entity.set_initial_delay(sprite.init, sprite.param)
        return entity

    def __init_display(self, sidx, position):
        sprite = self.get_sprite(sidx)
        entity = ga.Display([sprite], position)
        return entity

    def __init_monitor(self, sidx, position):
        # it doesn't seem to be used
        sprite = self.get_sprite(sidx)
        entity = ga.Monitor([sprite], position)
        return entity

    def __init_rocketup(self, sidx, position):
        sprite = self.get_sprite(sidx)
        entity = ga.RocketUp([sprite], position)
        return entity

    def __init_rocketdown(self, sidx, position):
        sprite = self.get_sprite(sidx)
        entity = ga.RocketDown([sprite], position)
        return entity

    def __init_killingfloor(self, sidx, position):
        sprite = self.get_sprite(sidx)
        entity = ga.KillingFloor([sprite], position)
        return entity

    def __init_checkpoint(self, sidx, position):
        ends = self.get_anim_ends(sidx)
        sprites = self.get_anim(ends)
        entity = ga.Checkpoint(sprites, position)
        entity.frame = sidx - ends[0]
        return entity

    def __init_teleport(self, sidx, position):
        sprite = self.get_sprite(sidx)
        base = ga.Teleport([sprite], position)
        if sprite.param == 1:
            position += XY(0, -gl.SPRITE_Y)
            sidx = self.get_anim_ends(sidx)[1] + 1
            # signal that another object needs to instantiated
            return base, sidx, position
        return base

    def __init_exit(self, sidx, position):
        sprite = self.get_sprite(sidx)
        entity = ga.Exit([sprite], position)
        return entity

    def __init_cannonleft(self, sidx, position):
        sprite = self.get_sprite(sidx)
        entity = ga.CannonLeft([sprite], position)
        return entity

    def __init_cannonright(self, sidx, position):
        sprite = self.get_sprite(sidx)
        entity = ga.CannonRight([sprite], position)
        return entity

    def __init_cannonup(self, sidx, position):
        sprite = self.get_sprite(sidx)
        entity = ga.CannonUp([sprite], position)
        return entity

    def __init_cannondown(self, sidx, position):
        sprite = self.get_sprite(sidx)
        entity = ga.CannonDown([sprite], position)
        return entity

    def __init_enemy(self, sidx, position):
        sprite = self.get_sprite(sidx)
        num = (sprite.param & 0x7F) // 3
        anims, frames = gl.enemies.get_anims(num)
        if num == 2:  # enemy types can be hardcoded
            entity = ga.EnemyFlying([sprite], position)
        else:
            entity = ga.EnemyPlatform([sprite], position)
        entity.shoots = (sprite.param & 0x80) != 0
        entity.anims = anims
        entity.frames = frames
        return entity

    def __get_active_entity(self, sidx, position):
        sprite = self.get_sprite(sidx)
        action = sprite.action
        return self.init_functions.get(action, self.__init_display)(sidx,
                                                                    position)

    def load(self, name):
        self.__init__()
        self.name = name
        LevelData.load(self, name)
        set1_name = self.data["names"][0]
        set2_name = self.data["names"][1]
        assert set1_name is not "" and set2_name is not ""
        self.set1.load(set1_name)
        self.set2.load(set2_name)
        cntr = 0
        for s in range(256):
            gl.init_screen_randoms(s)
            layers = self.data["screens"][s]
            if layers:
                screen = Screen()
                for lay in range(4):
                    layer = layers[lay]
                    if layer:
                        for y in range(gl.SCREEN_Y):
                            for x in range(gl.SCREEN_X):
                                sidx = layer[y * gl.SCREEN_X + x]
                                if sidx != 0:
                                    self.process(screen, sidx, x, y, s)
                self.screens.append(screen)
                cntr += 1
            else:
                self.screens.append(None)
        logging.info("Level '%s' loaded: %d screens", name, cntr)

    def process(self, screen, sidx, x, y, screen_number):
        sprite = self.get_sprite(sidx)
        flags = sprite.flags
        action = sprite.action
        param = sprite.param
        position = XY(x * gl.SPRITE_X, y * gl.SPRITE_Y)
        if (flags == 0x80) & (action == 0):
            entity = ga.Entity([sprite], position)
            screen.collisions.append(entity)
        elif flags & 0x80:
            entity = self.__get_active_entity(sidx, position)
            if isinstance(entity, tuple):
                # tuple is returned if initialized object has additional one
                entity[0].set_origin(screen)  # remember screen for deletion
                screen.active.append(entity[0])
                # process additional object
                entity = self.__get_active_entity(entity[1], entity[2])
            entity.set_origin(screen)  # remember screen for deletion
            screen.active.append(entity)
            if isinstance(entity, ga.Checkpoint) and param == 1:
                # active checkpoint - level start
                level_number = gl.level_names.index(self.name)
                gl.checkpoint.update(level_number, screen_number, position)
        else:
            entity = ga.Entity([sprite], position)
            screen.background.append(entity)


    def get_set(self, set_id):
        if set_id == 0:
            return self.set1
        else:
            return self.set2

    def get_screen(self, screen):
        assert screen >= 0 and screen < 256
        return self.screens[screen]

    def get_screens(self):
        return self.screens

    def get_sprite(self, number):
        assert number >= 0 and number < 128
        if number < 64:
            return self.set1.get_sprite(number)
        else:
            return self.set2.get_sprite(number - 64)

    def get_anim_ends(self, number):
        """Return sprite animation start and end numbers as a tuple"""
        s = number
        while True and (s > 0):
            if self.get_sprite(s).flag("first_frame"):
                break
            s -= 1
        start = s
        while True and (s < 128):
            if self.get_sprite(s).flag("last_frame"):
                break
            s += 1
        s = min(s, 127)
        return start, s

    def get_anim(self, ends):
        """Return anim sprites list based on 'ends' tuple"""
        anim = []
        for sidx in range(ends[0], ends[1] + 1):
            anim.append(self.get_sprite(sidx))
        return anim

# -----------------------------------------------------------------------------
# test code below

def main():
    import em
    game = em.Game()
    game.init()
    for l in range(8):
        lname = gl.level_names[l]
        print("Level:", lname)
        level = Level()
        level.load(lname)
        for s in range(256):
            screen = level.get_screen(s)
            if screen:
                actives = {}
                for a in screen.active:
                    name = a.name()
                    if name in actives:
                        actives[name] += 1
                    else:
                        actives[name] = 1
                if actives:
                    print("Screen %3d: " % s),
                    for key, value in actives.items():
                        print("%s(%d) " % (key, value)),
                    print()
    game.quit()

if __name__ == "__main__":
    main()
