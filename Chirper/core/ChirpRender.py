from dataclasses import dataclass
from typing import Any


@dataclass(slots = True, init = False)
class ChirpRenderPlan:
    synthesizer: Any
    events: tuple
    sampleCount: int

    def __init__(self, synthesizer, events, sampleCount):
        self.synthesizer = synthesizer
        self.events = tuple(events)
        self.sampleCount = sampleCount


@dataclass(slots = True)
class ParsedTone:
    freq: Any
    duration: float
    wave: Any
    pitch: float
    amplitude: float
    vibrato: float
    vibratoRate: float
    vibratoWave: Any
    tremolo: float
    tremoloRate: float
    tremoloWave: Any
    modFreq: Any
    modDepth: float
    modWave: Any
    pan: float
    autoPanEnabled: bool
    autoPanDepth: float
    autoPanRate: float
    autoPanWave: Any
    autoPanOffset: float
    bend: Any
    bendEasing: Any
    bendIn: Any
    bendInDuration: float
    bendInEasing: Any
    bendOut: Any
    bendOutDuration: float
    bendOutEasing: Any
    amplitudeBend: Any
    amplitudeEasing: Any
    fadeInDuration: float
    fadeInEasing: Any
    fadeOutDuration: float
    fadeOutEasing: Any
    phaseDegrees: Any
    unisonVoices: int
    unisonDetune: float
    unisonSpread: float
    performanceBend: Any
    performanceBendEasing: Any
    performanceBendStepped: bool
    performanceBendRatios: Any
    performanceBendDuration: float
    performanceBendIn: Any
    performanceBendInDuration: float
    performanceBendInEasing: Any
    performanceBendOut: Any
    performanceBendOutDuration: float
    performanceBendOutEasing: Any
    performancePortamentoStart: Any
    performancePortamentoDuration: float
    performanceTrill: Any
    performanceTrillLength: float
    performanceTrillDuration: float
    performanceVibrato: float
    performanceVibratoRate: float
    performanceVibratoWave: Any


@dataclass(slots = True, eq = False)
class SilenceRenderEvent:
    duration: float
    sampleCount: int


@dataclass(slots = True, eq = False)
class InsertRenderEvent:
    samples: Any
    sampleCount: int


@dataclass(slots = True, eq = False)
class ToneRenderEvent:
    freq: float
    duration: float
    wave: Any
    pitch: float
    amplitude: float
    vibrato: float
    vibratoRate: float
    vibratoWave: Any
    tremolo: float
    tremoloRate: float
    tremoloWave: Any
    modFreq: Any
    modDepth: float
    modWave: Any
    pan: float
    autoPanEnabled: bool
    autoPanDepth: float
    autoPanRate: float
    autoPanWave: Any
    autoPanOffset: float
    continueAutoPan: bool
    arpeggioGroup: Any
    bend: Any
    bendEasing: Any
    bendDuration: float
    bendOffset: float
    bendIn: Any
    bendInDuration: float
    bendInEasing: Any
    bendOut: Any
    bendOutDuration: float
    bendOutEasing: Any
    amplitudeBend: Any
    amplitudeEasing: Any
    amplitudeBendDuration: float
    amplitudeBendOffset: float
    fadeInDuration: float
    fadeInEasing: Any
    fadeOutDuration: float
    fadeOutEasing: Any
    scopedDuration: float
    phaseDegrees: Any
    unisonVoices: int
    unisonDetune: float
    unisonSpread: float
    performanceBend: Any
    performanceBendEasing: Any
    performanceBendStepped: bool
    performanceBendRatios: Any
    performanceBendDuration: float
    performanceBendOffset: float
    performanceBendIn: Any
    performanceBendInDuration: float
    performanceBendInEasing: Any
    performanceBendOut: Any
    performanceBendOutDuration: float
    performanceBendOutEasing: Any
    performancePortamentoStart: Any
    performancePortamentoDuration: float
    performancePortamentoOffset: float
    performanceTrill: Any
    performanceTrillLength: float
    performanceTrillDuration: float
    performanceOffset: float
    performanceVibrato: float
    performanceVibratoRate: float
    performanceVibratoWave: Any
    isNoise: bool
    fadeIn: bool
    fadeOut: bool
    fadeFrames: int
    sampleCount: int


@dataclass(slots = True)
class ToneRenderSettings:
    freq: float
    duration: float
    wave: Any
    pitch: float
    amplitude: float
    vibrato: float
    vibratoRate: float
    vibratoPhase: float
    vibratoWave: Any
    tremolo: float
    tremoloRate: float
    tremoloWave: Any
    modFreq: Any
    modDepth: float
    modWave: Any
    modPhase: float
    bend: Any
    bendEasing: Any
    bendIn: Any
    bendInDuration: float
    bendInEasing: Any
    bendOut: Any
    bendOutDuration: float
    bendOutEasing: Any
    amplitudeBend: Any
    amplitudeEasing: Any
    fadeInDuration: float
    fadeInEasing: Any
    fadeOutDuration: float
    fadeOutEasing: Any
    scopedDuration: float
    oscillatorPhase: float
    fadeIn: bool
    fadeOut: bool
    phaseDegrees: Any
    tremoloPhase: float
    performanceBend: Any
    performanceBendEasing: Any
    performanceBendStepped: bool
    performanceBendRatios: Any
    performanceBendDuration: float
    performanceBendOffset: float
    performanceBendIn: Any
    performanceBendInDuration: float
    performanceBendInEasing: Any
    performanceBendOut: Any
    performanceBendOutDuration: float
    performanceBendOutEasing: Any
    performancePortamentoStart: Any
    performancePortamentoDuration: float
    performancePortamentoOffset: float
    performanceTrill: Any
    performanceTrillLength: float
    performanceTrillDuration: float
    performanceOffset: float
    performanceVibrato: float
    performanceVibratoRate: float
    performanceVibratoWave: Any
    bendDuration: float
    amplitudeBendDuration: float
    bendOffset: float
    amplitudeBendOffset: float
    fadeFrames: int


@dataclass(slots = True)
class ChirpRenderState:
    vibratoPhase: float
    tremoloPhase: float
    modPhase: float
    autoPanPhaseDegrees: float
    oscillatorPhases: list


__all__ = [
    "ChirpRenderPlan",
    "ChirpRenderState",
    "InsertRenderEvent",
    "ParsedTone",
    "SilenceRenderEvent",
    "ToneRenderEvent",
    "ToneRenderSettings",
]
