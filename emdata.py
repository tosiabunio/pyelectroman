"""Data loading and preprocessing module"""

import emglobals as gl
from emglobals import XY
import emgame as ga
import json
import os
import logging
import pygame

status_masks = { "active" : 0x80, "touchable" : 0x40, "shootable" : 0x20,
                 "stays_active" : 0x10, "destroyable" : 0x08,
                 "in_front" : 0x04, "last_frame" : 0x02, "first_frame" : 0x01}

class SpriteData:
    def __init__(self):
        self.image = None
        self.bbox = None
        self.collide = {}
        self.status = []
        self.sidx = 0
        self.aux1 = 0
        self.aux2 = 0
        self.param = 0
        self.action = None
        self.touch = None
        self.index = 0

    def load(self, set_name, number, status):
        self.__init__()
        self.sidx = number
        set_file_path = os.path.join(gl.data_folder, set_name)
        image_file_path = os.path.join(set_file_path,
                                       set_name + "_%02d.png" % number)
        self.image = pygame.image.load(image_file_path).convert_alpha()
        self.image = pygame.transform.scale2x(self.image)
        self.status = status[0]
        #self.status = status[0:4]
        self.action = status[1] & 0x1F
        self.param = status[2]
        self.touch = status[3]
        self.aux1 = (status[1] & 0xE0) >> 5
        self.aux2 = 0
        x = (status[4] & 0x7F) * 2
        y = (status[6] & 0x7F) * 2
        w = ((status[5] & 0x7F) - (status[4] & 0x7F)) * 2
        h = ((status[7] & 0x7F) - (status[6] & 0x7F)) * 2
        self.bbox = pygame.Rect(x, y, w, h)
        for col in range(4):
            self.collide["LRTB"[col]] = (status[4 + col] & 0x80) == 0

    def get_status(self):
        return self.status

    def status_is(self, mask_id):
        if mask_id not in status_masks:
            raise KeyError("Mask id not found %s", mask_id);
        mask = status_masks[mask_id]
        return (self.status & mask) != 0


class EmptySprite(SpriteData):
    def __init__(self):
        SpriteData.__init__(self)
        self.status = 0
        self.action = 0
        self.param = 0
        self.touch = 0
        self.aux1 = 0
        self.aux2 = 0
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
        self.set = json.load(jfile, encoding='ascii')
        for spr in range(64):
            if self.is_used(spr):
                sprite = SpriteData()
                sprite.load(set_name, spr, self.get_status(spr))
                self.sprites.append(sprite)
            else:
                self.sprites.append(None)
        logging.info("Sprite set '%s' loaded: %d sprites",
                     set_name, 64 - self.sprites.count(None))

    def get_status(self, sprite):
        return self.set["status table"][sprite * 8:sprite * 8 + 8]

    def is_used(self, sprite):
        return self.set["used table"][sprite]

    def get_sprite(self, number):
        """Return sprite[number] from the set"""
        assert number >= 0 and number < 64
        return self.sprites[number]


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
        self.data = json.load(jfile, encoding='ascii')


class Level(LevelData):
    def __init__(self):
        LevelData.__init__(self)
        self.set1 = SpriteSet()
        self.set2 = SpriteSet()
        self.screens = []
        self.start = None
        self.init_functions = {1: self.__init_cycle,
                               2: self.__init_pulse,
                               3: self.__init_monitor,
                               4: self.__init_display,
                               5: self.__init_cycleplus,
                               6: self.__init_pulseplus,
                               7: self.__init_flash,
                               9: self.__init_rocketup,
                               10: self.__init_rocketup,
                               11: self.__init_killingfloor,
                               12: self.__init_checkpoint,
                               13: self.__init_teleport,
                               14: self.__init_flashplus,
                               15: self.__init_exit,
                               16: self.__init_enemy,
                               17: self.__init_cannonleft,
                               18: self.__init_cannonright,
                               19: self.__init_cannonup,
                               20: self.__init_cannondown,
                               21: self.__init_flashspecial}

    def __init_cycle(self, sidx, position):
        sprite = self.get_sprite(sidx)
        entity = ga.Cycle([sprite], position)
        return entity

    def __init_cycleplus(self, sidx, position):
        sprite = self.get_sprite(sidx)
        entity = ga.CyclePlus([sprite], position)
        return entity

    def __init_pulse(self, sidx, position):
        sprite = self.get_sprite(sidx)
        entity = ga.Pulse([sprite], position)
        return entity

    def __init_pulseplus(self, sidx, position):
        sprite = self.get_sprite(sidx)
        entity = ga.PulsePlus([sprite], position)
        return entity

    def __init_flash(self, sidx, position):
        sprite = self.get_sprite(sidx)
        entity = ga.Flash([sprite], position)
        return entity

    def __init_flashplus(self, sidx, position):
        sprite = self.get_sprite(sidx)
        entity = ga.FlashPlus([sprite], position)
        return entity

    def __init_display(self, sidx, position):
        sprite = self.get_sprite(sidx)
        entity = ga.Display([sprite], position)
        return entity

    def __init_monitor(self, sidx, position):
        sprite = self.get_sprite(sidx)
        entity = ga.Monitor([sprite], position)
        return entity

    def __init_flashspecial(self, sidx, position):
        sprite = self.get_sprite(sidx)
        entity = ga.FlashSpecial([sprite], position)
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
        entity = ga.Teleport([sprite], position)
        return entity

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
        entity = ga.Display([sprite], position)
        return entity

    def __get_active_entity(self, sidx, position):
        sprite = self.get_sprite(sidx)
        action = sprite.action
        return self.init_functions.get(action, self.__init_display)(sidx,
                                                                    position)

    def load(self, filename):
        self.__init__()
        LevelData.load(self, filename)
        set1_name = self.data["names"][0]
        set2_name = self.data["names"][1]
        assert set1_name is not "" and set2_name is not ""
        self.set1.load(set1_name)
        self.set2.load(set2_name)
        cntr = 0
        for s in range(256):
            layers = self.data["screens"][s]
            if layers:
                if self.start is None:
                    self.start = s
                screen = Screen()
                for lay in range(4):
                    layer = layers[lay]
                    if layer:
                        for y in range(gl.SCREEN_Y):
                            for x in range(gl.SCREEN_X):
                                sidx = layer[y * gl.SCREEN_X + x]
                                if sidx != 0:
                                    sprite = self.get_sprite(sidx)
                                    activity = sprite.get_status()
                                    action = sprite.action
                                    position = XY(x * gl.SPRITE_X,
                                                y * gl.SPRITE_Y)
                                    if (activity == 0x80) & (action == 0):
                                        entity = ga.Entity([sprite], position)
                                        screen.collisions.append(entity)
                                    elif activity & 0x80:
                                        entity = \
                                        self.__get_active_entity(sidx,
                                                                 position)
                                        screen.active.append(entity)
                                    else:
                                        entity = ga.Entity([sprite], position)
                                        screen.background.append(entity)
                self.screens.append(screen)
                cntr += 1
            else:
                self.screens.append(None)
        logging.info("Level '%s' loaded: %d screens", filename, cntr)

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

    def get_start(self):
        return self.start

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
            if self.get_sprite(s).status_is("first_frame"):
                break
            s -= 1
        start = s
        while True and (s < 128):
            if self.get_sprite(s).status_is("last_frame"):
                break
            s += 1
        s = min(s, 127)
        return (start, s)

    def get_anim(self, ends):
        """Return anim sprites list based on 'ends' tuple"""
        anim = []
        for sidx in range(ends[0], ends[1] + 1):
            anim.append(self.get_sprite(sidx))
        return anim


# -----------------------------------------------------------------------------
# test code below

def main():
    pass

if __name__ == "__main__":
    main()
