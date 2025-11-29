import mmap
import os
import png
import glob
import json
import struct

class MyError(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return repr(self.message)

palette = [(0, 0, 0), (0, 0, 42), (0, 42, 0), (0, 42, 42), (42, 0, 0), (42, 0, 42), (42, 21, 0), (42, 42, 42),
(21, 21, 21), (21, 21, 63), (21, 63, 21), (21, 63, 63), (63, 21, 21), (63, 21, 63), (63, 63, 21), (63, 63, 63),
(4, 4, 4), (13, 13, 13), (16, 16, 16), (18, 18, 18), (20, 20, 20), (23, 23, 23), (25, 25, 25), (29, 29, 29),
(33, 33, 33), (38, 38, 38), (42, 42, 42), (46, 46, 46), (50, 50, 50), (54, 54, 54), (59, 59, 59), (63, 63, 63),
(19, 0, 0), (24, 0, 0), (28, 0, 0), (33, 0, 0), (39, 0, 0), (45, 0, 0), (51, 0, 0), (57, 0, 0),
(63, 0, 0), (63, 20, 20), (63, 24, 24), (63, 28, 28), (63, 33, 33), (63, 39, 39), (63, 46, 46), (63, 54, 54),
(1, 16, 0), (1, 19, 0), (1, 21, 0), (1, 23, 0), (1, 24, 0), (1, 26, 0), (1, 28, 0), (2, 33, 0),
(1, 39, 0), (1, 45, 0), (1, 51, 0), (0, 57, 0), (0, 63, 0), (37, 63, 36), (47, 63, 46), (54, 63, 54),
(0, 17, 17), (0, 21, 21), (0, 25, 25), (0, 28, 28), (0, 32, 32), (0, 35, 35), (0, 39, 39), (0, 42, 42),
(0, 46, 46), (0, 49, 49), (0, 53, 53), (0, 56, 56), (0, 60, 60), (0, 63, 63), (42, 63, 63), (54, 63, 63),
(0, 11, 18), (0, 12, 22), (0, 16, 28), (0, 19, 33), (0, 23, 39), (0, 27, 45), (0, 31, 51), (0, 35, 57),
(0, 39, 63), (8, 42, 63), (16, 44, 63), (23, 47, 63), (31, 50, 63), (39, 53, 63), (46, 56, 63), (54, 59, 63),
(0, 0, 19), (2, 2, 24), (3, 3, 29), (5, 5, 33), (6, 6, 37), (8, 8, 42), (10, 10, 46), (11, 11, 50),
(13, 13, 54), (14, 14, 59), (16, 16, 63), (23, 24, 63), (31, 32, 63), (39, 39, 63), (46, 47, 63), (54, 54, 63),
(21, 15, 7), (27, 18, 9), (32, 20, 11), (37, 23, 13), (41, 25, 15), (45, 28, 17), (49, 30, 18), (54, 33, 20),
(58, 35, 22), (61, 38, 25), (63, 41, 28), (63, 44, 32), (63, 46, 36), (63, 49, 41), (63, 53, 47), (63, 56, 52),
(26, 13, 10), (29, 15, 11), (33, 16, 13), (36, 18, 13), (42, 21, 7), (48, 24, 0), (54, 27, 0), (59, 30, 0),
(63, 32, 3), (63, 39, 3), (63, 46, 4), (63, 53, 6), (59, 59, 6), (63, 63, 34), (63, 63, 46), (63, 63, 55),
(15, 17, 9), (12, 19, 9), (13, 21, 14), (14, 24, 17), (17, 29, 21), (19, 33, 24), (24, 40, 30), (29, 46, 36),
(9, 15, 19), (9, 17, 21), (13, 19, 23), (12, 22, 26), (11, 24, 30), (12, 26, 33), (17, 33, 40), (22, 39, 47),
(17, 17, 12), (19, 19, 12), (21, 21, 13), (23, 23, 14), (27, 27, 17), (30, 30, 20), (35, 35, 23), (40, 40, 28),
(18, 18, 16), (19, 20, 18), (21, 21, 19), (21, 22, 19), (23, 24, 21), (27, 28, 24), (33, 34, 30), (39, 40, 36),
(14, 17, 17), (12, 19, 19), (13, 20, 20), (15, 22, 22), (16, 25, 25), (20, 30, 30), (26, 35, 35), (34, 42, 42),
(14, 17, 19), (16, 19, 21), (19, 21, 23), (21, 23, 26), (23, 26, 29), (26, 29, 32), (33, 35, 38), (37, 39, 41),
(6, 17, 17), (6, 19, 17), (7, 20, 18), (8, 22, 20), (7, 25, 23), (10, 30, 28), (12, 38, 34), (13, 45, 40),
(21, 16, 9), (24, 18, 9), (26, 20, 9), (29, 22, 9), (31, 23, 8), (35, 25, 9), (38, 28, 11), (42, 32, 12),
(32, 15, 15), (45, 18, 15), (52, 21, 17), (55, 24, 19), (59, 28, 21), (58, 32, 25), (58, 34, 28), (57, 37, 32),
(45, 16, 3), (50, 20, 3), (54, 24, 3), (58, 27, 4), (63, 29, 13), (63, 36, 22), (63, 41, 32), (62, 49, 42),
(31, 41, 13), (35, 46, 15), (40, 55, 14), (50, 60, 17), (44, 16, 35), (47, 24, 41), (55, 30, 48), (57, 38, 51),
(50, 19, 25), (57, 22, 27), (63, 29, 36), (63, 41, 45), (25, 17, 29), (30, 21, 35), (36, 26, 41), (42, 34, 46),
(0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0),
(0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0)]

#extern struct sfh {
#  byte header  [32];
#  byte V16_pal [16];
#  byte V32_pal [32];
#  byte params  [16];
#} sprite_file_header;

class SpriteFileHeader:
    def __init__(self):
        self.header = ""
        self.V16_pal = ""
        self.V32_pal = ""
        self.params = ""

    def read(self, mapping):
        self.header = mapping.read(32)
        self.V16_pal = mapping.read(16)
        self.V32_pal = mapping.read(32)
        self.params = mapping.read(16)

#extern struct spd {
#  byte future [8];
#  byte def [288];
#  byte VGA_colors [48];
#  byte EGA_colors [32];
#  byte CGA_colors [32];
#  byte V16_colors [32];
#  byte V32_colors [48];
#} sprite_definition;

class SpriteDefinition:
    def __init__(self):
        self.future = ""
        self.packed_pixels = ""
        self.VGA_colors = ""
        self.EGA_colors = ""
        self.CGA_colors = ""
        self.V16_colors = ""
        self.V32_colors = ""
        self.pixels = []
        self.index = 0

    def palette_lookup(self, index):
        pindex = ord(self.VGA_colors[index])
        alpha = (255, 0)[pindex == 0]
        color = palette[pindex]
        final = (color[0] * 4, color[1] * 4, color[2] * 4, alpha)
        return final

    def read(self, mapping):
        self.future= mapping.read(8)
        self.packed_pixels= mapping.read(288)
        self.VGA_colors= mapping.read(48)
        self.EGA_colors= mapping.read(32)
        self.CGA_colors= mapping.read(32)
        self.V16_colors= mapping.read(32)
        self.V32_colors= mapping.read(48)
        for pp in self.packed_pixels:
            pv = (ord(pp) >> 4) & 0x0F
            pixel = self.palette_lookup(pv)
            self.pixels.append(pixel)
            pv = ord(pp) & 0x0F
            pixel = self.palette_lookup(pv)
            self.pixels.append(pixel)

    def get_pixels(self):
        return self.pixels

    def get_index(self):
        return self.index

class GGSFile:
    def __init__(self):
        self.header = SpriteFileHeader()
        self.file = None
        self.mapping = None
        self.status_table = ""
        self.size_table = ""
        self.future_size = ""
        self.definitions = []

    def open(self, filename):
        try:
            self.file = open(filename, "r+b")
            self.mapping = mmap.mmap(self.file.fileno(), 0)
        except IOError:
            raise MyError("Error: cannot open sprite file.")

    def get_number(self):
        return len(self.definitions)

    def read(self):
        self.header.read(self.mapping)
        self.status_table = self.mapping.read(512)
        self.size_table = self.mapping.read(256)
        self.future_size = self.mapping.read(2)
        skip = ord(self.future_size[0]) + (ord(self.future_size[1]) << 8)
        skip = self.mapping.read(skip)
        for i in range(64):
            used = self.mapping.read(1)
            if ord(used) != 0xFF:
                sprite_definition = SpriteDefinition()
                sprite_definition.read(self.mapping)
                sprite_definition.index = i
                self.definitions.append(sprite_definition)
            else:
                self.definitions.append(None)

    def get_sprites(self):
        return self.definitions

    def get_status_table(self):
        return struct.unpack("512B", self.status_table)

    def get_size_table(self):
        return struct.unpack("256B", self.size_table)

def main():
    try:
        folder = r"D:\PyEB\conversion\olddata"
        destination = r"D:\PyEB\conversion\newdata"
        all_files = glob.glob(os.path.join(folder, "*.ggs"))
        for filename in all_files:
            fname = os.path.split(filename)[1]
            fname = os.path.splitext(fname)[0]
            sprites_file = GGSFile()
            sprites_file.open(os.path.join(folder, filename))
            sprites_file.read()
            print("File '%s' opened." % filename)
            print("%d sprites loaded." % sprites_file.get_number())
            sprites = sprites_file.get_sprites()
            print("Converting and writing sprites and data...")
            sprites_path = os.path.join(destination, fname)
            if not os.path.exists(sprites_path):
                os.mkdir(sprites_path)
            f = open(os.path.join(sprites_path, "%s.ebs" % fname), "wt")
            used = []
            for sprite in sprites:
                used.append((True, False)[sprite is None])
            jdata = {"status table" : sprites_file.get_status_table(),
                     "size table" : sprites_file.get_size_table(),
                     "used table" : used}
            json.dump(jdata, f, sort_keys = True)
            f.close()
            for sprite in sprites:
                if sprite is not None:
                    pixels = sprite.get_pixels()
                    png_data = []
                    for row in range(24):
                        png_data.append([])
                        for col in range(24):
                            for color in pixels[row * 24 + col]:
                                png_data[row].append(color)
                    name = "%s_%02d.png" % (fname, sprite.get_index())
                    sprite_filename = os.path.join(sprites_path, name)
                    f = open(sprite_filename, "wb")
                    w = png.Writer(width = 24, height = 24, alpha = True)
                    w.write(f, png_data)
                    f.close()
            print("File processed successfully.")
        print("All done.")
    except MyError as error:
        print(error)

if __name__ == '__main__':
    main()