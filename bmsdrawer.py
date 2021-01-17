from PIL import Image, ImageDraw
from enum import Enum, auto
from abc import ABCMeta, abstractmethod
from typing import List, Tuple
from copy import copy

import bms
from oraplayexceptions import UnsupportedType

COLOR_WHITE = (255, 255, 255)
COLOR_RED = (255, 0, 0)
COLOR_BLUE = (0, 0, 255)

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
    def __init__(self, mode: KeyMode, keysize: KeySize=ModeSevenKeySize(), height: int=200, line_width: int=1):
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
        drawer.line((0, image_height - 1, image_width - 1, image_height - 1), fill=(128, 128, 128), width=self.line_width)

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

class Canvas():
    def __init__(self, width: int, height: int, barlist: List[List[bms.BarInfo]]):
        self.width = width
        self.height = height
        self.barlist = barlist

class BMSImage():
    def __init__(self, bms: bms.BMS, keymode: KeyMode=KeyMode.mode7key, keysize: KeySize=ModeSevenKeySize(),
        line_width: int=1, bar_height: int=200, canvas_height: int=1000, width_offset: int=20, height_offset: int=50):
        self.bms = bms
        self.image = None
        self.keymode = keymode
        self.keysize = keysize
        self.line_width = line_width
        self.info_width = 30
        self.bar_height = bar_height
        self.canvas = None
        self.canvas_height = canvas_height
        self.width_offset = width_offset
        self.height_offset = height_offset

    def __bar_width(self) -> int:
        return sum(self.keysize.get_widths()) + self.info_width + self.line_width * 10

    def __calc_size_of_bar(self, bar: bms.BarInfo) -> Tuple:
        width = self.__bar_width()
        height = int(self.bar_height * bar.beat)
        return (width, height)

    def __calc_info_of_canvas(self) -> None:
        cursor = [ self.width_offset, self.canvas_height - self.height_offset - 1 ]
        oneline_barlist = list()
        barlist = list()
        for bar in self.bms.bars:
            size_of_bar = self.__calc_size_of_bar(bar)
            if (cursor[1] - size_of_bar[1]) < self.height_offset:
                cursor[0] += size_of_bar[0]
                cursor[0] += self.width_offset
                cursor[1] = self.canvas_height - self.height_offset - 1
                oneline_barlist.append(barlist)
                barlist = list()
            cursor[1] -= size_of_bar[1]
            barlist.append(bar)
        cursor[0] += self.__bar_width()
        cursor[0] += self.width_offset
        oneline_barlist.append(barlist)
        self.canvas = Canvas(cursor[0], self.canvas_height, oneline_barlist)

    def __draw_bar_background(self):
        dr = ImageDraw.Draw(self.image)
        cursor = [ self.width_offset, self.canvas.height - self.height_offset - 1 ]
        for line in self.canvas.barlist:
            for b in line:
                bar_width = self.__bar_width()
                bar_height = int(self.bar_height * b.beat)

                # 黒の描画
                # 左下から右上へ描画
                dr.rectangle((cursor[0], cursor[1], cursor[0] + bar_width - 1, cursor[1] - bar_height + 1), fill=(0, 0, 0))

                # 線の描画
                # info line
                line_cursor = [ cursor[0], cursor[1] - bar_height + 1 ]
                dr.line((line_cursor[0], line_cursor[1], line_cursor[0], line_cursor[1] + bar_height - 1), \
                    fill=(128, 128, 128), width=self.line_width)
                line_cursor[0] += self.line_width
                line_cursor[0] += self.info_width

                # key line
                for i in range(len(self.keysize.get_widths())):
                    dr.line((line_cursor[0], line_cursor[1], line_cursor[0], line_cursor[1] + bar_height - 1), \
                        fill=(128, 128, 128), width=self.line_width)
                    line_cursor[0] += self.line_width
                    line_cursor[0] += self.keysize.get_widths()[i]
                dr.line((line_cursor[0], line_cursor[1], line_cursor[0], line_cursor[1] + bar_height- 1), \
                    fill=(128, 128, 128), width=self.line_width)
                dr.line((cursor[0], cursor[1], cursor[0] + bar_width - 1, cursor[1]), fill=(128, 128, 128), width=self.line_width)
                cursor[1] -= bar_height
            cursor[0] += self.__bar_width()
            cursor[0] += self.width_offset
            cursor[1] = self.canvas.height - self.height_offset - 1

    def __draw_notes(self, modify: List[int]=[0, 1, 2, 3, 4, 5, 6]):
        dr = ImageDraw.Draw(self.image)
        cursor = [ self.width_offset, self.canvas.height - self.height_offset - 1 ]
        for line in self.canvas.barlist:
            for b in line:
                bar_height = int(self.bar_height * b.beat)
                note_cursor = copy(cursor)
                note_cursor[1] -= (bar_height - 1)

                # draw bpm notes

                for bpm in b.bpm:
                    y_bpm = note_cursor[1] + int((1 - bpm.timing) * bar_height) - 1
                    dr.line((note_cursor[0], y_bpm, note_cursor[0] + self.__bar_width() - 2 * self.line_width - 1, y_bpm), \
                        fill=(0, 255, 0), width=self.line_width*2)
                    dr.text((note_cursor[0] + 2, y_bpm - 11), text=str(bpm.bpm), anchor='rs', fill=(0, 255, 0))

                # draw notes

                def __draw_note(note: bms.Note, order: int, pos: Tuple[int, int], color: Tuple) -> None:
                    x_start = pos[0]
                    x_end = x_start + self.keysize.get_widths()[order] - 1
                    y_start = pos[1] + int((1 - note.timing) * bar_height) - self.keysize.get_height() - 1
                    y_end = y_start + self.keysize.get_height()
                    dr.rectangle((x_start, y_start, x_end, y_end), fill=color)

                def __move_cursor(cr, order):
                    cr += self.keysize.get_widths()[order]
                    cr += self.line_width
                    return cr

                note_cursor[0] += self.line_width * 2
                note_cursor[0] += self.info_width
                for scratch in b.notes_scratch:
                    __draw_note(scratch, 0, note_cursor, COLOR_RED)

                color_index = [ COLOR_WHITE, COLOR_BLUE, COLOR_WHITE, COLOR_BLUE, COLOR_WHITE, COLOR_BLUE, COLOR_WHITE ]
                for i, m in enumerate(modify):
                    t = None
                    if m == 0:
                        t = b.notes_one
                    elif m == 1:
                        t = b.notes_two
                    elif m == 2:
                        t = b.notes_three
                    elif m == 3:
                        t = b.notes_four
                    elif m == 4:
                        t = b.notes_five
                    elif m == 5:
                        t = b.notes_six
                    elif m == 6:
                        t = b.notes_seven
                    note_cursor[0] = __move_cursor(note_cursor[0], i)
                    for n in t:
                        __draw_note(n, i + 1, note_cursor, color_index[i])

                cursor[1] -= bar_height
            cursor[0] += self.__bar_width()
            cursor[0] += self.width_offset
            cursor[1] = self.canvas.height - self.height_offset - 1

    def draw(self, modify: List[int] = [0, 1, 2, 3, 4, 5, 6]):
        self.__calc_info_of_canvas()
        self.image = Image.new("RGB", (self.canvas.width, self.canvas.height), (200, 200,200))
        self.__draw_bar_background()
        self.__draw_notes(modify)

class BMSDrawer():
    def __init__(self, bms: bms.BMS):
        self.bms = bms
        self.images = list()

    def draw(self):
        for b in self.bms.bars:
            self.images.append(BarImage(KeyMode.mode7key).draw(b))
