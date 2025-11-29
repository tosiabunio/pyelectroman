import mmap
import os
import json
import struct
import glob

#struct
#{
#  byte gge_header [32];
#  byte name       [2][9];
#  byte param      [16];
#  byte map        [256];
#} header;

class LevelFile:
    def __init__(self):
        self.header = ""
        self.names = []
        self.params = ()
        self.mapping = None
        self.map = []
        self.screen_offsets = []
        self.screens = []

    def open(self, filename):
        self.file = open(filename, "r+b")
        self.mapping = mmap.mmap(self.file.fileno(), 0)

    def read(self):
        assert self.mapping is not None
        self.header = self.mapping.read(32)
        self.names.append(self.mapping.read(9))
        self.names[0] = (self.names[0], self.names[0]
                         [:self.names[0].index('\x00')])[self.names[0][-1] == '\x00']
        self.names.append(self.mapping.read(9))
        self.names[1] = (self.names[1], self.names[1]
                         [:self.names[1].index('\x00')])[self.names[1][-1] == '\x00']
        self.names[0] = self.names[0].lower()
        self.names[1] = self.names[1].lower()
        self.params = struct.unpack("16B",self.mapping.read(16))
        self.map = self.mapping.read(256)
        self.map = list(struct.unpack("256B",self.map))
        self.future = self.mapping.read(2)
        self.future = struct.unpack("H",self.future)[0]
        self.future = self.mapping.read(self.future)
        for screen_index in range(256):
            if self.map[screen_index] != 0:
                offsets_data = struct.unpack("4H",self.mapping.read(8))
                offsets = []
                for ofs in offsets_data:
                    offsets.append((None ,ofs - 2048)[ofs != 0])
                self.screen_offsets.append(tuple(offsets))
                self.mapping.read(8)
            else:
                self.screen_offsets.append(None)
        level_data_size = self.mapping.size() - self.mapping.tell()
        self.level_data = self.mapping.read(level_data_size)
        self.level_data = list(struct.unpack("%dB" % level_data_size,
                                             self.level_data))
        for scr in range(256):
            if self.map[scr] == 0:
                self.screens.append(None)
            else:
                self.screens.append([[0] * 104, [0] * 104, [0] * 104, [0] * 104])
                for plane in range(4):
                    data_pointer = self.screen_offsets[scr][plane]
                    if data_pointer is None:
                        self.screens[scr][plane] = None
                    else:
                        if self.level_data[data_pointer] > 127:
                            # kompresja w pionie
                            data_pointer += 1
                            rpt = 0
                            for x in range(13):
                                for y in range(8):
                                    robj = self.level_data[data_pointer]
                                    pobj = robj & 0x7F
                                    if robj > 127:
                                        if rpt == 0:
                                            rpt = self.level_data[data_pointer + 1]
                                        else:
                                            rpt -= 1
                                            if rpt == 0:
                                                data_pointer += 2
                                    else:
                                        data_pointer += 1
                                    self.screens[scr][plane][y * 13 + x] = pobj
                        else:
                            # kompresja w poziomie
                            data_pointer += 1
                            rpt = 0
                            for y in range(8):
                                for x in range(13):
                                    robj = self.level_data[data_pointer]
                                    pobj = robj & 0x7F
                                    if robj > 127:
                                        if rpt == 0:
                                            rpt = self.level_data[data_pointer + 1]
                                        else:
                                            rpt -= 1
                                            if rpt == 0:
                                                data_pointer += 2
                                    else:
                                        data_pointer += 1
                                    self.screens[scr][plane][y * 13 + x] = pobj

    def get_screens(self):
        return self.screens

    def get_names(self):
        return self.names

    def get_params(self):
        return self.params

def main():
    folder = r"D:\PyEB\conversion\olddata"
    destination = r"D:\PyEB\conversion\newdata"
    all_files = glob.glob(os.path.join(folder, "*.ggc"))
    for filename in all_files:
        fname = os.path.splitext(os.path.split(filename)[1])[0]
        print("Processing level file:", fname)
        level = LevelFile()
        level.open(filename)
        level.read()
        # write as JSON data
        jdata = {"params" : level.get_params(),
                 "names" : level.get_names(),
                 "screens" : level.get_screens()}
        f = open(os.path.join(destination, "%s.ebl" % fname), "wt")
        json.dump(jdata, f, sort_keys = True)
        f.close()
    print("Done.")


if __name__ == '__main__':
    main()