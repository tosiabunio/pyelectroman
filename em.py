"""Main game module"""

import emglobals as gl
from emglobals import XY
import emdata as da
import emgame as ga
import emdisplay as di
import emhero as pl
import emother as ot
import sys
import pygame
import logging


class Gameplay:
    __single = None

    def __init__(self):
        if Gameplay.__single:
            raise TypeError("Only one instance is allowed!")
        Gameplay.__single = self
        # sigleton protection code ends here
        gl.data_folder = "data"
        gl.level = da.Level()
        self.controller = ga.Controller()
        # initialize a few global objects
        gl.screen_manager = ga.ScreenManager()
        gl.player = pl.PlayerEntity(self.controller)
        gl.enemies = ot.Enemies()
        gl.weapons = ot.Weapons()
        gl.checkpoint = ga.ActiveCheckpoint()
        # initialize rest
        self.loop = True
        self.screens_map = None
        self.key_handlers = {}
        self.key_handlers[pygame.K_ESCAPE] = self.on_k_escape
        self.key_handlers[pygame.K_TAB] = self.on_k_tab
        self.key_handlers[pygame.K_LEFT] = self.on_k_left
        self.key_handlers[pygame.K_RIGHT] = self.on_k_right
        self.key_handlers[pygame.K_UP] = self.on_k_up
        self.key_handlers[pygame.K_DOWN] = self.on_k_down
        self.key_handlers[pygame.K_1] = self.on_k_1
        self.key_handlers[pygame.K_2] = self.on_k_2
        self.key_handlers[pygame.K_3] = self.on_k_3
        self.key_handlers[pygame.K_4] = self.on_k_4
        self.key_handlers[pygame.K_5] = self.on_k_5
        self.key_handlers[pygame.K_6] = self.on_k_6
        self.key_handlers[pygame.K_7] = self.on_k_7
        self.key_handlers[pygame.K_8] = self.on_k_8
        self.deferred = None

    def init_map(self):
        """Initialize level map"""
        # pylint: disable-msg=E1121
        screens_map = pygame.Surface((32, 32))
        pixels = pygame.PixelArray(screens_map)
        # pylint: enable-msg=E1121
        FULL = 0x33AA33
        EMPTY = 0x333333
        screens = gl.screen_manager.get_all_screens()
        for scr in range(256):
            if screens[scr]:
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
        """Display level map (for debug only)"""
        scr = gl.screen_manager.get_current_screen()
        CURRENT = 0xFFFFFF
        # pylint: disable-msg=E1121
        screens_map_copy = pygame.Surface((32, 32))
        screens_map_copy.blit(self.screens_map, (0, 0))
        pixels = pygame.PixelArray(screens_map_copy)
        # pylint: enable-msg=E1121
        pixels[(scr % 16) * 2 + 0][(scr / 16) * 2 + 0] = CURRENT
        pixels[(scr % 16) * 2 + 1][(scr / 16) * 2 + 0] = CURRENT
        pixels[(scr % 16) * 2 + 0][(scr / 16) * 2 + 1] = CURRENT
        pixels[(scr % 16) * 2 + 1][(scr / 16) * 2 + 1] = CURRENT
        del pixels
        gl.window.blit(screens_map_copy, pos)

    def show_info(self):
        """Display status line"""
        di.status_line.show()

    def display_screen(self, screen):
        """Display all objects (active and background on the screen"""
        if screen:
            for entity in screen.background:
                entity.display()
            for entity in screen.collisions:
                entity.display()
                if gl.show_collisions:
                    entity.display_collisions()
            self.deferred = []
            for entity in screen.active:
                deferred = entity.display()
                if deferred:
                    self.deferred.append(deferred)

    def display_deferred(self, screen):
        for deferred in self.deferred:
            deferred()

    def display_hero(self):
        """Display player's character"""
        gl.player.display()

    def move_player(self, offset):
        position = gl.player.get_position() + offset
        gl.player.set_position(position)

    def on_k_left(self):
        cs = gl.screen_manager.get_current_screen()
        if pygame.key.get_mods() & pygame.KMOD_CTRL:
            cs -= 1 if cs > 0 else -255
            gl.screen_manager.change_screen(cs)
        elif pygame.key.get_mods() & pygame.KMOD_SHIFT:
            if gl.player.get_x() >= 0:
                self.move_player((-gl.SPRITE_X, 0))

    def on_k_right(self):
        cs = gl.screen_manager.get_current_screen()
        if pygame.key.get_mods() & pygame.KMOD_CTRL:
            cs += 1 if cs < 255 else -255
            gl.screen_manager.change_screen(cs)
        elif pygame.key.get_mods() & pygame.KMOD_SHIFT:
            if gl.player.get_x() <= (gl.MAX_X):
                self.move_player((gl.SPRITE_X, 0))

    def on_k_up(self):
        cs = gl.screen_manager.get_current_screen()
        if pygame.key.get_mods() & pygame.KMOD_CTRL:
            cs -= 16 if cs > 15 else -240
            gl.screen_manager.change_screen(cs)
        elif pygame.key.get_mods() & pygame.KMOD_SHIFT:
            if gl.player.get_y() >= -2 * gl.SPRITE_Y:
                self.move_player((0, -gl.SPRITE_Y))

    def on_k_down(self):
        cs = gl.screen_manager.get_current_screen()
        if pygame.key.get_mods() & pygame.KMOD_CTRL:
            cs += 16 if cs < 240 else -240
            gl.screen_manager.change_screen(cs)
        elif pygame.key.get_mods() & pygame.KMOD_SHIFT:
            if gl.player.get_y() <= ((gl.SCREEN_Y + 2) * gl.SPRITE_Y):
                self.move_player((0, gl.SPRITE_Y))

    def on_k_tab(self):
        gl.show_collisions = False if gl.show_collisions else True
        return True

    def on_k_1(self):
        gl.current_level = 0
        self.load_level()
        return True

    def on_k_2(self):
        gl.current_level = 1
        self.load_level()
        return True

    def on_k_3(self):
        gl.current_level = 2
        self.load_level()
        return True

    def on_k_4(self):
        gl.current_level = 3
        self.load_level()
        return True

    def on_k_5(self):
        gl.current_level = 4
        self.load_level()
        return True

    def on_k_6(self):
        gl.current_level = 5
        self.load_level()
        return True

    def on_k_7(self):
        gl.current_level = 6
        self.load_level()
        return True

    def on_k_8(self):
        gl.current_level = 7
        self.load_level()
        return True

    def on_k_escape(self):
        gl.loop_main_loop = False

    def load_level(self):
        gl.level.load(gl.level_names[gl.current_level])
        gl.screen_manager.add_all_screens(gl.level.get_screens())
        self.screens_map = self.init_map()
        start_screen = gl.checkpoint.get_screen()
        start_position = gl.checkpoint.get_position()
        if start_position:
            start_position += XY(gl.SPRITE_X / 2, gl.SPRITE_Y)
            gl.screen_manager.change_screen(start_screen)
            gl.player.stand(start_position)

    def loop_begin(self):
        di.clear_screen()

    def loop_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                gl.loop_main_loop = False
        keys = pygame.key.get_pressed()
        for key, state in enumerate(keys):
            if (key in self.key_handlers) and state:
                self.key_handlers[key]()
        self.controller.update()

    def loop_run(self):
        gl.screen = gl.screen_manager.get_screen()
        if gl.screen:
            for active in gl.screen.active:
                active.update()
        gl.player.update()

    def loop_end(self):
        self.display_screen(gl.screen)
        self.display_hero()
        self.display_deferred(gl.screen)
        self.show_map((640 - 32 - 8, 8))
        self.show_info()
        di.show()

    def start(self):
        self.load_level()

    def run(self):
        gl.loop_main_loop = True
        clock = pygame.time.Clock()
        while gl.loop_main_loop:
            self.loop_begin()
            self.loop_events()
            self.loop_run()
            self.loop_end()
            clock.tick(20)  # keep constant frame rate (20fps)

    def stop(self):
        pass


class Game:
    __single = None

    def __init__(self):
        if Game.__single:
            raise TypeError("Only one instance is allowed!")
        Game.__single = self
        # sigleton protection code ends here
        if gl.log_filename:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(filename=gl.log_filename,
                                filemode="w", format=(
                                '%(levelname)s: %(funcName)s(): %(message)s'),
                                level=logging.DEBUG)

    def init(self):
        di.init_display()

    def quit(self):
        di.quit_display()

def real_main():
    game = Game()
    game.init()
    gameplay = Gameplay()
    gameplay.start()
    gameplay.run()
    gameplay.stop()
    game.quit()


def profile_main():
    # This is the main function for profiling
    # We've renamed our original main() above to real_main()
    import cProfile, pstats, StringIO
    prof = cProfile.Profile()
    prof = prof.runctx("real_main()", globals(), locals())
    stream = StringIO.StringIO()
    stats = pstats.Stats(prof, stream=stream)
    stats.sort_stats("time")  # Or cumulative
    stats.print_stats(80)  # 80 = how many to print
    # The rest is optional.
    #stats.print_callees()
    #stats.print_callers()
    logging.info("Profile data:\n%s", stream.getvalue())


main = real_main


if __name__ == "__main__":
    main()