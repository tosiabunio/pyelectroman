import os
import sys
import pygame
import json

screen = None
sprites = []
font = None
mfont = None
sets = []
areas = []

def binary(n, digits=8):
    return "{0:0>{1}}".format(bin(n)[2:], digits)

def init():
    global screen, font, mfont
    pygame.init()
    screen = pygame.display.set_mode((1024, 768), 0, 32)
    pygame.display.set_caption("sprite info")
    font = pygame.font.SysFont("consolas", 10)
    mfont = pygame.font.SysFont("consolas", 14)

def quit():
    pygame.quit()
    sys.exit()

class SpriteData():
    def __init__(self, img=None, status=None, size=None):
        self.img = img
        self.status = status
        self.size = size

def load_data(filename):
    global sprites
    global areas
    set_path = os.path.join(r"E:\pyelectroman-git\data", filename)
    params_path = os.path.join(set_path, filename + ".ebs")
    f = open(params_path, "rt")
    data = json.load(f)
    f.close()
    sprites = []
    areas = [None] * 64
    for s in range(64):
        sprite_path = os.path.join(set_path, filename + "_%02d.png" % s)
        if data["used table"][s]:
            img = pygame.image.load(sprite_path).convert_alpha()
            img = pygame.transform.scale2x(img)
            size = (data["size table"][s * 4 + 0],
                     data["size table"][s * 4 + 1],
                     data["size table"][s * 4 + 2],
                     data["size table"][s * 4 + 3])
            status = []
            for i in range(8):
                status.append(data["status table"][s * 8 + i])
            sprites.append(SpriteData(img, status, size))
        else:
            sprites.append(SpriteData())

def clear_screen():
    screen.fill(pygame.Color(0, 0, 0))

X_GRID = 128
Y_GRID = 64
TXT_OFS = 60
TOP_OFS = 12

def display_data(info_type):
    global sprites
    global screen
    global areas
    for x in range(8):
        for y in range(8):
            snum = y * 8 + x
            sprite = sprites[snum]
            status = sprite.status
            img = sprite.img
            if img is not None:
                x_pos = x * X_GRID + TOP_OFS
                y_pos = y * Y_GRID + (Y_GRID - 48)/2 + TOP_OFS
                screen.blit(img, (x_pos, y_pos))
                area = pygame.Rect(x_pos, y_pos, 48, 48)
                areas[snum] = area
                pygame.draw.rect(screen, pygame.Color(127, 127, 127),
                                 pygame.Rect(x_pos - 1, y_pos -1, 49, 49), 1)
                # Display sprite number below the sprite
                num_txt = font.render("%d" % snum, False, pygame.Color(200, 200, 200))
                screen.blit(num_txt, (x_pos + 20, y_pos + 50))
                if info_type == 1:
                    for stp in range(4):
                        txt = "%02X %02X" % (status[stp * 2],
                                             status[stp * 2 + 1])
                        line = font.render(txt, False,
                                           pygame.Color(255, 255, 255))
                        screen.blit(line, (x_pos + TXT_OFS,
                                           y_pos + stp * font.get_height() + 2))
                if info_type == 2:
                    for siz in range(4):
                        txt = "%s: %02d" % (("l", "r", "t", "b")[siz],
                                            sprite.size[siz])
                        line = font.render(txt, False,
                                           pygame.Color(255, 255, 255))
                        screen.blit(line, (x_pos + TXT_OFS,
                                           y_pos + siz * font.get_height() + 2))

stat_txt = ["active", "touchable", "shootable", "stays_active", "destroyable",
            "in_front", "last_frame", "first_frame"]

procs = ["",  #0 unused
         "cycle(%d, %s)",  #1
         "pulse(%d, %s)",  #2
         "monitor(%d, %s)",  #3
         "display(%d, %s)",  #4
         "cycleplus(%d, %s)",  #5
         "pulseplus(%d, %s)",  #6
         "flashplus(%d, %s)",   #7
         "",  #8 unused
         "rocketup(%d, %s)",  #9
         "rocketdown(%d, %s)",  #10
         "killingfloor(%d, %s)",  #11
         "checkpoint(%d, %s)",  #12
         "teleport(%d, %s)", #13
         "flash(%d, %s)",  #14
         "exit(%d, %s)",  #15
         "enemy(%d, %s)",  #16
         "cannonleft(%d, %s)",  #17
         "cannoright(%d, %s)",  #18
         "cannonup(%d, %s)",  #19
         "cannondown(%d, %s)",  #20
         "flashspecial(%d, %s)"]  #21


frame_cycles = ["diag", "x", "y", "const", "rand", "rand x const",
                "rand y const", "rand start"]

touch_procs = ["none", "battery", "teleport", "checkpoint", "killer", "floppy",
               "exit", "special good", "special bad"]

ZOOM_X = 32
ZOOM_Y = 580
ZOOM_TXT_X = ZOOM_X + 112
ZOOM_TXT_Y = ZOOM_Y - 4
LINE = 18

def display_zoom(sprite):
    txt = "Mouse over sprite# %d" % sprite
    line = font.render(txt, False, pygame.Color(255, 255, 255))
    screen.blit(line, (6, 756))
    sprite = sprites[sprite]
    zimg = pygame.transform.scale2x(sprite.img)
    status = sprite.status
    screen.blit(zimg, (ZOOM_X, ZOOM_Y))
    pygame.draw.rect(screen, pygame.Color(127, 127, 127),
                     pygame.Rect(ZOOM_X - 1, ZOOM_Y -1, 97, 97), 1)

    txt = "%02X (%s) %02X (%s) %02X (%s) %02X (%s)" \
        % (status[0], binary(status[0]),
           status[1], binary(status[1]),
           status[2], binary(status[2]),
           status[3], binary(status[3]))
    line = mfont.render(txt, True, pygame.Color(255, 255, 255))
    screen.blit(line, (ZOOM_TXT_X, ZOOM_TXT_Y + LINE * 0))
    txt = "%02X (%s) %02X (%s) %02X (%s) %02X (%s)" \
        % (status[4], binary(status[4]),
           status[5], binary(status[5]),
           status[6], binary(status[6]),
           status[7], binary(status[7]),)
    line = mfont.render(txt, True, pygame.Color(255, 255, 255))
    screen.blit(line, (ZOOM_TXT_X, ZOOM_TXT_Y + LINE * 1))
    bbox = sprite.size
    if bbox[0] != 0 or bbox[1] != 0 or bbox[2] != 0 or bbox[3] != 0:
        ibbox = (bbox[0], bbox[2], bbox[1] - bbox[0], bbox[3] - bbox[2])
        dbbox = pygame.Rect(ZOOM_X + ibbox[0] * 4, ZOOM_Y + ibbox[1] * 4,
                            ibbox[2] * 4, ibbox[3] * 4)
        pygame.draw.rect(screen, pygame.Color(192, 0, 192), dbbox, 1)
        txt = "Bounding box: (%d, %d, %d, %s)" % ibbox
        if status[0] & 0x80:
            dirs = ("L", "R", "T", "B")
            collide = ""
            for d in range(4):
                if not (status[4 + d] & 0x80):
                    collide += dirs[d]
            if collide:
                txt += " Collide from: %s" % collide
        line = mfont.render(txt, True, pygame.Color(255, 255, 255))
        screen.blit(line, (ZOOM_TXT_X, ZOOM_TXT_Y + LINE * 2))
    txt = "["
    for i in range(8):
        b = 0x80 >> i
        if status[0] & b:
            if txt[-1] != "[":
                txt += ", "
            txt += stat_txt[i]
    txt += "]"
    touchable = txt.find("touchable") != -1
    if txt != "[]":
        line = mfont.render(txt, True, pygame.Color(255, 255, 255))
        screen.blit(line, (ZOOM_TXT_X, ZOOM_TXT_Y + LINE * 3))
    proc_num = status[1] & 0x1F
    cycle_type = frame_cycles[(status[1]  >> 5) & 0x7]
    param = status[2]
    txt = ""
    if proc_num > 21:
        txt = "proc out of range!"
    else:
        if procs[proc_num] :
            txt = procs[proc_num] % (param, cycle_type)
    line = mfont.render(txt, True, pygame.Color(255, 255, 255))
    screen.blit(line, (ZOOM_TXT_X, ZOOM_TXT_Y + LINE * 4))
    if touchable:
        txt = "touched(%s)" % touch_procs[status[3] & 0x7]
        line = mfont.render(txt, True, pygame.Color(255, 255, 255))
        screen.blit(line, (ZOOM_TXT_X, ZOOM_TXT_Y + LINE * 5))

def display_info(current_set):
    txt = "Press 1 to display status bytes, 2 to display size bytes, \
up an down arrows to change set, ESC to exit | Loaded set: %-8s (%d/%d)"
    line = font.render(txt % (sets[current_set], current_set + 1, len(sets)),
                       False, pygame.Color(255, 255, 255))
    screen.blit(line, (6, 4))

def main_loop():
    loop = True
    info_type = 1
    current_set = 0
    while loop:
        clear_screen()
        display_info(current_set)
        display_data(info_type)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                loop = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    loop = False
                if event.key == pygame.K_1:
                    info_type = 1
                if event.key == pygame.K_2:
                    info_type = 2
                if event.key == pygame.K_DOWN:
                    if (current_set + 1) < len(sets):
                        current_set += 1
                        load_data(sets[current_set])
                if event.key == pygame.K_UP:
                    if current_set > 0:
                        current_set -= 1
                        load_data(sets[current_set])
        mouse = pygame.mouse.get_pos()
        for area in areas:
            if area and area.collidepoint(mouse):
                display_zoom(areas.index(area))
        pygame.display.flip()

def scan_for_data(data_folder):
    global sets
    sets = []
    for root, dirs, files in os.walk(data_folder):
        for file in files:
            file = file.lower()
            if file.endswith(".ebs"):
                sets.append(os.path.splitext(file)[0])

def main():
    scan_for_data(r"data")
    init()
    if sets:
        load_data(sets[0])
    main_loop()
    quit()

if __name__ == '__main__':
    main()