from fractions import Fraction

def ms_per_beat(bpm: int):
    return Fraction(60000 / bpm)

def beat_per_ms(bpm: int):
    return Fraction(bpm / 60000)