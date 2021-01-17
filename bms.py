import re
import json

from typing import List, Optional, Union
from fractions import Fraction

re_bar = re.compile(r"^#(?P<number>[0-9]{3})(?P<order>[0-9]{2}):(?P<value>(([0-9A-Z]{2})+)|([0-9]+\.[0-9]+))")
re_wav = re.compile(r"^#WAV(?P<order>[0-9A-Z]{2}) (?P<value>.+)")
re_bpm = re.compile(r"^#BPM(?P<order>[0-9A-Z]{2}) (?P<value>.+)")
re_stop = re.compile(r"^#STOP(?P<order>[0-9A-Z]{2}) (?P<value>.+)")

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

class BpmNote():
    def __init__(self):
        self.timing = Fraction()
        self.bpm    = float()

class StopNote():
    def __init__(self):
        self.timing = Fraction()
        self.duration = Fraction()

class BarInfo():
    def __init__(self):
        self.number        = int()
        self.notes         = ( list(), list(), list(), list(), list(), list(), list(), list() )
        self.background    = list() # List[Note]
        self.bpm           = list() # List[BpmNote]
        self.stops         = list() # List[StopNote]
        self.beat          = Fraction()

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

        self.title = str()
        self.genre = str()
        self.bpm = float()

        # def
        self.exbpm = list() # List[ExBPMDef]
        self.wav = list() # List[WavDef]
        self.stop = list() # List[StopDef]

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

    def __parse_note(self, data: str) -> Optional[List[Note]]:
        if not data:
            return None
        assert len(data) % 2 == 0
        result = list() #List[Note]
        length = int(len(data) / 2)
        for i in range(length):
            s = data[2*i:2*(i+1)]
            if s == '00':
                continue
            new_note = Note()
            new_note.defwav = int(s, 36)
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

    def __merge_item(self, src: List[Union[Note, BpmNote, StopNote]], dst: List[Union[Note, BpmNote, StopNote]]):
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

            if l.startswith("#BPM"):
                self.bpm = float(l[5:])
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
                    self.__merge_item(value, bar.notes[1])
                elif order == '12':
                    value = self.__parse_note(m.group('value'))
                    if value is None:
                        continue
                    self.__merge_item(value, bar.notes[2])
                elif order == '13':
                    value = self.__parse_note(m.group('value'))
                    if value is None:
                        continue
                    self.__merge_item(value, bar.notes[3])
                elif order == '14':
                    value = self.__parse_note(m.group('value'))
                    if value is None:
                        continue
                    self.__merge_item(value, bar.notes[4])
                elif order == '15':
                    value = self.__parse_note(m.group('value'))
                    if value is None:
                        continue
                    self.__merge_item(value, bar.notes[5])
                elif order == '16':
                    value = self.__parse_note(m.group('value'))
                    if value is None:
                        continue
                    self.__merge_item(value, bar.notes[0])
                elif order == '18':
                    value = self.__parse_note(m.group('value'))
                    if value is None:
                        continue
                    self.__merge_item(value, bar.notes[6])
                elif order == '19':
                    value = self.__parse_note(m.group('value'))
                    if value is None:
                        continue
                    self.__merge_item(value, bar.notes[7])
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

                self.__set_barinfo(bar)

        for b in self.bars:
            b.sort()

    def output_json(self, path):
        with open(path, mode='wt') as fp:
            json.dump(self, fp, cls=BMS.BMSDataJSONEncoder)
