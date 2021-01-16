from PIL import Image, ImageDraw
from enum import Enum, auto
from abc import ABCMeta, abstractmethod
from typing import List

import bms
from oraplayexceptions import UnsupportedType

class KeyMode(Enum):
    mode7key = auto()
    others = auto()

class KeySize(metaclass=ABCMeta):
    @abstractmethod
    def get_widths(self):
        pass

    @abstractmethod
    def get_height(self):
        pass

class ModeSevenKeySize(KeySize):
    def __init__(self, height: int=4, widths: List[int]=[40, 24, 20, 24, 20, 24, 20, 24]):
        super().__init__()
        self.height = height
        self.widths = widths

    def get_widths(self):
        return self.widths

    def get_height(self):
        return self.height

class Canvas():
    def __init__(self):
        pass

class BarImage():
    def __init__(self, mode: KeyMode, keysize: KeySize=ModeSevenKeySize(), height: int=400, line_width: int=1):
        self.mode = mode
        if self.mode is not KeyMode.mode7key:
            raise UnsupportedType("7key mode only available")
        self.keysize = keysize
        self.height = height
        self.line_width = line_width

    def draw(self, data: bms.BarInfo):

        image_width = self.line_width * 9
        image_width += sum(self.keysize.get_widths())
        image_height = int(self.height * data.beat)
        image = Image.new("RGB", (image_width, image_height), (0, 0, 0))
        drawer = ImageDraw.Draw(image)

        cursor = 0
        for i in range(len(self.keysize.get_widths())):
            drawer.line((cursor, 0, cursor, image_height - 1), fill=(128, 128, 128), width=self.line_width)
            cursor += self.line_width
            cursor += self.keysize.get_widths()[i]
        drawer.line((cursor, 0, cursor, image_height- 1), fill=(128, 128, 128), width=self.line_width)

        def __draw_notes(note, order, x, color):
            x_end = x + self.keysize.get_widths()[order] - 1
            y_start = image_height - int(note.timing * image_height) - self.keysize.get_height() - 1
            y_end = y_start + self.keysize.get_height()
            drawer.rectangle((x, y_start, x_end, y_end), fill=color)

        def __move_cursor(cr, order):
            cr += self.keysize.get_widths()[order]
            cr += self.line_width
            return cr

        cursor = self.line_width
        for scratch in data.notes_scratch:
            __draw_notes(scratch, 0, cursor, (255, 0, 0))

        cursor = __move_cursor(cursor, 0)
        for one in data.notes_one:
            __draw_notes(one, 1, cursor, (255, 255, 255))

        cursor = __move_cursor(cursor, 1)
        for two in data.notes_two:
            __draw_notes(two, 2, cursor, (0, 0, 255))

        cursor = __move_cursor(cursor, 2)
        for three in data.notes_three:
            __draw_notes(three, 3, cursor, (255, 255, 255))

        cursor = __move_cursor(cursor, 3)
        for four in data.notes_four:
            __draw_notes(four, 4, cursor, (0, 0, 255))

        cursor = __move_cursor(cursor, 4)
        for five in data.notes_five:
            __draw_notes(five, 5, cursor, (255, 255, 255))

        cursor = __move_cursor(cursor, 5)
        for six in data.notes_six:
            __draw_notes(six, 6, cursor, (0, 0, 255))

        cursor = __move_cursor(cursor, 6)
        for seven in data.notes_seven:
            __draw_notes(seven, 7, cursor, (255, 255, 255))

        return image

class BMSDrawer():
    def __init__(self, bms: bms.BMS):
        self.bms = bms
        self.images = list()

    def draw(self):
        for b in self.bms.bars:
            self.images.append(BarImage(KeyMode.mode7key).draw(b))
