import random
import math

from ..core.ChirpConstants import Q, ReadOnly, N, T
from ..core.ChirpUtil import Util
from ..core.ChirpSound import Sound
from ..core.ChirpTone import Insert, Tone
from .ChirpPatch import Envelope, Patch


# -----------------------------------
# Basic
# -----------------------------------

basicEnv = Envelope(0.003, 0.0, 1.0, 0.003)

def _SinePatch(freq, dur, amp):
    return [Tone(freq, dur, amp).Wave("Sine")]

def _TrianglePatch(freq, dur, amp):
    return [Tone(freq, dur, amp).Wave("TriangleAA")]

def _SquarePatch(freq, dur, amp):
    return [Tone(freq, dur, amp).Wave("Pulse50AA")]

def _SawPatch(freq, dur, amp):
    return [Tone(freq, dur, amp).Wave("SawAA")]

# -----------------------------------
# Flavor
# -----------------------------------

def _PluckyTransient(freq, dur, amp):
    return [
        Tone(freq, 0.2, amp).Wave("Sine").Bend(freq * 2.0, "inoutback").Fade(0.0, "outexpo"),
        Tone(freq, 0.2, amp).Wave("Sine").Bend(freq * 0.5, "inoutback").Fade(0.0, "outexpo"),
    ]

def _SuperSinePatch(freq, dur, amp):
    return [
        Tone(freq, dur, amp).Wave("Sine").Unison(),
        Tone(freq * 0.5, dur, amp).Wave("Sine").Unison(),
    ]

def _SuperTrianglePatch(freq, dur, amp):
    return [
        Tone(freq, dur, amp).Wave("TriangleAA").Unison(),
        Tone(freq * 0.5, dur, amp).Wave("TriangleAA").Unison(),
    ]

def _SuperSquarePatch(freq, dur, amp):
    return [
        Tone(freq, dur, amp).Wave("Pulse50AA").Unison(),
        Tone(freq * 0.5, dur, amp).Wave("TriangleAA").Unison(),
    ]

def _SuperSawPatch(freq, dur, amp):
    return [
        Tone(freq, dur, amp).Wave("SawAA").Unison(),
        Tone(freq * 0.5, dur, amp).Wave("TriangleAA").Unison(),
    ]

def _BellBody(freq, dur, amp):
    def RFreq():
        return (random.random() * 0.2) - 0.1

    body = Sound.Mix([
        Sound([
            Tone(freq * 0.51, (dur * 1.25) * 0.05, 0.0000).Fade(0.0225, "inSine"),
            Tone(freq * 0.51, (dur * 1.25) * 0.95, 0.0225).Fade(0.0000, "outSine"),
        ], channels = 1, layered = False),
        Sound([
            Tone(freq * 02.02 + RFreq(), dur,        1.0000).Fade(0.0, "outSine").Tremolo(),
            Tone(freq * 02.95 + RFreq(), dur * 0.50, 0.2500).Fade(0.0, "outSine").Tremolo(),
            Tone(freq * 04.23 + RFreq(), dur * 0.25, 0.1089).Fade(0.0, "outSine").Tremolo(),
            Tone(freq * 05.47 + RFreq(), dur * 0.33, 0.0625).Fade(0.0, "outSine").Tremolo(),
            Tone(freq * 06.82 + RFreq(), dur * 0.20, 0.0400).Fade(0.0, "outSine").Tremolo(),
            Tone(freq * 07.59 + RFreq(), dur * 0.16, 0.0256).Fade(0.0, "outSine").Tremolo(),
            Tone(freq * 08.25 + RFreq(), dur * 0.12, 0.0064).Fade(0.0, "outSine").Tremolo(),
            Tone(freq * 09.13 + RFreq(), dur * 0.11, 0.0049).Fade(0.0, "outSine").Tremolo(),
            Tone(freq * 09.58 + RFreq(), dur * 0.13, 0.0036).Fade(0.0, "outSine").Tremolo(),
            Tone(freq * 10.75 + RFreq(), dur * 0.12, 0.0049).Fade(0.0, "outSine").Tremolo(),
            Tone(freq * 12.20 + RFreq(), dur * 0.15, 0.0064).Fade(0.0, "outSine").Tremolo(),
        ], channels = 1),
    ], channels = 1).Normalize().Schroverb()

    return [Insert(body.Gain(amp))]

def _BellTransient(freq, dur, amp):
    transient = (
        Sound([
            Tone(freq, 0.02, 1.00).Wave("Triangle").Fade(0.0, "outSine"),
            Tone(freq * 1.43, 0.01, 0.36).Wave("Triangle").Fade(0.0, "outSine"),
        ], channels = 1).Normalize()
        .SoftClip(1.25)
        .HighPass(2000.0, Q.NARROW)
        .Delay(0.0125, 0.6, 1)
        .Schroverb(0.35, 0.65)
    )
    return [Insert(transient.Gain(amp))]

def _PianoPatch():

    env = Envelope(0.01, 5.0, 0.05, 2.0)

    def FreqToStepCount(freq):
        c4 = 440.0 * (2.0 ** (-9.0 / 12.0))
        value = 16.0 * (c4 / freq)

        return max(4.0, min(32.0, value))

    def Body(freq, dur, amp):
        low = N.C1
        high = N.C8
        position = math.log2(freq / low) / math.log2(high / low)
        position = max(0.0, min(1.0, position))
        pan = position - 0.5

        freq *= 0.5
        body = Sound.Mix([(
            Sound([
                Tone(freq, dur, 1.0).Wave("sawAA").Unison(3, 0.5, 0.1).Tremolo(T.LIGHT, 0.5),
                Tone(Util.FreqAddCents(freq, 2), dur + env.release, 0.125).Wave("sawAA").Tremolo(T.MEDIUM, 0.5).FadeIn(0.25, "inexpo"),#.Bend(freq * 0.991)
            ])
            .LowPassSweep(freq * FreqToStepCount(freq), freq)
            .HighPass(80.0)
            .Schroverb(1.0)
        ),]).Pan(pan)

        return [Insert(body.Normalize().Gain(amp))]

    return Patch(None, Body, 1.0, 1.0, env)

# -----------------------------------
# Built-In Patches
# -----------------------------------

class Patches(metaclass = ReadOnly):
    Sine        = Patch(None, _SinePatch, envelope = basicEnv)._Freeze()
    Triangle    = Patch(None, _TrianglePatch, envelope = basicEnv)._Freeze()
    Square      = Patch(None, _SquarePatch, envelope = basicEnv)._Freeze()
    Saw         = Patch(None, _SawPatch, envelope = basicEnv)._Freeze()

    SuperSine       = Patch(_PluckyTransient, _SuperSinePatch,     1.0, 0.84, basicEnv)._Freeze()
    SuperTriangle   = Patch(_PluckyTransient, _SuperTrianglePatch, 1.0, 0.84, basicEnv)._Freeze()
    SuperSquare     = Patch(_PluckyTransient, _SuperSquarePatch,   1.0, 0.84, basicEnv)._Freeze()
    SuperSaw        = Patch(_PluckyTransient, _SuperSawPatch,      1.0, 0.84, basicEnv)._Freeze()

    Piano           = _PianoPatch()
    CowBell         = Patch(_BellTransient, _BellBody, 1.0, 0.35)._Freeze()


__all__ = [
    "Patches",
]
