import gzip
import json
from typing import Dict, List, Tuple
from enum import Enum, auto
from fractions import Fraction

from oraplayexceptions import OraPlayBaseException, FailedParseReplay, __LINE__
from oradb import SongDB
from bms import BMS, BarInfo, Note, BpmNote, LNStart, LN, LNEnd
from bmsdrawer import *

COLOR_PURPLE = (255, 0, 255)

class RandomType(Enum):
    Normal = auto()
    Mirror = auto()
    Random = auto()
    Others = auto()

class ReplayData():
    def __init__(self, path: str):
        with gzip.open(path) as f:
            self.data = json.load(f)
        if self.data["randomoption"] == 0:
            self.option = RandomType.Normal
        elif self.data["randomoption"] == 1:
            self.option = RandomType.Mirror
        elif self.data["randomoption"] == 2:
            self.option = RandomType.Random
        else:
            # 現在未対応
            self.option = RandomType.Others

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def get_file_sha256(self) -> str:
        return self.data["sha256"]

    def get_keys(self) -> List:
        return self.data["keylog"]

    def get_pattern_modify(self) -> List[int]:
        if self.option == RandomType.Normal:
            return [0, 1, 2, 3, 4, 5, 6]
        if self.option == RandomType.Mirror:
            return [0, 1, 2, 3, 4, 5, 6]
        if self.option == RandomType.Random:
            return self.data["pattern"][0]["modify"]
        if self.option == RandomType.Others:
            raise OraPlayBaseException("this option is not supported", __LINE__())

class TimeBar():
    def __init__(self):
        self.bpm = float()
        self.beats = Fraction()
        self.start_ms = int()
        self.end_ms = int()

class TimeDefinition():
    def __init__(self):
        self.start_bar = int()
        self.start_beat = Fraction(0, 1)
        self.bpm = float()
        self.start_ms = int()
        self.end_ms = int()

class BeatConvertedReplay():
    def __init__(self):
        self.time_definition = list() # List[TimeDefinition]
        self.bars = list() # List[BarInfo]
        self.modify = list() # List[int]

    def __ms_per_beat(self, bpm: int):
        return Fraction(60000 / bpm)

    def __beat_per_ms(self, bpm: int):
        return Fraction(bpm / 60000)

    def __calculate_timing(self, bms: BMS) -> List[TimeDefinition]:
        result = list()
        current_ms = 0
        current_beat = 0
        current_bpm = bms.bpm
        current_start_bar = 0
        current_start_beat = Fraction(0, 1)

        def make_new_time_definition():
            new_def = TimeDefinition()
            new_def.start_beat = current_start_beat
            new_def.start_ms = current_ms
            new_def.end_ms = current_ms + (current_beat * 4 * self.__ms_per_beat(current_bpm)) - 1
            new_def.start_bar = current_start_bar
            new_def.bpm = current_bpm
            return new_def

        def reset_current_state(b: BpmNote):
            nonlocal current_ms
            nonlocal current_beat
            nonlocal current_bpm
            nonlocal current_start_bar
            nonlocal current_start_beat

            current_ms = result[-1].end_ms + 1
            current_beat = 0
            current_bpm = b.bpm
            current_start_bar = bar.number
            current_start_beat = b.timing

        for bar in bms.bars:
            if len(bar.bpm) == 0:
                current_beat += bar.beat
                continue
            before_timing = Fraction()
            for b in bar.bpm:
                current_beat += (b.timing - before_timing)
                before_timing = b.timing

                result.append(make_new_time_definition())
                reset_current_state(b)

        result.append(make_new_time_definition())
        return result

    def convert(self, bms: BMS, replay: ReplayData, threshold: int = 100, threshold_scratch: int = 400):

        class KeyStatus():
            def __init__(self):
                self.ms = int()
                self.bar = int()
                self.pressed = False

        class NoMoreBar(Exception):
            def __init__(self):
                pass

        result = list() # List[BarInfo]
        timings = self.__calculate_timing(bms)
        status = ( KeyStatus(), KeyStatus(), KeyStatus(), KeyStatus(), KeyStatus(), KeyStatus(), KeyStatus(), KeyStatus() )

        def calc_timing(ms: int) -> Tuple[int, int]:

            def get_timing_index(ms: int) -> int:
                for i, t in enumerate(timings):
                    if t.start_ms <= ms and ms <= t.end_ms:
                        return i
                raise NoMoreBar()

            timing = timings[get_timing_index(ms)]
            beat = Fraction((ms - timing.start_ms) * self.__beat_per_ms(timing.bpm) / 4)
            result_bar_number = timing.start_bar
            result_timing = timing.start_beat + beat

            counter = 0
            while True:
                try:
                    beat_temp = bms.bars[result_bar_number].beat
                except IndexError:
                    beat_temp = 1
                if result_timing >= beat_temp:
                    result_timing -= beat_temp
                    result_bar_number += 1
                    counter += 1
                    continue
                break

            return (result_bar_number, result_timing)

        def get_key_index(key):
            # scratch
            try:
                if key["keycode"] == 7:
                    return 0
                return key["keycode"] + 1
            except KeyError:
                return 1

        def is_scratch(value: int) -> bool:
            return value == 8

        def get_barinfo(bars: List[BarInfo], number: int) -> BarInfo:
            try:
                i = next(filter(lambda x: x.number == number, bars))
                return i
            except StopIteration:
                # no element
                pass
            bar = BarInfo()
            bar.number = number
            return bar

        def set_barinfo(bars: List[BarInfo], new_item: BarInfo) -> None:
            try:
                i = next(filter(lambda x: x[1].number == new_item.number, enumerate(bars)))
                bars[i[0]] = new_item
                return
            except StopIteration:
                #no element
                pass
            bars.append(new_item)

        for key in replay.get_keys():
            key_index = get_key_index(key)
            if key_index is None:
                continue

            try:
                if key["pressed"] is True:
                    if status[key_index].pressed is True:
                        raise FailedParseReplay("duplication of press. ms={}, key_index={}".format(key["time"], key_index), __LINE__())
                    status[key_index].bar, _ = calc_timing(key["time"])
                    status[key_index].pressed = True
                    status[key_index].ms = key["time"]
                    continue
            except KeyError:
                # pressed False
                pass

            threshold_value = 0
            if is_scratch(key_index):
                threshold_value = threshold_scratch
            else:
                threshold_value = threshold

            new_key_bar, new_key_timing = calc_timing(status[key_index].ms)

            if (key["time"] - status[key_index].ms) <= threshold_value:
                target_bar = get_barinfo(result, new_key_bar)
                new_key_input = Note()
                new_key_input.timing = new_key_timing
                target_bar.notes[key_index].append(new_key_input)
                set_barinfo(result, target_bar)

                status[key_index].bar = new_key_bar
                status[key_index].pressed = False
                status[key_index].ms = key["time"]
            else:
                # LN
                new_key_bar_end, new_key_timing_end = calc_timing(key["time"])

                new_key_input_start = LNStart()
                new_key_input_start.timing = new_key_timing
                new_key_input_end = LNEnd()
                new_key_input_end.timing = new_key_timing_end
                if new_key_bar_end == new_key_bar:
                    new_key_input_ln = LN()
                    new_key_input_ln.start = new_key_timing
                    new_key_input_ln.end = new_key_timing_end
                    new_key_input_ln.is_start = True
                    new_key_input_ln.is_end = True

                    target_bar = get_barinfo(result, new_key_bar)
                    target_bar.lnnotes[key_index].extend([ new_key_input_start, new_key_input_ln, new_key_input_end ])
                    set_barinfo(result, target_bar)
                else:
                    new_key_input_ln = LN()
                    new_key_input_ln.start = new_key_input_start.timing
                    new_key_input_ln.end = 1
                    new_key_input_ln.is_start = True
                    new_key_input_ln.is_end = False

                    start_bar = get_barinfo(result, new_key_bar)
                    start_bar.lnnotes[key_index].extend([ new_key_input_start, new_key_input_ln ])
                    set_barinfo(result, start_bar)

                    target_bar_number = new_key_bar + 1
                    while target_bar_number <= new_key_bar_end:
                        if target_bar_number != new_key_bar_end:
                            new_key_input_ln = LN()
                            new_key_input_ln.start = 0
                            new_key_input_ln.end = 1
                            new_key_input_ln.is_start = False
                            new_key_input_ln.is_end = False

                            target_bar = get_barinfo(result, target_bar_number)
                            start_bar.lnnotes[key_index].append(target_bar)
                            set_barinfo(result, target_bar)
                            target_bar_number += 1
                            continue

                        # LNEndは既に生成済み
                        new_key_input_ln = LN()
                        new_key_input_ln.start = 0
                        new_key_input_ln.end = new_key_input_end.timing
                        new_key_input_ln.is_start = False
                        new_key_input_ln.is_end = True

                        target_bar = get_barinfo(result, target_bar_number)
                        target_bar.lnnotes[key_index].extend([ new_key_input_ln, new_key_input_end ])
                        set_barinfo(result, target_bar)
                        break

                status[key_index].bar = new_key_bar_end
                status[key_index].pressed = False
                status[key_index].ms = key["time"]

        for b in result:
            b.sort()

        self.bars = result

class ReplayNoteDrawer():
    def __init__(self, bar_height: int, key_size: KeySize=ModeSevenKeySize()):
        self.drawer = None
        self.bar_height = bar_height
        self.key_size = key_size
        self.color = COLOR_PURPLE

    def set_drawer(self, drawer):
        self.drawer = drawer

    def set_height(self, height):
        self.bar_height = height

    def __draw_note_implement(self, note, order, pos):
        x_start = pos[0]
        x_end = x_start + self.key_size.get_widths()[order] - 1
        y_start = pos[1] + int((1 - note.timing) * self.bar_height) - self.key_size.get_height() - 1
        y_end = y_start + self.key_size.get_height()
        self.drawer.rectangle((x_start, y_start, x_end, y_end), outline=self.color, width=2)

    def draw_note(self, notes, order, pos):
        for note in notes:
            self.__draw_note_implement(note, order, pos)

    def __draw_note_ln_layer_start(self, note, order, pos):
        x_start = pos[0]
        x_end = x_start + self.key_size.get_widths()[order] - 1
        y_start = pos[1] + int((1 - note.timing) * self.bar_height) - self.key_size.get_height() - 1
        y_end = y_start + self.key_size.get_height()
        self.drawer.line((x_start, y_start, x_start, y_end, x_end, y_end, x_end, y_start), fill=self.color, width=2)

    def __draw_note_ln_layer_end(self, note, order, pos):
        x_start = pos[0]
        x_end = x_start + self.key_size.get_widths()[order] - 1
        y_start = pos[1] + int((1 - note.timing) * self.bar_height) - self.key_size.get_height() + 1
        y_end = y_start + self.key_size.get_height()
        self.drawer.line((x_start, y_end, x_start, y_start, x_end, y_start, x_end, y_end), fill=self.color, width=2)

    def __draw_note_ln_layer(self, note, order, pos):
        x_start = pos[0]
        x_end = x_start + self.key_size.get_widths()[order] - 1
        y_start = pos[1] + int((1 - note.end) * self.bar_height) - 1
        y_end = pos[1] + int((1 - note.start) * self.bar_height) - self.key_size.get_height() - 1
        if note.is_start is True:
            y_end -= 1
        else:
            y_end += self.key_size.get_height()
        if note.is_end is True:
            y_start -= 1
        self.drawer.line((x_start, y_start, x_start, y_end), fill=self.color, width=2)
        self.drawer.line((x_end, y_start, x_end, y_end), fill=self.color, width=2)

    def draw_lnnote(self, notes, order, pos):
        for note in notes:
            if isinstance(note, bms.LNStart):
                self.__draw_note_ln_layer_start(note, order, pos)
            if isinstance(note, bms.LNEnd):
                self.__draw_note_ln_layer_end(note, order, pos)
            if isinstance(note, bms.LN):
                self.__draw_note_ln_layer(note, order, pos)

class ReplayImage(BMSImage):
    def __init__(self, bms: BMS, replay: List[BarInfo], style=None, replay_style=None, keymode: KeyMode=KeyMode.mode7key, keysize: KeySize=ModeSevenKeySize(),
        line_width: int=1, bar_height: int=200, canvas_height: int=1000, width_offset: int=20, height_offset: int=50):
        super().__init__(bms, style, keymode, keysize, line_width, bar_height,
            canvas_height, width_offset, height_offset)
        self.replay = replay
        if replay_style is not None:
            self.replay_style = replay_style
        else:
            self.replay_style = ReplayNoteDrawer(bar_height, keysize)

    def _draw_notes(self, modify: List[int]=[0, 1, 2, 3, 4, 5, 6]):
        dr = ImageDraw.Draw(self.image)
        self.style.set_drawer(dr)
        self.replay_style.set_drawer(dr)

        cursor = [ self.width_offset, self.canvas.height - self.height_offset - 1 ]
        for line in self.canvas.barlist:

            def move_cursor(cr, order):
                cr += self.keysize.get_widths()[order]
                cr += self.line_width
                return cr

            def get_bar_from_replay(number) -> BarInfo:
                i = next(filter(lambda x: x.number == number, self.replay))
                return i

            # draw bms notes

            worker_cursor = copy(cursor)

            for b in line:
                bar_height = int(self.bar_height * b.beat)
                self.style.set_height(bar_height)
                note_cursor = copy(worker_cursor)
                note_cursor[1] -= (bar_height - 1)

                # draw bpm notes

                for bpm in b.bpm:
                    y_bpm = note_cursor[1] + int((1 - bpm.timing) * bar_height) - 1
                    dr.line((note_cursor[0], y_bpm, note_cursor[0] + self.__bar_width() - 2 * self.line_width - 1, y_bpm), \
                        fill=(0, 255, 0), width=self.line_width*2)
                    dr.text((note_cursor[0] + 2, y_bpm - 11), text=str(bpm.bpm), anchor='rs', fill=(0, 255, 0))

                note_cursor[0] += self.line_width * 2
                note_cursor[0] += self.info_width
                self.style.draw_note(b.notes[0], 0, note_cursor)
                self.style.draw_lnnote(b.lnnotes[0], 0, note_cursor)

                for i, m in enumerate(modify):
                    note_cursor[0] = move_cursor(note_cursor[0], i)
                    self.style.draw_note(b.notes[m + 1], i + 1, note_cursor)
                    self.style.draw_lnnote(b.lnnotes[m + 1], i + 1, note_cursor)

                worker_cursor[1] -= bar_height

            worker_cursor = copy(cursor)

            # draw replay notes
            for b in line:
                bar_height = int(self.bar_height * b.beat)
                self.replay_style.set_height(bar_height)
                note_cursor = copy(worker_cursor)
                note_cursor[1] -= (bar_height - 1)

                replay_data = get_bar_from_replay(b.number)

                note_cursor[0] += self.line_width * 2
                note_cursor[0] += self.info_width

                self.replay_style.draw_note(replay_data.notes[0], 0, note_cursor)
                self.replay_style.draw_lnnote(replay_data.lnnotes[0], 0, note_cursor)

                for i in range(7):
                    note_cursor[0] = move_cursor(note_cursor[0], i)
                    self.replay_style.draw_note(replay_data.notes[i + 1], i + 1, note_cursor)
                    self.replay_style.draw_lnnote(replay_data.lnnotes[i + 1], i + 1, note_cursor)

                worker_cursor[1] -= bar_height

            cursor[0] += self._bar_width()
            cursor[0] += self.width_offset
            cursor[1] = self.canvas.height - self.height_offset - 1

    def draw(self, modify: List[int] = [0, 1, 2, 3, 4, 5, 6]):
        self._calc_info_of_canvas()
        self.image = Image.new("RGB", (self.canvas.width, self.canvas.height), (200, 200,200))
        self._draw_bar_background()
        self._draw_notes(modify)

class Replay():
    def __init__(self, file: str, db: str):
        self.replay_data = ReplayData(file)
        file_sha256 = self.replay_data.get_file_sha256()
        file_path = SongDB(db).get_file_path(file_sha256)
        self.bms = BMS(file_path)
        self.convert = BeatConvertedReplay()
        self.image = None

    def draw(self, threshold: int=100, threshold_scratch: int=400):
        self.convert.convert(self.bms, self.replay_data, threshold, threshold_scratch)
        image = BMSImage(self.convert.bars)
        image.draw()
        self.image = image.image

    def draw_replay(self, threshold: int=100, threshold_scratch: int=400):
        self.convert.convert(self.bms, self.replay_data, threshold, threshold_scratch)
        image = ReplayImage(self.bms, self.convert.bars)
        image.draw(modify=self.replay_data.get_pattern_modify())
        self.image = image.image
