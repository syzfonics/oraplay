from abc import ABCMeta, abstractmethod
from copy import deepcopy
from math import sqrt

from common import *
from bms import *

class CalcBase(metaclass=ABCMeta):
    @abstractmethod
    def calc(self, data: List[BarInfo]):
        pass

class BpmDefinition:
    def __init__(self, number : int = 0, timing: Fraction = 0, bpm: float = 0):
        self.number = number
        self.timing = timing
        self.bpm = bpm

class InputTimeline:

    def __init__(self, bms: BMS):
        self.value = [BpmDefinition(0, 0, bms.bpm)] # BarNumber(int), Timing(Fraction), Bpm(float)
        self.beats = list()
        self.key_ms = ( list(), list(), list(), list(), list(), list(), list(), list() )

        for b in bms.bars:
            if len(b.bpm) > 0:
                for j in b.bpm:
                    new_item = BpmDefinition(b.number, j.timing, j.bpm)
                    self.value.append(new_item)
            self.beats.append(b.beat)

        current_ms = 0
        current_bpm = bms.bpm
        for b in bms.bars:
            if len(b.bpm) == 0:
                for i in range(8):
                    notes = deepcopy(b.notes[i])
                    notes.extend([x for x in b.lnnotes[i] if isinstance(x, LNStart) is True])
                    if len(notes) == 0:
                        continue
                    notes.sort(key=lambda x: x.timing)
                    for n in notes:
                        ms = current_ms + ms_per_beat(current_bpm) * (b.beat * n.timing) * 4
                        self.key_ms[i].append(ms)
                current_ms += ms_per_beat(current_bpm) * b.beat * 4
                continue

            current_beat = 0
            for change_bpm in b.bpm:
                for i in range(8):
                    notes = deepcopy(b.notes[i])
                    notes.extend([x for x in b.lnnotes[i] if isinstance(x, LNStart) is True])
                    if len(notes) == 0:
                        continue
                    notes.sort(key=lambda x: x.timing)
                    target_notes = [x for x in notes if current_beat <= x.timing and x.timing < change_bpm.timing]

                    for n in target_notes:
                        ms = current_ms + ms_per_beat(current_bpm) * b.beat * (n.timing - current_beat) * 4
                        self.key_ms[i].append(ms)

                current_ms += ms_per_beat(current_bpm) * b.beat * (change_bpm.timing - current_beat) * 4
                current_beat = change_bpm.timing
                current_bpm = change_bpm.bpm

            for i in range(8):
                notes = deepcopy(b.notes[i])
                notes.extend([x for x in b.lnnotes[i] if isinstance(x, LNStart) is True])
                if len(notes) == 0:
                    continue
                notes.sort(key=lambda x: x.timing)

                target_notes = [x for x in notes if current_beat <= x.timing]
                for n in target_notes:
                    ms = current_ms + ms_per_beat(current_bpm) * b.beat * (n.timing - current_beat) * 4
                    self.key_ms[i].append(ms)

                current_ms += ms_per_beat(current_bpm) * b.beat * (1 - current_beat) * 4

    def get_lane_timeline(self, index: int):
        return self.key_ms[index]


class CalcDensity(CalcBase):
    def __init__(self, bms: BMS):
        self.timeline = InputTimeline(bms)

    def calc(self):
        total_notes = 0
        key_input_intervals = ( list(), list(), list(), list(), list(), list(), list(), list() )
        for i in range(8):
            key_input_timings = self.timeline.get_lane_timeline(i)
            total_notes += len(key_input_timings)
            start = 0
            for input in key_input_timings:
                if start != 0:
                    key_input_intervals[i].append(input - start)
                start = input

        key_influence = float(0)
        for inputs in key_input_intervals:
            for i in inputs:
                key_influence += (float(200) / i) ** 2
        key_influence /= sqrt(total_notes)
        return key_influence

class BMSLevelCalculator():
    def __init__(self, file: str):
        self.bms = BMS(file)
        self.calc_density = CalcDensity(self.bms)

    def calc(self):
        return self.calc_density.calc()
