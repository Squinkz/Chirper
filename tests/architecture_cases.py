import hashlib
import json

import numpy as np

from Chirper.core.ChirpConstants import N
from Chirper.core.ChirpTone import (
    Insert,
    Seconds,
    Tone,
    TremoloDepth,
    TremoloWave,
    VibratoDepth,
    VibratoWave,
    Wave,
)
from Chirper.core.ChirpSound import Sound


def GetSoundHash(sound):
    samples = np.asarray(sound._samples, dtype = "<f8")
    return hashlib.sha256(samples.tobytes()).hexdigest()


def GetArchitectureHashes():
    cases = {}

    for wave in (
            "Sine",
            "Pulse50",
            "Pulse25",
            "Pulse12",
            "Triangle",
            "Saw",
            "Noise",
            "NoiseLP",
            "NoiseHP",
            "NoiseBP",
            "NoiseStep",
            "NoiseQuanta",
            ):
        sound = Sound([
            Seconds(),
            Tone(N.A4, 0.017, 0.63).Wave(wave),
        ], channels = 1)
        cases["wave_" + wave] = GetSoundHash(sound)

    sequence = [
        Seconds(),
        Wave("Saw"),
        VibratoDepth(31.0),
        VibratoWave("Triangle"),
        TremoloDepth(0.4),
        TremoloWave("Pulse25"),
        Tone(N.C4, 0.021, 0.7)
            .Vibrato(rate = 5.0)
            .Tremolo(rate = 7.0)
            .Mod(83.0, 1.2, "Saw"),
        Tone(N.E4, 0.019, 0.5)
            .Vibrato(rate = 5.0)
            .Tremolo(rate = 7.0)
            .Mod(83.0, 1.2, "Saw")
            .Bend(N.G4, "inoutsine")
            .Fade(0.2, "outsine")
            .Pan(-0.3),
        Tone.Rest(0.003),
        Tone(N.G4, 0.013, 0.4).Phase(90.0).Pan(0.6),
    ]
    cases["control_sequence_stereo"] = GetSoundHash(
        Sound(sequence, channels = 2, layered = False)
    )

    inserted = Sound([
        Seconds(),
        Tone(N.C5, 0.009, 0.35),
    ], channels = 1)
    insertSequence = [
        Seconds(),
        Tone(N.C4, 0.008, 0.4),
        Insert(inserted),
        Tone(N.D4, 0.007, 0.3),
    ]
    cases["insert_sequence_mono"] = GetSoundHash(
        Sound(insertSequence, channels = 1, layered = False)
    )

    baseStereo = Sound([
        Seconds(),
        Tone(N.C4, 0.031, 0.55).Wave("Saw").Pan(-0.35),
        Tone(N.E4, 0.027, 0.45).Wave("Triangle").Pan(0.4),
    ], channels = 2, layered = False)
    baseMono = Sound([
        Seconds(),
        Tone(N.A3, 0.047, 0.6).Wave("Pulse25"),
    ], channels = 1)

    cases["base_stereo"] = GetSoundHash(baseStereo)
    cases["base_mono"] = GetSoundHash(baseMono)
    cases["unison"] = GetSoundHash(Sound([
        Seconds(),
        Tone(N.A3, 0.031, 0.65).Wave("SawAA").Unison(5, 14.0, 0.75),
    ], channels = 2))
    cases["mix"] = GetSoundHash(
        Sound.Mix(
            [baseStereo, baseStereo.Gain(0.5)],
            mixGain = 0.6
        ).Normalize(0.1)
    )
    cases["cut"] = GetSoundHash(baseStereo.Cut(0.041, fade = 0.002))
    cases["fade_in"] = GetSoundHash(baseStereo.FadeIn(0.012, "insine"))
    cases["fade_out"] = GetSoundHash(baseStereo.FadeOut(0.012, "outsine"))
    cases["reverse"] = GetSoundHash(baseStereo.Reverse())
    cases["gain"] = GetSoundHash(baseStereo.Gain(0.73))
    cases["normalize"] = GetSoundHash(baseStereo.Normalize(0.08))
    cases["soft_clip"] = GetSoundHash(baseStereo.SoftClip(2.4, 0.65))
    cases["ring"] = GetSoundHash(baseStereo.Ring(317.0, 0.7))
    cases["chorus"] = GetSoundHash(baseStereo.Chorus(
        rate = 0.73,
        depth = 0.0025,
        delay = 0.013,
        voices = 3,
        feedback = 0.18,
        spread = 0.8,
        mix = 0.6,
        wave = "TriangleAA"
    ))
    cases["phaser"] = GetSoundHash(baseStereo.Phaser(
        rate = 0.41,
        minFreq = 180.0,
        maxFreq = 2400.0,
        stages = 8,
        feedback = 0.3,
        spread = 0.7,
        mix = 0.55,
        wave = "Sine"
    ))
    cases["pan_stereo"] = GetSoundHash(baseStereo.Pan(-0.42))
    cases["pan_mono"] = GetSoundHash(baseMono.Pan(0.75))
    cases["low_pass"] = GetSoundHash(baseStereo.LowPass(1300.0, 0.6))
    cases["high_pass"] = GetSoundHash(baseStereo.HighPass(180.0, 0.8))
    cases["band_pass"] = GetSoundHash(baseStereo.BandPass(900.0, 0.7))
    cases["notch"] = GetSoundHash(baseStereo.Notch(700.0, 1.1))
    cases["peak"] = GetSoundHash(baseStereo.Peak(850.0, 3.5, 0.9))
    cases["low_shelf"] = GetSoundHash(baseStereo.LowShelf(420.0, -2.5, 0.7))
    cases["high_shelf"] = GetSoundHash(baseStereo.HighShelf(2400.0, 2.0, 0.8))
    cases["low_pass_sweep"] = GetSoundHash(
        baseStereo.LowPassSweep(300.0, 2600.0, 0.7, "inoutsine")
    )
    cases["high_pass_sweep"] = GetSoundHash(
        baseStereo.HighPassSweep(100.0, 1600.0, 0.7, "outsine")
    )
    cases["band_pass_sweep"] = GetSoundHash(
        baseStereo.BandPassSweep(350.0, 1800.0, 0.7, "linear")
    )
    cases["notch_sweep"] = GetSoundHash(
        baseStereo.NotchSweep(250.0, 1500.0, 0.8, "insine")
    )
    cases["peak_sweep"] = GetSoundHash(
        baseStereo.PeakSweep(300.0, 2000.0, 2.5, 0.9, "outsine")
    )
    cases["low_shelf_sweep"] = GetSoundHash(
        baseStereo.LowShelfSweep(180.0, 900.0, -2.0, 0.7, "linear")
    )
    cases["high_shelf_sweep"] = GetSoundHash(
        baseStereo.HighShelfSweep(1000.0, 4200.0, 2.0, 0.7, "inoutsine")
    )
    cases["schroverb"] = GetSoundHash(baseStereo.Schroverb(
        wet = 0.25,
        decay = 0.55,
        roomSize = 0.8,
        tail = 0.015
    ))
    cases["freeverb"] = GetSoundHash(baseStereo.Freeverb(
        wet = 0.2,
        decay = 0.65,
        damping = 0.4,
        width = 0.7,
        tail = 0.015
    ))
    cases["mtverb"] = GetSoundHash(baseStereo.MTVerb(
        wet = 0.2,
        decay = 0.6,
        mode = "room",
        tail = 0.015
    ))
    cases["delay"] = GetSoundHash(baseStereo.Delay(
        delay = 0.007,
        decay = 0.35,
        count = 2,
        extend = True
    ))
    cases["ping_pong"] = GetSoundHash(baseStereo.PingPong(
        delay = 0.009,
        decay = 0.4,
        count = 2,
        width = 0.8,
        extend = True
    ))

    return cases


if __name__ == "__main__":
    print(json.dumps(GetArchitectureHashes(), sort_keys = True, indent = 2))
