import math


class ReadOnly(type):
    def __setattr__(cls, name, value):
        raise AttributeError(cls.__name__ + " cannot be modified")

    def __delattr__(cls, name):
        raise AttributeError(cls.__name__ + " cannot be modified")

class ReadOnlyObject(metaclass = ReadOnly):
    def _Freeze(self):
        object.__setattr__(self, "_frozen", True)
        return self

    def __setattr__(self, name, value):
        if getattr(self, "_frozen", False):
            raise AttributeError(type(self).__name__ + " cannot be modified")
        object.__setattr__(self, name, value)

    def __delattr__(self, name):
        if getattr(self, "_frozen", False):
            raise AttributeError(type(self).__name__ + " cannot be modified")
        object.__delattr__(self, name)


# -----------------------------------
# Constants
# -----------------------------------

# Just intonation ratios
class JustRatio(metaclass = ReadOnly):
    UNISON          =  1.0
    UNI             =  UNISON
    MIN2            = 16.0 / 15.0
    MAJ2            =  9.0 /  8.0
    MIN3            =  6.0 /  5.0
    MAJ3            =  5.0 /  4.0
    FOURTH          =  4.0 /  3.0
    AUG4            = 45.0 / 32.0
    DIM5            = 64.0 / 45.0
    FIFTH           =  3.0 /  2.0
    MIN6            =  8.0 /  5.0
    MAJ6            =  5.0 /  3.0
    MIN7            =  9.0 /  5.0
    MAJ7            = 15.0 /  8.0
    OCTAVE          =  2.0
    OCT             =  OCTAVE

# Equal temperament ratios
class EqualRatio(metaclass = ReadOnly):
    UNISON          = 2.0 ** (0.0 / 12.0)
    UNI             = UNISON

    MIN2            = 2.0 ** (1.00 / 12.0)
    MAJ2            = 2.0 ** (2.00 / 12.0)
    MIN3            = 2.0 ** (3.00 / 12.0)
    MAJ3            = 2.0 ** (4.00 / 12.0)
    FOURTH          = 2.0 ** (5.00 / 12.0)
    AUG4            = 2.0 ** (6.00 / 12.0)
    DIM5            = AUG4
    FIFTH           = 2.0 ** (7.00 / 12.0)
    MIN6            = 2.0 ** (8.00 / 12.0)
    MAJ6            = 2.0 ** (9.00 / 12.0)
    MIN7            = 2.0 ** (10.0 / 12.0)
    MAJ7            = 2.0 ** (11.0 / 12.0)

    OCTAVE          = 2.0 ** (12.0 / 12.0)
    OCT             = OCTAVE

class Scale(ReadOnlyObject):
    def __init__(self, ratio):

        R = ratio

        # Scales
        self.CHROMATIC   = (R.UNI, R.MIN2, R.MAJ2, R.MIN3, R.MAJ3, R.FOURTH,
                            R.AUG4, R.FIFTH, R.MIN6, R.MAJ6, R.MIN7, R.MAJ7)
        self.WHOLE_TONE  = (R.UNI, R.MAJ2, R.MAJ3, R.AUG4, R.MIN6, R.MIN7)

        self.MAJOR       = (R.UNI, R.MAJ2, R.MAJ3, R.FOURTH, R.FIFTH, R.MAJ6, R.MAJ7)
        self.MINOR       = (R.UNI, R.MAJ2, R.MIN3, R.FOURTH, R.FIFTH, R.MIN6, R.MIN7)

        self.HALF_WHOLE  = (R.UNI, R.MIN2, R.MIN3, R.MAJ3, R.AUG4, R.FIFTH, R.MAJ6, R.MIN7)
        self.WHOLE_HALF  = (R.UNI, R.MAJ2, R.MIN3, R.FOURTH, R.DIM5, R.MIN6, R.MAJ6, R.MAJ7)
        self.DIMINISHED  = self.WHOLE_HALF
        self.DOM_DIM     = self.HALF_WHOLE

        self.HARM_MAJ    = (R.UNI, R.MAJ2, R.MAJ3, R.FOURTH, R.FIFTH, R.MIN6, R.MAJ7)
        self.MELO_MIN    = (R.UNI, R.MAJ2, R.MIN3, R.FOURTH, R.FIFTH, R.MAJ6, R.MAJ7)
        self.HARM_MIN    = (R.UNI, R.MAJ2, R.MIN3, R.FOURTH, R.FIFTH, R.MIN6, R.MAJ7)

        self.PENTA_MIN   = (R.UNI, R.MIN3, R.FOURTH, R.FIFTH, R.MIN7)
        self.PENTA       = self.PENTA_MIN
        self.PENTA_MAJ   = (R.UNI, R.MAJ2, R.MAJ3, R.FIFTH, R.MAJ6)
        self.PENTA_NEUT  = (R.UNI, R.MAJ2, R.FOURTH, R.FIFTH, R.MIN7)

        self.PENTA_BLUES = (R.UNI, R.MIN3, R.FOURTH, R.DIM5, R.FIFTH, R.MIN7)
        self.BLUES       = self.PENTA_BLUES

        # Modes
        self.IONIAN      = self.MAJOR
        self.DORIAN      = (R.UNI, R.MAJ2, R.MIN3, R.FOURTH, R.FIFTH, R.MAJ6, R.MIN7)
        self.PHRYGIAN    = (R.UNI, R.MIN2, R.MIN3, R.FOURTH, R.FIFTH, R.MIN6, R.MIN7)
        self.LYDIAN      = (R.UNI, R.MAJ2, R.MAJ3, R.AUG4, R.FIFTH, R.MAJ6, R.MAJ7)
        self.MIXOLYDIAN  = (R.UNI, R.MAJ2, R.MAJ3, R.FOURTH, R.FIFTH, R.MAJ6, R.MIN7)
        self.AEOLIAN     = self.MINOR
        self.LOCRIAN     = (R.UNI, R.MIN2, R.MIN3, R.FOURTH, R.DIM5, R.MIN6, R.MIN7)
        self.LYDIAN_DOM  = (R.UNI, R.MAJ2, R.MAJ3, R.AUG4, R.FIFTH, R.MAJ6, R.MIN7)
        # Bright to Dark:
        # Lydian, Ionian, Mixolydian, Dorian, Aeolian, Phrygian, Locrian

        # Chords
        self.MAJ         = (R.UNI, R.MAJ3,   R.FIFTH)
        self.MIN         = (R.UNI, R.MIN3,   R.FIFTH)
        self.SUS2        = (R.UNI, R.MAJ2,   R.FIFTH)
        self.SUS4        = (R.UNI, R.FOURTH, R.FIFTH)
        self.DIM         = (R.UNI, R.MIN3,   R.DIM5)
        self.AUG         = (R.UNI, R.MAJ3,   R.MIN6)
        self.FOURTH      = (R.UNI, R.FOURTH)
        self.FIFTH       = (R.UNI, R.FIFTH)
        self.POWER       = (R.UNI, R.FIFTH, R.OCT)
        self.MIN6        = (R.UNI, R.MIN3, R.FIFTH, R.MAJ6)
        self.MAJ6        = (R.UNI, R.MAJ3, R.FIFTH, R.MAJ6)
        self.SIXTH       = self.MAJ6
        self.MAJ7        = (R.UNI, R.MAJ3, R.FIFTH, R.MAJ7)
        self.MIN7        = (R.UNI, R.MIN3, R.FIFTH, R.MIN7)
        self.DOM7        = (R.UNI, R.MAJ3, R.FIFTH, R.MIN7)
        self.SEVENTH     = self.DOM7
        self.DIM7        = (R.UNI, R.MIN3, R.DIM5,  R.MAJ6)
        self.HALFDIM7    = (R.UNI, R.MIN3, R.DIM5,  R.MIN7)
        self.MINMAJ7     = (R.UNI, R.MIN3, R.FIFTH, R.MAJ7)
        self.MAJMIN7     = self.DOM7
        self.MIN7B5      = self.HALFDIM7
        self.AUG7        = (R.UNI, R.MAJ3, R.MIN6, R.MIN7)
        self.AUGMAJ7     = (R.UNI, R.MAJ3, R.MIN6, R.MAJ7)
        self.ADD9        = (R.UNI, R.MAJ3, R.FIFTH, R.MAJ2 * R.OCT)
        self.MAJADD9     = self.ADD9
        self.MINADD9     = (R.UNI, R.MIN3, R.FIFTH, R.MAJ2 * R.OCT)
        self.MINMAJ9     = (R.UNI, R.MIN3, R.FIFTH, R.MAJ7, R.MAJ2 * R.OCT)
        self.MAJ9        = (R.UNI, R.MAJ3, R.FIFTH, R.MAJ7, R.MAJ2 * R.OCT)
        self.MIN9        = (R.UNI, R.MIN3, R.FIFTH, R.MIN7, R.MAJ2 * R.OCT)
        self.DOM9        = (R.UNI, R.MAJ3, R.FIFTH, R.MIN7, R.MAJ2 * R.OCT)
        self.MAJMIN9     = self.DOM9
        self.SUS7        = (R.UNI, R.FOURTH, R.FIFTH, R.MIN7)
        self.SUS9        = (R.UNI, R.FOURTH, R.FIFTH, R.MIN7, R.MAJ2 * R.OCT)

        self._Freeze()

JustScale = Scale(JustRatio)
EqualScale = Scale(EqualRatio)

class NoteFrequency(ReadOnlyObject):

    MIN         = 20.0
    MAX         = 20000.0

    def __init__(self, concertA = 440.0, ratio = EqualRatio):

        R = ratio

        self.A4          = concertA

        self.AS4         = self.A4 * R.MIN2
        self.BB4         = self.AS4
        self.B4          = self.A4 * R.MAJ2

        self.C5          = self.A4 * R.MIN3
        self.CS5         = self.A4 * R.MAJ3
        self.DB5         = self.CS5
        self.D5          = self.A4 * R.FOURTH
        self.DS5         = self.A4 * R.AUG4
        self.EB5         = self.DS5
        self.E5          = self.A4 * R.FIFTH
        self.F5          = self.A4 * R.MIN6
        self.FS5         = self.A4 * R.MAJ6
        self.GB5         = self.FS5
        self.G5          = self.A4 * R.MIN7
        self.GS5         = self.A4 * R.MAJ7
        self.AB5         = self.GS5
        self.A5          = self.A4 * R.OCT
        self.AS5         = self.AS4 * R.OCT
        self.BB5         = self.AS5
        self.B5          = self.B4 * R.OCT

        self.C6          = self.C5 * R.OCT
        self.CS6         = self.CS5 * R.OCT
        self.DB6         = self.CS6
        self.D6          = self.D5 * R.OCT
        self.DS6         = self.DS5 * R.OCT
        self.EB6         = self.DS6
        self.E6          = self.E5 * R.OCT
        self.F6          = self.F5 * R.OCT
        self.FS6         = self.FS5 * R.OCT
        self.GB6         = self.FS6
        self.G6          = self.G5 * R.OCT
        self.GS6         = self.GS5 * R.OCT
        self.AB6         = self.GS6
        self.A6          = self.A5 * R.OCT
        self.AS6         = self.AS5 * R.OCT
        self.BB6         = self.AS6
        self.B6          = self.B5 * R.OCT

        self.C7          = self.C6 * R.OCT
        self.CS7         = self.CS6 * R.OCT
        self.DB7         = self.CS7
        self.D7          = self.D6 * R.OCT
        self.DS7         = self.DS6 * R.OCT
        self.EB7         = self.DS7
        self.E7          = self.E6 * R.OCT
        self.F7          = self.F6 * R.OCT
        self.FS7         = self.FS6 * R.OCT
        self.GB7         = self.FS7
        self.G7          = self.G6 * R.OCT
        self.GS7         = self.GS6 * R.OCT
        self.AB7         = self.GS7
        self.A7          = self.A6 * R.OCT
        self.AS7         = self.AS6 * R.OCT
        self.BB7         = self.AS7
        self.B7          = self.B6 * R.OCT

        self.C8          = self.C7 * R.OCT
        self.CS8         = self.CS7 * R.OCT
        self.DB8         = self.CS8
        self.D8          = self.D7 * R.OCT
        self.DS8         = self.DS7 * R.OCT
        self.EB8         = self.DS8
        self.E8          = self.E7 * R.OCT
        self.F8          = self.F7 * R.OCT
        self.FS8         = self.FS7 * R.OCT
        self.GB8         = self.FS8
        self.G8          = self.G7 * R.OCT
        self.GS8         = self.GS7 * R.OCT
        self.AB8         = self.GS8
        self.A8          = self.A7 * R.OCT
        self.AS8         = self.AS7 * R.OCT
        self.BB8         = self.AS8
        self.B8          = self.B7 * R.OCT

        self.C9          = self.C8 * R.OCT
        self.CS9         = self.CS8 * R.OCT
        self.DB9         = self.CS9
        self.D9          = self.D8 * R.OCT
        self.DS9         = self.DS8 * R.OCT
        self.EB9         = self.DS9
        self.E9          = self.E8 * R.OCT
        self.F9          = self.F8 * R.OCT
        self.FS9         = self.FS8 * R.OCT
        self.GB9         = self.FS9
        self.G9          = self.G8 * R.OCT
        self.GS9         = self.GS8 * R.OCT
        self.AB9         = self.GS9
        self.A9          = self.A8 * R.OCT
        self.AS9         = self.AS8 * R.OCT
        self.BB9         = self.AS9
        self.B9          = self.B8 * R.OCT

        self.GS4         = self.A4 / R.MIN2
        self.AB4         = self.GS4
        self.G4          = self.A4 / R.MAJ2
        self.FS4         = self.A4 / R.MIN3
        self.GB4         = self.FS4
        self.F4          = self.A4 / R.MAJ3
        self.E4          = self.A4 / R.FOURTH
        self.DS4         = self.A4 / R.AUG4
        self.EB4         = self.DS4
        self.D4          = self.A4 / R.FIFTH
        self.CS4         = self.A4 / R.MIN6
        self.DB4         = self.CS4
        self.C4          = self.A4 / R.MAJ6

        self.B3          = self.A4 / R.MIN7
        self.AS3         = self.A4 / R.MAJ7
        self.BB3         = self.AS3
        self.A3          = self.A4 / R.OCT
        self.GS3         = self.GS4 / R.OCT
        self.AB3         = self.GS3
        self.G3          = self.G4 / R.OCT
        self.FS3         = self.FS4 / R.OCT
        self.GB3         = self.FS3
        self.F3          = self.F4 / R.OCT
        self.E3          = self.E4 / R.OCT
        self.DS3         = self.DS4 / R.OCT
        self.EB3         = self.DS3
        self.D3          = self.D4 / R.OCT
        self.CS3         = self.CS4 / R.OCT
        self.DB3         = self.CS3
        self.C3          = self.C4 / R.OCT

        self.B2          = self.B3 / R.OCT
        self.AS2         = self.AS3 / R.OCT
        self.BB2         = self.AS2
        self.A2          = self.A3 / R.OCT
        self.GS2         = self.GS3 / R.OCT
        self.AB2         = self.GS2
        self.G2          = self.G3 / R.OCT
        self.FS2         = self.FS3 / R.OCT
        self.GB2         = self.FS2
        self.F2          = self.F3 / R.OCT
        self.E2          = self.E3 / R.OCT
        self.DS2         = self.DS3 / R.OCT
        self.EB2         = self.DS2
        self.D2          = self.D3 / R.OCT
        self.CS2         = self.CS3 / R.OCT
        self.DB2         = self.CS2
        self.C2          = self.C3 / R.OCT

        self.B1          = self.B2 / R.OCT
        self.AS1         = self.AS2 / R.OCT
        self.BB1         = self.AS1
        self.A1          = self.A2 / R.OCT
        self.GS1         = self.GS2 / R.OCT
        self.AB1         = self.GS1
        self.G1          = self.G2 / R.OCT
        self.FS1         = self.FS2 / R.OCT
        self.GB1         = self.FS1
        self.F1          = self.F2 / R.OCT
        self.E1          = self.E2 / R.OCT
        self.DS1         = self.DS2 / R.OCT
        self.EB1         = self.DS1
        self.D1          = self.D2 / R.OCT
        self.CS1         = self.CS2 / R.OCT
        self.DB1         = self.CS1
        self.C1          = self.C2 / R.OCT

        self._Freeze()

EqualNote = NoteFrequency(440.0, EqualRatio)

print(EqualNote.C8)

class NoteLength(metaclass = ReadOnly):

    # ----------------------------
    # Easy names:
    # ----------------------------

    # Regular notes
    L8X = 8.0
    L4X = 4.0
    L2X = 2.0
    L1  = 1.0
    L2  = 1.0 / 2.0
    L4  = 1.0 / 4.0
    L8  = 1.0 / 8.0
    L16 = 1.0 / 16.0
    L32 = 1.0 / 32.0
    L64 = 1.0 / 64.0

    # Dotted notes
    L1D  = L1  + L2
    L2D  = L2  + L4
    L4D  = L4  + L8
    L8D  = L8  + L16
    L16D = L16 + L32
    L32D = L32 + L64
    L64D = L64 + (L64 * 0.5)

    # Triplets
    L1T  = L1  * (2.0 / 3.0)
    L2T  = L2  * (2.0 / 3.0)
    L4T  = L4  * (2.0 / 3.0)
    L8T  = L8  * (2.0 / 3.0)
    L16T = L16 * (2.0 / 3.0)
    L32T = L32 * (2.0 / 3.0)
    L64T = L64 * (2.0 / 3.0)

    # ----------------------------
    # Descriptive names
    # ----------------------------

    # Regular notes
    LARGE         = L8X
    LONG          = L4X
    DOUBLE        = L2X
    WHOLE         = L1
    HALF          = L2
    QUARTER       = L4
    EIGHT         = L8
    SIXTEEN       = L16
    THIRTYTWO     = L32
    SIXTYFOUR     = L64

    # Dotted notes
    WHOLEDOT      = L1D
    HALFDOT       = L2D
    QUARTERDOT    = L4D
    EIGHTDOT      = L8D
    SIXTEENDOT    = L16D
    THIRTYTWODOT  = L32D
    SIXTYFOURDOT  = L64D

    # Triplets
    WHOLETRIP     = L1T
    HALFTRIP      = L2T
    QUARTERTRIP   = L4T
    EIGHTTRIP     = L8T
    SIXTEENTRIP   = L16T
    THIRTYTWOTRIP = L32T
    SIXTYFOURTRIP = L64T

    # ----------------------------
    # Traditional names
    # ----------------------------

    # Regular notes
    MAXIMA                 = L8X
    LONGA                  = L4X
    BREVE                  = L2X
    SEMIBREVE              = L1
    MINIM                  = L2
    CROTCHET               = L4
    QUAVER                 = L8
    SEMIQUAVER             = L16
    DEMISEMIQUAVER         = L32
    HEMIDEMISEMIQUAVER     = L64

    # Dotted notes
    SEMIBREVEDOT           = L1D
    MINIMDOT               = L2D
    CROTCHETDOT            = L4D
    QUAVERDOT              = L8D
    SEMIQUAVERDOT          = L16D
    DEMISEMIQUAVERDOT      = L32D
    HEMIDEMISEMIQUAVERDOT  = L64D

    # Triplets
    SEMIBREVETRIP          = L1T
    MINIMTRIP              = L2T
    CROTCHETTRIP           = L4T
    QUAVERTRIP             = L8T
    SEMIQUAVERTRIP         = L16T
    DEMISEMIQUAVERTRIP     = L32T
    HEMIDEMISEMIQUAVERTRIP = L64T

class Vibrato(metaclass = ReadOnly):
    NONE    = 0.0
    XLIGHT  = 12.5
    LIGHT   = 25.0
    MEDIUM  = 50.0
    HEAVY   = 75.0
    XHEAVY  = 100.0

class Tremolo(metaclass = ReadOnly):
    NONE    = 0.0
    XLIGHT  = 0.125
    LIGHT   = 0.25
    MEDIUM  = 0.5
    HEAVY   = 0.75
    XHEAVY  = 1.0

class Dynamics(metaclass = ReadOnly):
    D00 = 0.0

    D01 = 1.0 / 128.0
    D03 = 1.0 / 64.0
    D05 = 1.0 / 32.0
    D07 = 1.0 / 16.0
    D09 = 1.0 / 8.0
    D11 = 1.0 / 4.0
    D13 = 1.0 / 2.0
    D15 = 1.0

    D02 = math.sqrt(D01 * D03)
    D04 = math.sqrt(D03 * D05)
    D06 = math.sqrt(D05 * D07)
    D08 = math.sqrt(D07 * D09)
    D10 = math.sqrt(D09 * D11)
    D12 = math.sqrt(D11 * D13)
    D14 = math.sqrt(D13 * D15)

class QFactor(metaclass = ReadOnly):
    BROAD   = 0.25
    WIDE    = 0.5
    MID     = 0.707
    NARROW  = 1.0
    TIGHT   = 2.0

# -----------------------------------
# Aliases for easy typing
# -----------------------------------

N = EqualNote
L = NoteLength
V = Vibrato
T = Tremolo
D = Dynamics
JR = JustRatio
ER = EqualRatio
JS = JustScale
ES = EqualScale
Q = QFactor

__all__ = [
    "JustRatio",
    "EqualRatio",
    "JustScale",
    "EqualScale",
    "NoteFrequency",
    "EqualNote",
    "NoteLength",
    "Vibrato",
    "Tremolo",
    "Dynamics",
    "QFactor",
    "N",
    "L",
    "V",
    "T",
    "D",
    "JR",
    "ER",
    "JS",
    "ES",
    "Q",
]
