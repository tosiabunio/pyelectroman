"""Data loading and preprocessing module"""

import emglobals as gl
from emglobals import XY
import emdisplay as di
import emgame as ga
import json
import os
import logging
import pygame

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
        self.status = status[0:4]
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
        self.image = pygame.Surface(pos)
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
        logging.info("Loading sprite data set '%s'", set_file_path)
        jfile = open(set_file_path, "rt")
        self.set = json.load(jfile, encoding='ascii')
        sprites = 0
        for spr in range(64):
            sprites += self.set["used table"][spr]
        logging.info("Sprite data set loaded: %d sprites", sprites)
        logging.info("Loading sprite images for set '%s'", set_name)
        for spr in range(64):
            if self.is_used(spr):
                sprite = SpriteData()
                sprite.load(set_name, spr, self.get_status(spr))
                self.sprites.append(sprite)
            else:
                self.sprites.append(None)
        logging.info("%d sprite entities created",
                     64 - self.sprites.count(None))

    def get_status(self, sprite):
        return self.set["status table"][sprite * 8:sprite * 8 + 8]

    def is_used(self, sprite):
        return self.set["used table"][sprite]

    def get_sprite(self, number):
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
        logging.info("Loading level data '%s'", level_file_path)
        jfile = open(level_file_path, "rt")
        self.data = json.load(jfile, encoding='ascii')
        screens = 0
        for scr in range(256):
            screens += self.data["screens"][scr] is not None
        logging.info("Level data loaded: %d screens", screens)


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
        entity = ga.Entity([sprite], position)
        return entity

    def __init_cycleplus(self, sidx, position):
        sprite = self.get_sprite(sidx)
        entity = ga.Entity([sprite], position)
        return entity

    def __init_pulse(self, sidx, position):
        sprite = self.get_sprite(sidx)
        entity = ga.Entity([sprite], position)
        return entity

    def __init_pulseplus(self, sidx, position):
        sprite = self.get_sprite(sidx)
        entity = ga.Entity([sprite], position)
        return entity

    def __init_flash(self, sidx, position):
        sprite = self.get_sprite(sidx)
        entity = ga.Entity([sprite], position)
        return entity

    def __init_flashplus(self, sidx, position):
        sprite = self.get_sprite(sidx)
        entity = ga.Entity([sprite], position)
        return entity

    def __init_display(self, sidx, position):
        sprite = self.get_sprite(sidx)
        entity = ga.Entity([sprite], position)
        return entity

    def __init_monitor(self, sidx, position):
        sprite = self.get_sprite(sidx)
        entity = ga.Entity([sprite], position)
        return entity

    def __init_flashspecial(self, sidx, position):
        sprite = self.get_sprite(sidx)
        entity = ga.Entity([sprite], position)
        return entity

    def __init_rocketup(self, sidx, position):
        sprite = self.get_sprite(sidx)
        entity = ga.Entity([sprite], position)
        return entity

    def __init_rocketdown(self, sidx, position):
        sprite = self.get_sprite(sidx)
        entity = ga.Entity([sprite], position)
        return entity

    def __init_killingfloor(self, sidx, position):
        sprite = self.get_sprite(sidx)
        entity = ga.Entity([sprite], position)
        return entity

    def __init_checkpoint(self, sidx, position):
        sprite = self.get_sprite(sidx)
        entity = ga.Entity([sprite], position)
        return entity

    def __init_teleport(self, sidx, position):
        sprite = self.get_sprite(sidx)
        entity = ga.Entity([sprite], position)
        return entity

    def __init_exit(self, sidx, position):
        sprite = self.get_sprite(sidx)
        entity = ga.Entity([sprite], position)
        return entity

    def __init_cannonleft(self, sidx, position):
        sprite = self.get_sprite(sidx)
        entity = ga.Entity([sprite], position)
        return entity

    def __init_cannonright(self, sidx, position):
        sprite = self.get_sprite(sidx)
        entity = ga.Entity([sprite], position)
        return entity

    def __init_cannonup(self, sidx, position):
        sprite = self.get_sprite(sidx)
        entity = ga.Entity([sprite], position)
        return entity

    def __init_cannondown(self, sidx, position):
        sprite = self.get_sprite(sidx)
        entity = ga.Entity([sprite], position)
        return entity

    def __init_enemy(self, sidx, position):
        sprite = self.get_sprite(sidx)
        entity = ga.Entity([sprite], position)
        return entity

    def __get_active_entity(self, sidx, position):
        sprite = self.get_sprite(sidx)
        action = sprite.action
        return self.init_functions.get(action, self.__init_display)(sidx,
                                                                    position)

    def load(self, filename):
        self.__init__()
        logging.info("Processing level '%s'", filename)
        LevelData.load(self, filename)
        set1_name = self.data["names"][0]
        set2_name = self.data["names"][1]
        assert set1_name is not "" and set2_name is not ""
        logging.info("Loading sprite sets")
        self.set1.load(set1_name)
        self.set2.load(set2_name)
        logging.info("Level processed and sprites loaded")
        logging.info("Converting screens into sprite groups")
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
                                    activity = sprite.get_status()[0]
                                    action = sprite.action
                                    position = XY(x * gl.SPRITE_X,
                                                y * gl.SPRITE_Y)
                                    if (activity == 0x80) & (action == 0):
                                        entity = ga.Entity([sprite], position)
                                        screen.collisions.append(entity)
                                    elif activity & 0x80:
                                        entity = \
                                        self.__get_active_entity(sidx, position)
                                        screen.active.append(entity)
                                    else:
                                        entity = ga.Entity([sprite], position)
                                        screen.background.append(entity)
                self.screens.append(screen)
                cntr += 1
            else:
                self.screens.append(None)
        logging.info("Conversion done: %d screens converted", cntr)

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


# -----------------------------------------------------------------------------
# test code below


class Test:
    def __init__(self):
        self.enemies = SpriteSet()
        self.level = Level()
        self.current_screen = 0
        self.current_level = 0
        self.loop = True
        self.show_collisions = False
        self.screens_map = None
        self.screens = None
        self.shift = False
        self.key_handlers = {pygame.K_TAB: self.on_k_tab,
                             pygame.K_LEFT: self.on_k_left,
                             pygame.K_RIGHT: self.on_k_right,
                             pygame.K_UP: self.on_k_up,
                             pygame.K_DOWN: self.on_k_down,
                             pygame.K_ESCAPE: self.on_k_escape,
                             pygame.K_1: self.on_k_1,
                             pygame.K_2: self.on_k_2,
                             pygame.K_3: self.on_k_3,
                             pygame.K_4: self.on_k_4,
                             pygame.K_5: self.on_k_5,
                             pygame.K_6: self.on_k_6,
                             pygame.K_7: self.on_k_7,
                             pygame.K_8: self.on_k_8}

    def init_map(self):
        # pylint: disable-msg=E1121
        screens_map = pygame.Surface((32, 32))
        pixels = pygame.PixelArray(screens_map)
        # pylint: enable-msg=E1121
        FULL = 0x33AA33
        EMPTY = 0x333333
        for scr in range(256):
            if self.screens[scr]:
                pixels[(scr % 16) * 2 + 0][(scr / 16) * 2 + 0] = FULL
                pixels[(scr % 16) * 2 + 1][(scr / 16) * 2 + 0] = FULL
                pixels[(scr % 16) * 2 + 0][(scr / 16) * 2 + 1] = FULL
                pixels[(scr % 16) * 2 + 1][(scr / 16) * 2 + 1] = FULL
            else:
                pixels[(scr % 16) * 2 + 0][(scr / 16) * 2 + 0] = EMPTY
                pixels[(scr % 16) * 2 + 1][(scr / 16) * 2 + 0] = EMPTY
                pixels[(scr % 16) * 2 + 0][(scr / 16) * 2 + 1] = EMPTY
                pixels[(scr % 16) * 2 + 1][(scr / 16) * 2 + 1] = EMPTY
        del pixels
        return screens_map

    def show_map(self, pos):
        scr = self.current_screen
        FULL = 0xFFFFFF
        # pylint: disable-msg=E1121
        screens_map_copy = pygame.Surface((32, 32))
        screens_map_copy.blit(self.screens_map, (0, 0))
        pixels = pygame.PixelArray(screens_map_copy)
        # pylint: enable-msg=E1121
        pixels[(scr % 16) * 2 + 0][(scr / 16) * 2 + 0] = FULL
        pixels[(scr % 16) * 2 + 1][(scr / 16) * 2 + 0] = FULL
        pixels[(scr % 16) * 2 + 0][(scr / 16) * 2 + 1] = FULL
        pixels[(scr % 16) * 2 + 1][(scr / 16) * 2 + 1] = FULL
        del pixels
        gl.display.blit(screens_map_copy, pos)

    def display_screen(self, screen):
        if screen:
            for sprite in screen.background:
                sprite.display()
            for sprite in screen.collisions:
                sprite.display()
                if self.show_collisions:
                    sprite.display_collisions()
            for sprite in screen.active:
                sprite.display()
                if self.show_collisions:
                    sprite.display_collisions(pygame.Color(255, 255, 0))

    def on_k_left(self):
        if pygame.key.get_mods() & pygame.KMOD_CTRL:
            self.current_screen -= 1
            if self.current_screen < 0:
                self.current_screen = 255
        elif pygame.key.get_mods() & pygame.KMOD_SHIFT:
            pass
        else:
            pass

    def on_k_right(self):
        if pygame.key.get_mods() & pygame.KMOD_CTRL:
            self.current_screen += 1
            if self.current_screen > 255:
                self.current_screen = 0
        elif pygame.key.get_mods() & pygame.KMOD_SHIFT:
            pass
        else:
            pass

    def on_k_up(self):
        if pygame.key.get_mods() & pygame.KMOD_CTRL:
            self.current_screen -= 16
            if self.current_screen < 0:
                self.current_screen = 256 + self.current_screen
        elif pygame.key.get_mods() & pygame.KMOD_SHIFT:
            pass
        else:
            pass

    def on_k_down(self):
        if pygame.key.get_mods() & pygame.KMOD_CTRL:
            self.current_screen += 16
            if self.current_screen > 255:
                self.current_screen = self.current_screen - 256
        elif pygame.key.get_mods() & pygame.KMOD_SHIFT:
            pass
        else:
            pass

    def on_k_tab(self):
        self.show_collisions = False if self.show_collisions else True

    def on_k_1(self):
        self.current_level = 0
        self.load_level()

    def on_k_2(self):
        self.current_level = 1
        self.load_level()

    def on_k_3(self):
        self.current_level = 2
        self.load_level()

    def on_k_4(self):
        self.current_level = 3
        self.load_level()

    def on_k_5(self):
        self.current_level = 4
        self.load_level()

    def on_k_6(self):
        self.current_level = 5
        self.load_level()

    def on_k_7(self):
        self.current_level = 6
        self.load_level()

    def on_k_8(self):
        self.current_level = 7
        self.load_level()

    def on_k_escape(self):
        self.loop = False

    def on_default(self):
        pass

    def load_level(self):
        self.level.load(gl.level_names[self.current_level])
        self.screens = self.level.get_screens()
        self.screens_map = self.init_map()
        self.current_screen = self.level.get_start()

    def run(self):
        gl.data_folder = "data"
        self.enemies.load("enem")
        self.load_level()
        while self.loop:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.loop = False
                if event.type == pygame.KEYDOWN:
                    self.key_handlers.get(event.key, self.on_default)()
            screen = self.level.get_screen(self.current_screen)
            di.clear_screen()
            self.display_screen(screen)
            self.show_map((8, 8))
            di.show()

def main():
    logging.basicConfig(level=logging.DEBUG,
                        format='%(levelname)s: %(funcName)s(): %(message)s')
    di.init_display()
    test = Test()
    test.run()
    di.quit_display()

if __name__ == "__main__":
    main()