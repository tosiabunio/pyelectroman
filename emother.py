import emdata as da


class Enemies:
    def __init__(self):
        self.data = da.SpriteSet()
        self.data.load("enem")


class Weapons:
    def __init__(self):
        self.data = da.SpriteSet()
        self.data.load("weapons")

# -----------------------------------------------------------------------------
# test code below

def main():
    pass

if __name__ == "__main__":
    main()
