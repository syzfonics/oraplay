import re
import json

from typing import List, Optional, Union
from fractions import Fraction
from enum import Enum, auto

from oraplayexceptions import InvalidFormat, __LINE__

re_bar = re.compile(r"^#(?P<number>[0-9]{3})(?P<order>[0-9]{2}):(?P<value>(([0-9A-Z]{2})+)|([0-9]+\.[0-9]+))")
re_wav = re.compile(r"^#WAV(?P<order>[0-9A-Z]{2}) (?P<value>.+)")
re_bpm = re.compile(r"^#BPM(?P<order>[0-9A-Z]{2}) (?P<value>.+)")
re_stop = re.compile(r"^#STOP(?P<order>[0-9A-Z]{2}) (?P<value>.+)")

class LNType(Enum):
    LNTypeOne = auto()
    LNObj = auto()
    NoLN = auto()

class ExBPMDef():
    def __init__(self):
        self.order = int()
        self.bpm   = float()

class WavDef():
    def __init__(self):
        self.order = int()
        self.wav = str()

class StopDef():
    def __init__(self):
        self.order = int()
        self.value = int()

class Note():
    def __init__(self):
        self.timing = Fraction()
        self.defwav = int()

class LNBase():
    pass

class LNStart(LNBase):
    def __init__(self):
        self.timing = Fraction()
        self.defwav = int()

    def __str__(self):
        return 'LNBase timing:{}, defwav:{}'.format(self.timing, self.defwav)

class LNEnd(LNBase):
    def __init__(self):
        self.timing = Fraction()
        self.defwav = int()

    def __str__(self):
        return 'LNEnd timing:{}, defwav:{}'.format(self.timing, self.defwav)

class LN(LNBase):
    def __init__(self):
        self.is_start = False
        self.is_end = False
        self.start = Fraction()
        self.end = Fraction()

    def __str__(self):
        return 'LN start:{}({}), end:{}({})'.format(self.start, self.is_start, self.end, self.is_end)

class BpmNote():
    def __init__(self):
        self.timing = Fraction()
        self.bpm    = float()

class StopNote():
    def __init__(self):
        self.timing = Fraction()
        self.duration = Fraction()

class LNObj():
    def __init__(self, define: int=0):
        self.define = define

class BarInfo():
    def __init__(self):
        self.number        = int()
        self.notes         = ( list(), list(), list(), list(), list(), list(), list(), list() )
        self.lnnotes       = ( list(), list(), list(), list(), list(), list(), list(), list() )
        self.background    = list() # List[Note]
        self.bpm           = list() # List[BpmNote]
        self.stops         = list() # List[StopNote]
        self.beat          = Fraction(1, 1)

    def sort(self):
        sortkey = lambda x: x.timing
        self.notes[0].sort(key=sortkey)
        self.notes[1].sort(key=sortkey)
        self.notes[2].sort(key=sortkey)
        self.notes[3].sort(key=sortkey)
        self.notes[4].sort(key=sortkey)
        self.notes[5].sort(key=sortkey)
        self.notes[6].sort(key=sortkey)
        self.notes[7].sort(key=sortkey)
        self.bpm.sort(key=sortkey)
        self.stops.sort(key=sortkey)

class LNInfo():
    def __init__(self):
        self.is_start = False
        self.timing = Fraction()
        self.number = int() # Bar Number Info
        self.defwav = int()

class BMS():

    class BMSDataJSONEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, ExBPMDef):
                return { 'order': obj.order, 'bpm': obj.bpm }
            elif isinstance(obj, WavDef):
                return { 'order': obj.order, 'wav': obj.wav }
            elif isinstance(obj, StopDef):
                return { 'order': obj.order, 'value': obj.value }
            elif isinstance(obj, Note):
                return { 'timing': str(obj.timing), 'defwav': obj.defwav }
            elif isinstance(obj, BpmNote):
                return { 'timing': str(obj.timing), 'bpm': obj.bpm }
            elif isinstance(obj, StopNote):
                return { 'timing': str(obj.timing), 'duration': str(obj.duration) }
            elif isinstance(obj, BarInfo):
                return {
                    'number': obj.number,
                    'backgroud': obj.background,
                    'bpm': obj.bpm,
                    'beat': str(obj.beat),
                    'stop': obj.stops,
                    'notes_scratch': obj.notes[0],
                    'notes_one'    : obj.notes[1],
                    'notes_two'    : obj.notes[2],
                    'notes_three'  : obj.notes[3],
                    'notes_four'   : obj.notes[4],
                    'notes_five'   : obj.notes[5],
                    'notes_six'    : obj.notes[6],
                    'notes_seven'  : obj.notes[7]
                }
            elif isinstance(obj, BMS):
                return {
                    'title': obj.title,
                    'genre': obj.genre,
                    'bpm': obj.bpm,
                    'exbpm': obj.exbpm,
                    'wav': obj.wav,
                    'stop': obj.stop,
                    'bars': obj.bars
                }
            return super(BMS.BMSDataJSONEncoder, self).default(obj)

    def __init__(self, file: str):
        with open(file) as f:
            lines = f.readlines()

        self.lntype = LNType.LNTypeOne
        self.ln_info = ( LNInfo(), LNInfo(), LNInfo(), LNInfo(), LNInfo(), LNInfo(), LNInfo(), LNInfo() )

        self.title = str()
        self.genre = str()
        self.bpm = float()

        # def
        self.exbpm = list() # List[ExBPMDef]
        self.wav = list() # List[WavDef]
        self.stop = list() # List[StopDef]
        self.lnobj = list() # List[LNObj]

        self.bars = list() # List[BarInfo]

        self.__parse(lines)

    def __str__(self):
        pass

    def __get_barinfo(self, number: int) -> BarInfo:
        try:
            i = next(filter(lambda x: x.number == number, self.bars))
            return i
        except StopIteration:
            # no element
            pass
        bar = BarInfo()
        bar.number = number
        return bar

    def __set_barinfo(self, bar: BarInfo) -> None:
        try:
            i = next(filter(lambda x: x[1].number == bar.number, enumerate(self.bars)))
            self.bars[i[0]] = bar
            return
        except StopIteration:
            #no element
            pass
        self.bars.append(bar)

    def __parse_note(self, data: str) -> Optional[List[Union[Note, LNEnd]]]:
        if not data:
            return None
        assert len(data) % 2 == 0
        result = list() #List[Note]
        length = int(len(data) / 2)
        for i in range(length):
            s = data[2*i:2*(i+1)]
            if s == '00':
                continue
            define = int(s, 36)
            if self.lntype == LNType.LNObj:
                for l in self.lnobj:
                    if l.define == define:
                        new_ln = LNEnd()
                        new_ln.defwav = define
                        new_ln.timing = Fraction(i, length)
                        result.append(new_ln)
                        break
            else:
                new_note = Note()
                new_note.defwav = define
                new_note.timing = Fraction(i, length)
                result.append(new_note)
        return result

    def __parse_bpm(self, data: str) -> Optional[List[BpmNote]]:
        if not data:
            return None
        assert len(data) % 2 == 0
        result = list() # List[BpmNote]
        length = int(len(data) / 2)
        for i in range(length):
            s = data[2*i:2*(i+1)]
            if s == '00':
                continue
            new_bpm = BpmNote()
            new_bpm.bpm = int(s, 16)
            new_bpm.timing = Fraction(i, length)
            result.append(new_bpm)
        return result

    def __parse_exbpm(self, data: str) -> Optional[List[BpmNote]]:
        if not data:
            return None
        assert len(data) % 2 == 0
        result = list() # List[BpmNote]
        length = int(len(data) / 2)
        for i in range(length):
            s = data[2*i:2*(i+1)]
            if s == '00':
                continue
            new_bpm = BpmNote()
            new_bpm.bpm = next(filter(lambda x: x.order == int(s, 36), self.exbpm)).bpm
            new_bpm.timing = Fraction(i, length)
            result.append(new_bpm)
        return result

    def __parse_stop(self, data: str) -> Optional[List[StopNote]]:
        if not data:
            return None
        assert len(data) % 2 == 0
        result = list() # List[StopNote]
        length = int(len(data) / 2)
        for i in range(length):
            s = data[2*i:2*(i+1)]
            if s == '00':
                continue
            new_stop = StopNote()
            new_stop.duration = Fraction(next(filter(lambda x: x.order == int(s, 36), self.stop)).value, 192)
            result.append(new_stop)
        return result

    def __generate_ln_sub(self, order: int, start_bar: int, end_bar: int):
        for i in range(start_bar, end_bar):
            target_bar = self.__get_barinfo(i)
            target_ln_lane = target_bar.lnnotes[order]
            new_ln_line = LN()
            new_ln_line.is_start = False
            new_ln_line.start = 0
            new_ln_line.is_end = False
            new_ln_line.end = 1
            target_ln_lane.append(new_ln_line)

    def __generate_ln(self, order: int, notes: List[Note], bar: BarInfo):
        target_ln_info = self.ln_info[order]
        target_ln_lane = bar.lnnotes[order]

        for n in notes:
            if target_ln_info.is_start is True:
                new_ln_line = LN()
                new_ln_end = LNEnd()
                if target_ln_info.number != bar.number:
                    self.__generate_ln_sub(order, target_ln_info.number + 1, bar.number)
                    new_ln_line.is_start = False
                    new_ln_line.start = 0
                else:
                    new_ln_line.is_start = True
                    new_ln_line.start = target_ln_info.timing
                new_ln_line.is_end = True
                new_ln_line.end = n.timing
                new_ln_end.timing = n.timing
                new_ln_end.defwav = n.defwav
                target_ln_lane.append(new_ln_line)
                target_ln_lane.append(new_ln_end)

                target_ln_info.is_start = False
            else: # target_ln_info.is_start is False
                new_ln_note = LNStart()
                new_ln_note.timing = n.timing
                new_ln_note.defwav = n.defwav
                target_ln_lane.append(new_ln_note)

                target_ln_info.is_start = True

            target_ln_info.timing = n.timing
            target_ln_info.defwav = n.defwav
            target_ln_info.number = bar.number

        if target_ln_info.is_start is True:
            new_ln_line = LN()
            new_ln_line.is_start =True
            new_ln_line.start = target_ln_info.timing
            new_ln_line.is_end = False
            new_ln_line.end = 1
            target_ln_lane.append(new_ln_line)

    def __convert_to_ln(self, src, dst, num, order):
        b = list() # List[bool]
        for i, s in enumerate(src):
            if isinstance(s, LNEnd) is True:
                b.append(False)
                if i == 0:
                    for j in range(num):
                        before = self.__get_barinfo(num - j - 1)
                        target_lane = before.notes[order]
                        if len(target_lane) == 0:
                            ln_mid = LN()
                            ln_mid.is_start = False
                            ln_mid.start = 0
                            ln_mid.is_end = False
                            ln_mid.end = 1
                            before.lnnotes[order].append(ln_mid)
                            continue
                        target_note = target_lane[-1]
                        ln_start = LNStart()
                        ln_start.timing = target_note.timing
                        ln_start.defwav = target_note.defwav
                        ln_mid = LN()
                        ln_mid.is_start = True
                        ln_mid.start = target_note.timing
                        ln_mid.is_end = False
                        ln_mid.end = 1
                        before.lnnotes[order].append(ln_start)
                        before.lnnotes[order].append(ln_mid)
                        target_lane = target_lane[:-1]
                        break
                else:
                    assert isinstance(src, Note) is True
                    ln_start = LNStart()
                    ln_start.timing = src[i].timing
                    ln_start.defwav = src[i].defwav
                    ln_mid = LN()
                    ln_mid.is_start = True
                    ln_mid.start = src[i].timing
                    ln_mid.is_start = True
                    ln_mid.end = s.timing
                    dst.appned(ln_start)
                    dst.append(ln_mid)
                    dst.append(s)
            else:
                b.append(True)

        assert len(src) == len(b)
        new_src = [x for i, x in enumerate(src) if b[i] is True]
        src = new_src

    def __merge_item_with_ln(self, src: List[Union[Note, BpmNote, StopNote, LNEnd]], \
        dst: List[Union[Note, BpmNote, StopNote]], num, order, dst_ln: List[Union[LNBase]]=None):
        if self.lntype == LNType.LNObj:
            self.__convert_to_ln(src, dst_ln, num, order)
        for s in src:
            found = False
            for d in dst:
                if d.timing == s.timing:
                    found = True
                    break
            if not found:
                dst.append(s)

    def __merge_item(self, src: List[Union[Note, BpmNote, StopNote, LNEnd]], dst: List[Union[Note, BpmNote, StopNote]]):
        for s in src:
            found = False
            for d in dst:
                if d.timing == s.timing:
                    found = True
                    break
            if not found:
                dst.append(s)

    def __merge_all_item(self, src: List[Note], dst: List[Note]):
        dst.extend(src)

    def __parse(self, lines: List[str]):
        for line in lines:
            l = line.rstrip()

            # not command
            if not l.startswith("#"):
                continue

            if l.startswith("#TITLE"):
                self.title = l[7:]
                continue

            if l.startswith("#GENRE"):
                self.genre = l[7:]
                continue

            if l.startswith("#BPM "):
                self.bpm = float(l[5:])
                continue

            # LNTYPE
            if l.startswith("#LNTYPE 1"):
                self.lntype = LNType.LNTypeOne
                continue

            # LNOBJ
            if l.startswith("#LNOBJ"):
                self.lnobj.append(LNObj(int(l[7:])))
                self.lntype = LNType.LNObj
                continue

            m = re_bpm.match(l)
            if m is not None:
                new_exbpm = ExBPMDef()
                new_exbpm.order = int(m.group('order'), 36)
                new_exbpm.bpm = m.group('value')
                self.exbpm.append(new_exbpm)
                continue

            m = re_wav.match(l)
            if m is not None:
                new_wav = WavDef()
                new_wav.order = int(m.group('order'), 36)
                new_wav.wav = m.group('value')
                self.wav.append(new_wav)
                continue

            m = re_stop.match(l)
            if m is not None:
                new_stop = StopDef()
                new_stop.order = int(m.group('order'), 36)
                new_stop.value = int(m.group('value'))
                continue

            m = re_bar.match(l)
            if m is not None:
                bar = self.__get_barinfo(int(m.group('number')))
                order = m.group('order')

                if order == '11':
                    value = self.__parse_note(m.group('value'))
                    if value is None:
                        continue
                    self.__merge_item_with_ln(value, bar.notes[1], bar.number, 1, bar.lnnotes[1])
                elif order == '12':
                    value = self.__parse_note(m.group('value'))
                    if value is None:
                        continue
                    self.__merge_item_with_ln(value, bar.notes[2], bar.number, 2, bar.lnnotes[2])
                elif order == '13':
                    value = self.__parse_note(m.group('value'))
                    if value is None:
                        continue
                    self.__merge_item_with_ln(value, bar.notes[3], bar.number, 3, bar.lnnotes[3])
                elif order == '14':
                    value = self.__parse_note(m.group('value'))
                    if value is None:
                        continue
                    self.__merge_item_with_ln(value, bar.notes[4], bar.number, 4, bar.lnnotes[4])
                elif order == '15':
                    value = self.__parse_note(m.group('value'))
                    if value is None:
                        continue
                    self.__merge_item_with_ln(value, bar.notes[5], bar.number, 5, bar.lnnotes[5])
                elif order == '16':
                    value = self.__parse_note(m.group('value'))
                    if value is None:
                        continue
                    self.__merge_item_with_ln(value, bar.notes[0], bar.number, 0, bar.lnnotes[0])
                elif order == '18':
                    value = self.__parse_note(m.group('value'))
                    if value is None:
                        continue
                    self.__merge_item_with_ln(value, bar.notes[6], bar.number, 6, bar.lnnotes[6])
                elif order == '19':
                    value = self.__parse_note(m.group('value'))
                    if value is None:
                        continue
                    self.__merge_item_with_ln(value, bar.notes[7], bar.number, 7, bar.lnnotes[7])
                elif order == '01':
                    value = self.__parse_note(m.group('value'))
                    if value is None:
                        continue
                    self.__merge_all_item(value, bar.background)
                elif order == '03':
                    value = self.__parse_bpm(m.group('value'))
                    if value is None:
                        continue
                    self.__merge_item(value, bar.bpm)
                elif order == '08':
                    value = self.__parse_exbpm(m.group('value'))
                    if value is None:
                        continue
                    self.__merge_item(value, bar.bpm)
                elif order == '09':
                    value = self.__parse_stop(m.group('value'))
                    if value is None:
                        continue
                    self.__merge_item(value, bar.stops)
                elif order == '02':
                    # beat
                    bar.beat = Fraction(float(m.group('value')))

                # LNTYPE 1
                elif order == '51':
                    if self.lntype != LNType.LNTypeOne:
                        raise InvalidFormat("using LN lane without '#LNTYPE 1'", __LINE__())
                    value = self.__parse_note(m.group('value'))
                    if value is None:
                        continue
                    self.__generate_ln(1, value, bar)
                elif order == '52':
                    if self.lntype != LNType.LNTypeOne:
                        raise InvalidFormat("using LN lane without '#LNTYPE 1'", __LINE__())
                    value = self.__parse_note(m.group('value'))
                    if value is None:
                        continue
                    self.__generate_ln(2, value, bar)
                elif order == '53':
                    if self.lntype != LNType.LNTypeOne:
                        raise InvalidFormat("using LN lane without '#LNTYPE 1'", __LINE__())
                    value = self.__parse_note(m.group('value'))
                    if value is None:
                        continue
                    self.__generate_ln(3, value, bar)
                elif order == '54':
                    if self.lntype != LNType.LNTypeOne:
                        raise InvalidFormat("using LN lane without '#LNTYPE 1'", __LINE__())
                    value = self.__parse_note(m.group('value'))
                    if value is None:
                        continue
                    self.__generate_ln(4, value, bar)
                elif order == '55':
                    if self.lntype != LNType.LNTypeOne:
                        raise InvalidFormat("using LN lane without '#LNTYPE 1'", __LINE__())
                    value = self.__parse_note(m.group('value'))
                    if value is None:
                        continue
                    self.__generate_ln(5, value, bar)
                elif order == '56':
                    if self.lntype != LNType.LNTypeOne:
                        raise InvalidFormat("using LN lane without '#LNTYPE 1'", __LINE__())
                    value = self.__parse_note(m.group('value'))
                    if value is None:
                        continue
                    self.__generate_ln(0, value, bar)
                elif order == '58':
                    if self.lntype != LNType.LNTypeOne:
                        raise InvalidFormat("using LN lane without '#LNTYPE 1'", __LINE__())
                    value = self.__parse_note(m.group('value'))
                    if value is None:
                        continue
                    self.__generate_ln(6, value, bar)
                elif order == '59':
                    if self.lntype != LNType.LNTypeOne:
                        raise InvalidFormat("using LN lane without '#LNTYPE 1'", __LINE__())
                    value = self.__parse_note(m.group('value'))
                    if value is None:
                        continue
                    self.__generate_ln(7, value, bar)

                self.__set_barinfo(bar)

        for b in self.bars:
            b.sort()

        # add blank bar
        blank_number = list()
        for i in range(len(self.bars)):
            try:
                b = next(filter(lambda x: x.number == i, self.bars))
            except StopIteration:
                blank_number.append(i)

        for n in blank_number:
            new_item = BarInfo()
            new_item.number = n
            self.bars.insert(n, new_item)

    def output_json(self, path):
        with open(path, mode='wt') as fp:
            json.dump(self, fp, cls=BMS.BMSDataJSONEncoder)
