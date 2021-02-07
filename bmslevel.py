from abc import ABCMeta, abstractmethod
from copy import deepcopy
from math import sqrt
from collections import Counter

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

            def set_all_notes(notes, lnnotes, stops):
                result = deepcopy(notes)
                result.extend([x for x in lnnotes if isinstance(x, LNStart) is True])
                if len(result) == 0:
                    return None
                result.sort(key=lambda x: x.timing)
                if len(stops) == 0:
                    return result

                stop_process = deepcopy(result)
                for stop in stops:
                    for i, n in enumerate(result):
                        if stop.timing < n.timing:
                            stop_process[i].timing += Fraction(stop.duration, 192)

                result = stop_process
                return result

            if len(b.bpm) == 0:
                for i in range(8):
                    notes = set_all_notes(b.notes[i], b.lnnotes[i], b.stops)
                    if notes is None:
                        continue

                    for n in notes:
                        ms = current_ms + ms_per_beat(current_bpm) * (b.beat * n.timing) * 4
                        self.key_ms[i].append(ms)

                stop_beats = 0
                for stop in b.stops:
                    stop_beats += Fraction(stop.duration, 192)
                current_ms += ms_per_beat(current_bpm) * (b.beat + stop_beats) * 4

                c = Counter(self.key_ms[i])
                dup = [x for x in c.most_common() if x[1] > 1]
                assert len(dup) == 0, 'duplicates note?, {}, {}, {}'.format(b.number, i, b.beat)
                continue

            def set_bpm_notes():
                bpms = deepcopy(b.bpm)
                last_bpm = BpmNote()
                last_bpm.timing = 1
                last_bpm.bpm = bpms[-1].bpm
                bpms.append(last_bpm)
                if len(b.stops) == 0:
                    return bpms
                stop_process = deepcopy(bpms)
                for stop in b.stops:
                    for i, bpm in enumerate(bpms):
                        if stop.timing < bpm.timing:
                            stop_process[i].timing += Fraction(stop.duration, 192)

                bpms = stop_process
                return bpms

            current_beat = 0
            bpms = set_bpm_notes()

            for change_bpm in bpms:
                for i in range(8):
                    notes = set_all_notes(b.notes[i], b.lnnotes[i], b.stops)
                    if notes is None:
                        continue
                    target_notes = [x for x in notes if current_beat <= x.timing and x.timing < change_bpm.timing]

                    for n in target_notes:
                        ms = current_ms + ms_per_beat(current_bpm) * b.beat * (n.timing - current_beat) * 4
                        self.key_ms[i].append(ms)

                current_ms += ms_per_beat(current_bpm) * b.beat * (change_bpm.timing - current_beat) * 4
                current_beat = change_bpm.timing
                current_bpm = change_bpm.bpm

    def get_lane_timeline(self, index: int):
        return self.key_ms[index]


class CalcDensity(CalcBase):
    def __init__(self, bms: BMS):
        self.timeline = InputTimeline(bms)

    def calc(self):
        total_notes = 0
        key_input_intervals = ( list(), list(), list(), list(), list(), list(), list(), list() )

        def process_for_scratch():
            key_input_timings = self.timeline.get_lane_timeline(0)
            start_up = 0
            start_down = 0
            for i, input in enumerate(key_input_timings):
                if (i % 2) == 0:
                    if start_up != 0:
                        assert input != start_up, 'input == start_up, ({}, {})'.format(float(input), float(start_up))
                        key_input_intervals[0].append(input - start_up)
                    else:
                        key_input_intervals[0].append(None)
                    start_up = input
                else:
                    if start_down != 0:
                        assert input != start_down, 'input == start_down, ({} {})'.format(float(input), float(start_down))
                        key_input_intervals[0].append(input - start_down)
                    else:
                        key_input_intervals[0].append(None)
                    start_down = input

        def process():
            nonlocal total_notes
            for i in range(1, 8):
                key_input_timings = self.timeline.get_lane_timeline(i)
                total_notes += len(key_input_timings)
                start = 0
                for input in key_input_timings:
                    if start != 0:
                        assert input != start, 'input == start, ({}, {})'.format(float(input), float(start))
                        key_input_intervals[i].append(input - start)
                    else:
                        key_input_intervals[i].append(None)
                    start = input

        process_for_scratch()
        process()

        key_influence = float(0)
        for inputs in key_input_intervals:
            for i in inputs:
                if i is None:
                    key_influence += 1
                else:
                    key_influence += (float(200) / i) ** 2
        key_influence /= sqrt(total_notes)
        return key_influence

class BMSLevelCalculator():
    def __init__(self, file: str):
        self.bms = BMS(file)
        self.calc_density = CalcDensity(self.bms)

    def calc(self):
        return self.calc_density.calc()
