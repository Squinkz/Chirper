import math

class Util:

    @staticmethod
    def NoteLengthToSeconds(noteLength, bpm):
        return (240.0 / bpm) * noteLength

    @staticmethod
    def SecondsToNoteLength(seconds, bpm):
        return (seconds * bpm) / 240.0

    @staticmethod
    def SecondsToSamples(secs, samplerate = 44100):
        return int(round(secs * samplerate))

    @staticmethod
    def SamplesToSeconds(samples, samplerate = 44100):
        return samples / samplerate

    @staticmethod
    def FreqToOctave(freq):
        c0 = 440.0 * (2.0 ** (-57.0 / 12.0))
        return math.floor(math.log2(freq / c0))

    @staticmethod
    def GainToVol(gain):
        return math.sqrt(gain)

    @staticmethod
    def VolToGain(volume):
        return volume ** 2.0

    @staticmethod
    def GainToDb(gain):
        if gain == 0.0:
            return -math.inf
        return 20.0 * math.log10(abs(gain))

    @staticmethod
    def DbToGain(db):
        return 10.0 ** (db / 20.0)

    @staticmethod
    def FreqAddCents(freq, cents):
        return freq * (2.0 ** (cents / 1200.0))

    @staticmethod
    def FreqToCents(freq, refFreq):
        return 1200.0 * math.log2(freq / refFreq)

    @staticmethod
    def CentsToRatio(cents):
        return 2.0 ** (cents / 1200.0)

    @staticmethod
    def RatioToCents(ratio):
        return 1200.0 * math.log2(ratio)

    @staticmethod
    def MidiToFreq(note, concertA = 440.0):
        return concertA * (2.0 ** ((note - 69.0) / 12.0))

    @staticmethod
    def FreqToMidi(freq, concertA = 440.0):
        return 69.0 + (12.0 * math.log2(freq / concertA))

    @staticmethod
    def BpmToHz(bpm):
        return bpm / 60.0

    @staticmethod
    def HzToBpm(hz):
        return hz * 60.0

def FreqToStepCount(freq):
    c4 = 440.0 * (2.0 ** (-9.0 / 12.0))
    value = 16.0 * (c4 / freq)

    return max(4.0, min(32.0, value))
