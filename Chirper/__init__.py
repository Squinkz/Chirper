from importlib import import_module
from typing import TYPE_CHECKING as _TYPE_CHECKING


if _TYPE_CHECKING:
    from .Chirper import Chirper
    from .composition import Envelope, Meter, Note, Patch, Patches, Sequence, SetPatch
    from .core import (
        ChirpDSP, ChirpOscillator, ChirpRenderPlan, ChirpSynth, Control, D,
        Dynamics, EqualRatio, EqualScale, ER, ES, Insert, JR, JS, JustRatio,
        JustScale, L, N, NoteFrequency, NoteLength, Pitch, Q, QFactor, Seconds,
        Sound, T, Tempo, Tone, Tremolo, TremoloDepth, TremoloRate, TremoloWave,
        Util, V, Vibrato, VibratoDepth, VibratoRate, VibratoWave, Wave,
        WaveTable,
    )
    from .io import ChirpFile
    from .playback import ChirpMixer, ChirpPlayer, ChirpVoiceHandle


_EXPORTS = {
    "Chirper": (".Chirper", "Chirper"),
    "JustRatio": (".core.ChirpConstants", "JustRatio"),
    "EqualRatio": (".core.ChirpConstants", "EqualRatio"),
    "JustScale": (".core.ChirpConstants", "JustScale"),
    "EqualScale": (".core.ChirpConstants", "EqualScale"),
    "NoteFrequency": (".core.ChirpConstants", "NoteFrequency"),
    "NoteLength": (".core.ChirpConstants", "NoteLength"),
    "Vibrato": (".core.ChirpConstants", "Vibrato"),
    "Tremolo": (".core.ChirpConstants", "Tremolo"),
    "Dynamics": (".core.ChirpConstants", "Dynamics"),
    "QFactor": (".core.ChirpConstants", "QFactor"),
    "N": (".core.ChirpConstants", "N"),
    "L": (".core.ChirpConstants", "L"),
    "V": (".core.ChirpConstants", "V"),
    "T": (".core.ChirpConstants", "T"),
    "D": (".core.ChirpConstants", "D"),
    "JR": (".core.ChirpConstants", "JR"),
    "ER": (".core.ChirpConstants", "ER"),
    "JS": (".core.ChirpConstants", "JS"),
    "ES": (".core.ChirpConstants", "ES"),
    "Q": (".core.ChirpConstants", "Q"),
    "Tone": (".core.ChirpTone", "Tone"),
    "Control": (".core.ChirpTone", "Control"),
    "Wave": (".core.ChirpTone", "Wave"),
    "Pitch": (".core.ChirpTone", "Pitch"),
    "Tempo": (".core.ChirpTone", "Tempo"),
    "Seconds": (".core.ChirpTone", "Seconds"),
    "VibratoDepth": (".core.ChirpTone", "VibratoDepth"),
    "VibratoRate": (".core.ChirpTone", "VibratoRate"),
    "VibratoWave": (".core.ChirpTone", "VibratoWave"),
    "TremoloDepth": (".core.ChirpTone", "TremoloDepth"),
    "TremoloRate": (".core.ChirpTone", "TremoloRate"),
    "TremoloWave": (".core.ChirpTone", "TremoloWave"),
    "Insert": (".core.ChirpTone", "Insert"),
    "Sound": (".core.ChirpSound", "Sound"),
    "Util": (".core.ChirpUtil", "Util"),
    "Envelope": (".composition.ChirpPatch", "Envelope"),
    "Patch": (".composition.ChirpPatch", "Patch"),
    "Patches": (".composition.ChirpPatches", "Patches"),
    "Meter": (".composition.ChirpSequence", "Meter"),
    "SetPatch": (".composition.ChirpSequence", "SetPatch"),
    "Note": (".composition.ChirpSequence", "Note"),
    "Sequence": (".composition.ChirpSequence", "Sequence"),
    "ChirpDSP": (".core.ChirpDSP", "ChirpDSP"),
    "ChirpOscillator": (".core.ChirpOscillator", "ChirpOscillator"),
    "WaveTable": (".core.ChirpOscillator", "WaveTable"),
    "ChirpMixer": (".playback.ChirpMixer", "ChirpMixer"),
    "ChirpVoiceHandle": (".playback.ChirpMixer", "ChirpVoiceHandle"),
    "ChirpRenderPlan": (".core.ChirpRender", "ChirpRenderPlan"),
    "ChirpSynth": (".core.ChirpSynth", "ChirpSynth"),
    "ChirpPlayer": (".playback.ChirpPlayer", "ChirpPlayer"),
    "ChirpFile": (".io.ChirpFile", None),
}

__all__ = [
    "Chirper",
    "JustRatio", "EqualRatio", "JustScale", "EqualScale",
    "NoteFrequency", "NoteLength", "Vibrato", "Tremolo", "Dynamics",
    "QFactor", "N", "L", "V", "T", "D", "JR", "ER", "JS", "ES", "Q",
    "Tone", "Control", "Wave", "Pitch", "Tempo", "Seconds",
    "VibratoDepth", "VibratoRate", "VibratoWave",
    "TremoloDepth", "TremoloRate", "TremoloWave", "Insert", "Sound",
    "Util",
    "Envelope", "Patch", "Patches", "Meter", "SetPatch", "Note", "Sequence",
    "ChirpDSP", "ChirpOscillator", "WaveTable", "ChirpMixer",
    "ChirpVoiceHandle", "ChirpRenderPlan", "ChirpSynth", "ChirpPlayer",
    "ChirpFile",
]


def __getattr__(name):
    if name not in _EXPORTS:
        raise AttributeError("module 'Chirper' has no attribute " + repr(name))

    moduleName, attributeName = _EXPORTS[name]
    module = import_module(moduleName, __name__)
    value = module if attributeName is None else getattr(module, attributeName)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(__all__))
