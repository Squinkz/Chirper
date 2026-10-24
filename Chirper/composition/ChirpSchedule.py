from dataclasses import dataclass
from typing import Any


@dataclass(slots = True)
class SequenceSegment:
    section: Any
    tempo: float
    meter: Any
    start: Any
    end: Any


@dataclass(slots = True, eq = False)
class ScheduledNote:
    note: Any
    patch: Any
    balance: float
    polyphonic: bool
    portamento: bool
    portamentoStart: Any
    portamentoDuration: float
    startFrame: int
    duration: float
    performanceOffsetFrames: int
    performanceDuration: float
    bendInDuration: float
    bendOutDuration: float
    fadeInDuration: float
    fadeOutDuration: float
    forceEnvelopeRetrigger: bool
    arpeggioGroup: Any
    trillLength: Any
    eventIndex: int
    discarded: bool = False
    fadeTarget: Any = None
    renderAmplitude: float = 0.0
    freq: Any = None
    noteTremolo: Any = None
    noteAutoPan: Any = None
    tremoloPhaseDegrees: float = 0.0
    autoPanOffset: float = 0.0
    samples: Any = None


@dataclass(slots = True)
class EnvelopeRenderInfo:
    gains: Any
    offsetFrames: int
    extend: bool


@dataclass(slots = True)
class PatchToneLayer:
    event: Any
    gain: float
    request: ScheduledNote
    requestIndex: int
    requestOffsetFrames: int
    startFrame: int
    sectionName: str
    envelopeInfo: Any = None


__all__ = [
    "EnvelopeRenderInfo",
    "PatchToneLayer",
    "ScheduledNote",
    "SequenceSegment",
]
