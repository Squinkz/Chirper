import math
import os
from typing import NamedTuple

import numpy as np


numbaDisabled = os.environ.get("CHIRPER_DISABLE_NUMBA", "").lower() in ("1", "true", "yes", "on")

if numbaDisabled:
    njit = None
    NUMBA_AVAILABLE = False
else:
    try:
        from numba import njit

        NUMBA_AVAILABLE = True
    except ImportError:
        njit = None
        NUMBA_AVAILABLE = False


NUMBA_ENABLED = NUMBA_AVAILABLE

WAVE_SINE = 0
WAVE_PULSE50 = 1
WAVE_PULSE25 = 2
WAVE_PULSE12 = 3
WAVE_TRIANGLE = 4
WAVE_SAW = 5
WAVE_PULSE50_AA = 6
WAVE_PULSE25_AA = 7
WAVE_PULSE12_AA = 8
WAVE_SAW_AA = 9
WAVE_TRIANGLE_AA = 10

TRIANGLE_TABLE_SIZE = 2048
TRIANGLE_HARMONIC_LIMITS = np.asarray([1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024], dtype = np.int64)

EASING_LINEAR = 0
EASING_IN_SINE = 1
EASING_OUT_SINE = 2
EASING_IN_OUT_SINE = 3
EASING_IN_QUAD = 4
EASING_OUT_QUAD = 5
EASING_IN_OUT_QUAD = 6
EASING_IN_CUBIC = 7
EASING_OUT_CUBIC = 8
EASING_IN_OUT_CUBIC = 9
EASING_IN_EXPO = 10
EASING_OUT_EXPO = 11
EASING_IN_OUT_EXPO = 12
EASING_IN_QUART = 13
EASING_OUT_QUART = 14
EASING_IN_OUT_QUART = 15
EASING_IN_QUINT = 16
EASING_OUT_QUINT = 17
EASING_IN_OUT_QUINT = 18
EASING_IN_CIRCLE = 19
EASING_OUT_CIRCLE = 20
EASING_IN_OUT_CIRCLE = 21
EASING_IN_ELASTIC = 22
EASING_OUT_ELASTIC = 23
EASING_IN_OUT_ELASTIC = 24
EASING_IN_BACK = 25
EASING_OUT_BACK = 26
EASING_IN_OUT_BACK = 27
EASING_IN_BOUNCE = 28
EASING_OUT_BOUNCE = 29
EASING_IN_OUT_BOUNCE = 30
EASING_IN_LOG = 31
EASING_OUT_LOG = 32
EASING_IN_OUT_LOG = 33
EASING_SMOOTH_STEP_3 = 34
EASING_SMOOTH_STEP_5 = 35
EASING_SMOOTH_STEP_7 = 36

FILTER_LOW_PASS = 0
FILTER_HIGH_PASS = 1
FILTER_BAND_PASS = 2
FILTER_NOTCH = 3
FILTER_PEAK = 4
FILTER_LOW_SHELF = 5
FILTER_HIGH_SHELF = 6


class KernelOscillatorSettings(NamedTuple):
    count: int
    sampleRate: int
    minFreq: float
    startFreq: float
    waveId: int
    oscillatorPhase: float


class KernelAmplitudeSettings(NamedTuple):
    amplitude: float
    hasBend: bool
    target: float
    easingId: int
    duration: float
    offset: float


class KernelVibratoSettings(NamedTuple):
    depth: float
    rate: float
    phase: float
    waveId: int
    performanceDepth: float
    performanceRate: float
    performanceWaveId: int
    performanceOffset: float


class KernelTremoloSettings(NamedTuple):
    depth: float
    rate: float
    phase: float
    waveId: int


class KernelModulationSettings(NamedTuple):
    freq: float
    depth: float
    phase: float
    waveId: int


class KernelBendSettings(NamedTuple):
    hasBend: bool
    targetFreq: float
    easingId: int
    duration: float
    offset: float
    hasBendIn: bool
    bendInFreq: float
    bendInEasingId: int
    bendInDuration: float
    hasBendOut: bool
    bendOutFreq: float
    bendOutEasingId: int
    bendOutDuration: float
    scopedDuration: float
    hasPerformanceBend: bool
    targetPerformanceFreq: float
    performanceEasingId: int
    performanceStepped: bool
    performanceRatios: object
    performanceDuration: float
    performanceOffset: float
    hasPerformanceBendIn: bool
    performanceBendInFreq: float
    performanceBendInEasingId: int
    performanceBendInDuration: float
    hasPerformanceBendOut: bool
    performanceBendOutFreq: float
    performanceBendOutEasingId: int
    performanceBendOutDuration: float


class KernelPortamentoSettings(NamedTuple):
    enabled: bool
    startFreq: float
    duration: float
    offset: float


class KernelTrillSettings(NamedTuple):
    enabled: bool
    targetFreq: float
    length: float
    duration: float


class KernelFadeSettings(NamedTuple):
    frames: int
    fadeIn: bool
    fadeOut: bool


def CreateTriangleTables():
    phases = (np.arange(TRIANGLE_TABLE_SIZE, dtype = np.float64) / TRIANGLE_TABLE_SIZE)
    rawTriangle = 1.0 - (4.0 * np.abs(phases - 0.5))
    rawSpectrum = np.fft.rfft(rawTriangle)
    tables = np.empty((len(TRIANGLE_HARMONIC_LIMITS), TRIANGLE_TABLE_SIZE), dtype = np.float64)

    for tableIndex, harmonicLimit in enumerate(TRIANGLE_HARMONIC_LIMITS):
        spectrum = rawSpectrum.copy()
        spectrum[harmonicLimit + 1:] = 0.0
        tables[tableIndex] = np.fft.irfft(spectrum, n = TRIANGLE_TABLE_SIZE)

    tables.setflags(write = False)
    return tables


TRIANGLE_TABLES = CreateTriangleTables()


def SetNumbaEnabled(enabled):
    global NUMBA_ENABLED

    NUMBA_ENABLED = NUMBA_AVAILABLE and bool(enabled)
    return NUMBA_ENABLED


def GetEasingId(easing):
    if easing is None:
        return EASING_LINEAR

    easingKey = str(easing).replace("_", "").replace("-", "").lower()
    easingIds = {
        "linear": EASING_LINEAR,
        "lin": EASING_LINEAR,
        "insine": EASING_IN_SINE,
        "outsine": EASING_OUT_SINE,
        "inoutsine": EASING_IN_OUT_SINE,
        "inquad": EASING_IN_QUAD,
        "outquad": EASING_OUT_QUAD,
        "inoutquad": EASING_IN_OUT_QUAD,
        "incubic": EASING_IN_CUBIC,
        "outcubic": EASING_OUT_CUBIC,
        "inoutcubic": EASING_IN_OUT_CUBIC,
        "inquart": EASING_IN_QUART,
        "outquart": EASING_OUT_QUART,
        "inoutquart": EASING_IN_OUT_QUART,
        "inquint": EASING_IN_QUINT,
        "outquint": EASING_OUT_QUINT,
        "inoutquint": EASING_IN_OUT_QUINT,
        "incircle": EASING_IN_CIRCLE,
        "outcircle": EASING_OUT_CIRCLE,
        "inoutcircle": EASING_IN_OUT_CIRCLE,
        "inexpo": EASING_IN_EXPO,
        "outexpo": EASING_OUT_EXPO,
        "inoutexpo": EASING_IN_OUT_EXPO,
        "inelastic": EASING_IN_ELASTIC,
        "outelastic": EASING_OUT_ELASTIC,
        "inoutelastic": EASING_IN_OUT_ELASTIC,
        "inback": EASING_IN_BACK,
        "outback": EASING_OUT_BACK,
        "inoutback": EASING_IN_OUT_BACK,
        "inbounce": EASING_IN_BOUNCE,
        "outbounce": EASING_OUT_BOUNCE,
        "inoutbounce": EASING_IN_OUT_BOUNCE,
        "log": EASING_OUT_LOG,
        "logarithmic": EASING_OUT_LOG,
        "inlog": EASING_IN_LOG,
        "outlog": EASING_OUT_LOG,
        "inoutlog": EASING_IN_OUT_LOG,
        "smoothstep3": EASING_SMOOTH_STEP_3,
        "smoothstep5": EASING_SMOOTH_STEP_5,
        "smoothstep7": EASING_SMOOTH_STEP_7,
        "equalpower": EASING_OUT_SINE,
        "cos": EASING_IN_OUT_SINE,
        "cosine": EASING_IN_OUT_SINE,
    }

    if easingKey not in easingIds:
        raise ValueError("Unknown easing: " + str(easing))

    return easingIds[easingKey]


def GetFilterTypeId(filterType):
    filterTypes = {
        "lowPass": FILTER_LOW_PASS,
        "highPass": FILTER_HIGH_PASS,
        "bandPass": FILTER_BAND_PASS,
        "notch": FILTER_NOTCH,
        "peak": FILTER_PEAK,
        "lowShelf": FILTER_LOW_SHELF,
        "highShelf": FILTER_HIGH_SHELF,
    }

    if filterType not in filterTypes:
        raise ValueError("Unknown biquad sweep type: " + str(filterType))

    return filterTypes[filterType]


if NUMBA_AVAILABLE:
    CompileKernel = njit(cache = True, fastmath = False, nogil = True)
else:
    def CompileKernel(function):
        return function


# -----------------------------------
# Shared Numeric Functions
# -----------------------------------

@CompileKernel
def ApplyOutBounce(value):
    scale = 7.5625
    divisor = 2.75
    if value < 1.0 / divisor:
        return scale * value * value
    if value < 2.0 / divisor:
        value -= 1.5 / divisor
        return (scale * value * value) + 0.75
    if value < 2.5 / divisor:
        value -= 2.25 / divisor
        return (scale * value * value) + 0.9375

    value -= 2.625 / divisor
    return (scale * value * value) + 0.984375


@CompileKernel
def ApplyEasing(value, easingId):
    value = max(0.0, min(1.0, value))

    if easingId == EASING_IN_SINE:
        result = 1.0 - math.cos((value * math.pi) / 2.0)
    elif easingId == EASING_OUT_SINE:
        result = math.sin((value * math.pi) / 2.0)
    elif easingId == EASING_IN_OUT_SINE:
        result = -(math.cos(math.pi * value) - 1.0) / 2.0
    elif easingId == EASING_IN_QUAD:
        result = value * value
    elif easingId == EASING_OUT_QUAD:
        result = 1.0 - ((1.0 - value) * (1.0 - value))
    elif easingId == EASING_IN_OUT_QUAD:
        if value < 0.5:
            result = 2.0 * value * value
        else:
            result = 1.0 - (math.pow((-2.0 * value) + 2.0, 2.0) / 2.0)
    elif easingId == EASING_IN_CUBIC:
        result = value * value * value
    elif easingId == EASING_OUT_CUBIC:
        result = 1.0 - math.pow(1.0 - value, 3.0)
    elif easingId == EASING_IN_OUT_CUBIC:
        if value < 0.5:
            result = 4.0 * value * value * value
        else:
            result = 1.0 - (math.pow((-2.0 * value) + 2.0, 3.0) / 2.0)
    elif easingId == EASING_IN_QUART:
        result = value ** 4
    elif easingId == EASING_OUT_QUART:
        result = 1.0 - math.pow(1.0 - value, 4.0)
    elif easingId == EASING_IN_OUT_QUART:
        if value < 0.5:
            result = 8.0 * value ** 4
        else:
            result = 1.0 - (math.pow((-2.0 * value) + 2.0, 4.0) / 2.0)
    elif easingId == EASING_IN_QUINT:
        result = value ** 5
    elif easingId == EASING_OUT_QUINT:
        result = 1.0 - math.pow(1.0 - value, 5.0)
    elif easingId == EASING_IN_OUT_QUINT:
        if value < 0.5:
            result = 16.0 * value ** 5
        else:
            result = 1.0 - (math.pow((-2.0 * value) + 2.0, 5.0) / 2.0)
    elif easingId == EASING_IN_CIRCLE:
        result = 1.0 - math.sqrt(1.0 - (value * value))
    elif easingId == EASING_OUT_CIRCLE:
        result = math.sqrt(1.0 - ((value - 1.0) ** 2))
    elif easingId == EASING_IN_OUT_CIRCLE:
        if value < 0.5:
            result = (1.0 - math.sqrt(1.0 - ((2.0 * value) ** 2))) / 2.0
        else:
            result = (math.sqrt(1.0 - (((-2.0 * value) + 2.0) ** 2)) + 1.0) / 2.0
    elif easingId == EASING_IN_EXPO:
        result = 0.0 if value == 0.0 else math.pow(2.0, (10.0 * value) - 10.0)
    elif easingId == EASING_OUT_EXPO:
        result = 1.0 if value == 1.0 else 1.0 - math.pow(2.0, -10.0 * value)
    elif easingId == EASING_IN_OUT_EXPO:
        if value == 0.0:
            result = 0.0
        elif value == 1.0:
            result = 1.0
        elif value < 0.5:
            result = math.pow(2.0, (20.0 * value) - 10.0) / 2.0
        else:
            result = (2.0 - math.pow(2.0, (-20.0 * value) + 10.0)) / 2.0
    elif easingId == EASING_IN_ELASTIC:
        if value == 0.0 or value == 1.0:
            result = value
        else:
            period = (2.0 * math.pi) / 3.0
            result = -math.pow(2.0, (10.0 * value) - 10.0) * math.sin(((10.0 * value) - 10.75) * period)
    elif easingId == EASING_OUT_ELASTIC:
        if value == 0.0 or value == 1.0:
            result = value
        else:
            period = (2.0 * math.pi) / 3.0
            result = (math.pow(2.0, -10.0 * value) * math.sin(((10.0 * value) - 0.75) * period)) + 1.0
    elif easingId == EASING_IN_OUT_ELASTIC:
        if value == 0.0 or value == 1.0:
            result = value
        else:
            period = (2.0 * math.pi) / 4.5
            if value < 0.5:
                result = -(math.pow(2.0, (20.0 * value) - 10.0) * math.sin(((20.0 * value) - 11.125) * period)) / 2.0
            else:
                result = (math.pow(2.0, (-20.0 * value) + 10.0) * math.sin(((20.0 * value) - 11.125) * period) / 2.0) + 1.0
    elif easingId == EASING_IN_BACK:
        overshoot = 1.70158
        result = ((overshoot + 1.0) * value ** 3) - (overshoot * value ** 2)
    elif easingId == EASING_OUT_BACK:
        overshoot = 1.70158
        result = 1.0 + ((overshoot + 1.0) * (value - 1.0) ** 3) + (overshoot * (value - 1.0) ** 2)
    elif easingId == EASING_IN_OUT_BACK:
        overshoot = 1.70158 * 1.525
        if value < 0.5:
            result = (((2.0 * value) ** 2) * (((overshoot + 1.0) * 2.0 * value) - overshoot)) / 2.0
        else:
            result = ((((2.0 * value) - 2.0) ** 2) * (((overshoot + 1.0) * ((2.0 * value) - 2.0)) + overshoot) + 2.0) / 2.0
    elif easingId == EASING_IN_BOUNCE:
        result = 1.0 - ApplyOutBounce(1.0 - value)
    elif easingId == EASING_OUT_BOUNCE:
        result = ApplyOutBounce(value)
    elif easingId == EASING_IN_OUT_BOUNCE:
        if value < 0.5:
            result = (1.0 - ApplyOutBounce(1.0 - (2.0 * value))) / 2.0
        else:
            result = (1.0 + ApplyOutBounce((2.0 * value) - 1.0)) / 2.0
    elif easingId == EASING_IN_LOG:
        result = 1.0 - math.log10(10.0 - (9.0 * value))
    elif easingId == EASING_OUT_LOG:
        result = math.log10(1.0 + (9.0 * value))
    elif easingId == EASING_IN_OUT_LOG:
        if value < 0.5:
            result = (1.0 - math.log10(10.0 - (18.0 * value))) / 2.0
        else:
            result = (math.log10((18.0 * value) - 8.0) + 1.0) / 2.0
    elif easingId == EASING_SMOOTH_STEP_3:
        result = -(2.0 * (value ** 3.0)) + (3.0 * (value ** 2.0))
    elif easingId == EASING_SMOOTH_STEP_5:
        result = (6.0 * (value ** 5.0)) - (15.0 * (value ** 4.0)) + (10.0 * (value ** 3.0))
    elif easingId == EASING_SMOOTH_STEP_7:
        result = -(20.0 * (value ** 7.0)) + (70.0 * (value ** 6.0)) - (84.0 * (value ** 5.0)) + (35.0 * (value ** 4.0))
    else:
        result = value

    return result


@CompileKernel
def PolyBlep(phase, phaseIncrement):
    phaseIncrement = min(0.5, max(0.0, abs(phaseIncrement)))
    if phaseIncrement <= 0.0:
        return 0.0

    if phase < phaseIncrement:
        normalizedPhase = phase / phaseIncrement
        return normalizedPhase + normalizedPhase - (normalizedPhase * normalizedPhase) - 1.0

    if phase > 1.0 - phaseIncrement:
        normalizedPhase = (phase - 1.0) / phaseIncrement
        return (normalizedPhase * normalizedPhase) + normalizedPhase + normalizedPhase + 1.0

    return 0.0


@CompileKernel
def GetTriangleValue(phase, phaseIncrement):
    if phaseIncrement <= 0.0:
        lowerTableIndex = len(TRIANGLE_HARMONIC_LIMITS) - 1
        upperTableIndex = lowerTableIndex
        tableBlend = 0.0
    else:
        maximumHarmonic = 0.5 / abs(phaseIncrement)
        lowerTableIndex = 0
        upperTableIndex = 0
        for index in range(1, len(TRIANGLE_HARMONIC_LIMITS)):
            if TRIANGLE_HARMONIC_LIMITS[index] <= maximumHarmonic:
                lowerTableIndex = index
                upperTableIndex = index
            else:
                upperTableIndex = index
                break
        lowerLimit = TRIANGLE_HARMONIC_LIMITS[lowerTableIndex]
        upperLimit = TRIANGLE_HARMONIC_LIMITS[upperTableIndex]
        tableBlend = 0.0
        if upperLimit > lowerLimit:
            tableBlend = max(0.0, min(1.0, (maximumHarmonic - lowerLimit) / (upperLimit - lowerLimit)))

    tablePosition = phase * TRIANGLE_TABLE_SIZE
    firstIndex = int(tablePosition) % TRIANGLE_TABLE_SIZE
    secondIndex = (firstIndex + 1) % TRIANGLE_TABLE_SIZE
    fraction = tablePosition - int(tablePosition)
    lowerValue = (
        TRIANGLE_TABLES[lowerTableIndex, firstIndex]
        + ((TRIANGLE_TABLES[lowerTableIndex, secondIndex]
        - TRIANGLE_TABLES[lowerTableIndex, firstIndex]) * fraction)
    )
    if upperTableIndex == lowerTableIndex:
        return lowerValue

    upperValue = (
        TRIANGLE_TABLES[upperTableIndex, firstIndex]
        + ((TRIANGLE_TABLES[upperTableIndex, secondIndex]
        - TRIANGLE_TABLES[upperTableIndex, firstIndex]) * fraction)
    )
    return lowerValue + ((upperValue - lowerValue) * tableBlend)


@CompileKernel
def GetWavePhaseValue(waveId, phase, phaseIncrement):
    if waveId == WAVE_SINE:
        return math.sin(2.0 * math.pi * phase)
    if waveId == WAVE_PULSE50:
        return 1.0 if phase < 0.5 else -1.0
    if waveId == WAVE_PULSE25:
        return 1.0 if phase < 0.25 else -1.0
    if waveId == WAVE_PULSE12:
        return 1.0 if phase < 0.125 else -1.0
    if waveId == WAVE_TRIANGLE:
        return 1.0 - (4.0 * abs(phase - 0.5))
    if waveId == WAVE_TRIANGLE_AA:
        return GetTriangleValue(phase, phaseIncrement)
    if waveId == WAVE_SAW_AA:
        return (((phase * 2.0) - 1.0) - PolyBlep(phase, phaseIncrement))
    if (waveId == WAVE_PULSE50_AA or waveId == WAVE_PULSE25_AA or waveId == WAVE_PULSE12_AA):
        if waveId == WAVE_PULSE50_AA:
            width = 0.5
        elif waveId == WAVE_PULSE25_AA:
            width = 0.25
        else:
            width = 0.125

        sample = 1.0 if phase < width else -1.0
        sample += PolyBlep(phase, phaseIncrement)
        sample -= PolyBlep((phase - width) % 1.0, phaseIncrement)
        return sample

    return (phase * 2.0) - 1.0


@CompileKernel
def GetLfoValue(waveId, phase, phaseIncrement):
    if waveId == WAVE_SINE:
        return math.sin(phase)

    normalizedPhase = (phase / (2.0 * math.pi)) % 1.0
    return max(-1.0, min(1.0, GetWavePhaseValue(waveId, normalizedPhase, abs(phaseIncrement) / (2.0 * math.pi))))


# -----------------------------------
# Synthesis
# -----------------------------------

@CompileKernel
def MakeTone(
        oscillatorSettings, amplitudeSettings, vibratoSettings,
        tremoloSettings, modulationSettings, bendSettings,
        portamentoSettings, trillSettings, fadeSettings
        ):
    count = oscillatorSettings.count
    sampleRate = oscillatorSettings.sampleRate
    minFreq = oscillatorSettings.minFreq
    startFreq = oscillatorSettings.startFreq
    waveId = oscillatorSettings.waveId
    oscillatorPhase = oscillatorSettings.oscillatorPhase
    amplitude = amplitudeSettings.amplitude
    hasAmplitudeBend = amplitudeSettings.hasBend
    targetAmplitude = amplitudeSettings.target
    amplitudeEasingId = amplitudeSettings.easingId
    amplitudeBendDuration = amplitudeSettings.duration
    amplitudeBendOffset = amplitudeSettings.offset
    vibrato = vibratoSettings.depth
    vibratoRate = vibratoSettings.rate
    vibratoPhase = vibratoSettings.phase
    vibratoWaveId = vibratoSettings.waveId
    performanceVibrato = vibratoSettings.performanceDepth
    performanceVibratoRate = vibratoSettings.performanceRate
    performanceVibratoWaveId = vibratoSettings.performanceWaveId
    performanceOffset = vibratoSettings.performanceOffset
    tremolo = tremoloSettings.depth
    tremoloRate = tremoloSettings.rate
    tremoloPhase = tremoloSettings.phase
    tremoloWaveId = tremoloSettings.waveId
    modFreq = modulationSettings.freq
    modDepth = modulationSettings.depth
    modPhase = modulationSettings.phase
    modWaveId = modulationSettings.waveId
    hasBend = bendSettings.hasBend
    targetFreq = bendSettings.targetFreq
    bendEasingId = bendSettings.easingId
    bendDuration = bendSettings.duration
    bendOffset = bendSettings.offset
    hasBendIn = bendSettings.hasBendIn
    bendInFreq = bendSettings.bendInFreq
    bendInEasingId = bendSettings.bendInEasingId
    bendInDuration = bendSettings.bendInDuration
    hasBendOut = bendSettings.hasBendOut
    bendOutFreq = bendSettings.bendOutFreq
    bendOutEasingId = bendSettings.bendOutEasingId
    bendOutDuration = bendSettings.bendOutDuration
    scopedDuration = bendSettings.scopedDuration
    hasPerformanceBend = bendSettings.hasPerformanceBend
    targetPerformanceFreq = bendSettings.targetPerformanceFreq
    performanceBendEasingId = bendSettings.performanceEasingId
    performanceBendStepped = bendSettings.performanceStepped
    performanceBendRatios = bendSettings.performanceRatios
    performanceBendDuration = bendSettings.performanceDuration
    performanceBendOffset = bendSettings.performanceOffset
    hasPerformanceBendIn = bendSettings.hasPerformanceBendIn
    performanceBendInFreq = bendSettings.performanceBendInFreq
    performanceBendInEasingId = bendSettings.performanceBendInEasingId
    performanceBendInDuration = bendSettings.performanceBendInDuration
    hasPerformanceBendOut = bendSettings.hasPerformanceBendOut
    performanceBendOutFreq = bendSettings.performanceBendOutFreq
    performanceBendOutEasingId = bendSettings.performanceBendOutEasingId
    performanceBendOutDuration = bendSettings.performanceBendOutDuration
    hasPerformancePortamento = portamentoSettings.enabled
    performancePortamentoStartFreq = portamentoSettings.startFreq
    performancePortamentoDuration = portamentoSettings.duration
    performancePortamentoOffset = portamentoSettings.offset
    hasPerformanceTrill = trillSettings.enabled
    targetPerformanceTrillFreq = trillSettings.targetFreq
    performanceTrillLength = trillSettings.length
    performanceTrillDuration = trillSettings.duration
    fade = fadeSettings.frames
    fadeIn = fadeSettings.fadeIn
    fadeOut = fadeSettings.fadeOut

    samples = np.empty(count, dtype = np.float64)
    phase = oscillatorPhase
    startAmplitude = amplitude
    vibratoIncrement = (2.0 * math.pi * vibratoRate) / sampleRate
    performanceVibratoIncrement = (2.0 * math.pi * performanceVibratoRate) / sampleRate
    performanceVibratoPhase = 2.0 * math.pi * performanceVibratoRate * performanceOffset
    tremoloIncrement = (2.0 * math.pi * tremoloRate) / sampleRate
    modIncrement = (2.0 * math.pi * modFreq) / sampleRate
    bendFrames = max(0, int(sampleRate * bendDuration))
    bendOffsetFrames = round(bendOffset * sampleRate)
    bendDivisor = max(1, bendFrames - 1)
    scopedFrames = max(0, int(sampleRate * scopedDuration))
    bendInFrames = max(0, int(sampleRate * bendInDuration))
    bendInDivisor = max(1, bendInFrames - 1)
    bendOutFrames = max(0, int(sampleRate * bendOutDuration))
    bendOutStart = max(0, scopedFrames - bendOutFrames)
    bendOutDivisor = max(1, bendOutFrames - 1)
    amplitudeFrames = max(0, int(sampleRate * amplitudeBendDuration))
    amplitudeOffsetFrames = round(amplitudeBendOffset * sampleRate)
    amplitudeDivisor = max(1, amplitudeFrames - 1)
    portamentoFrames = max(0, int(sampleRate * performancePortamentoDuration))
    portamentoOffsetFrames = round(performancePortamentoOffset * sampleRate)
    portamentoDivisor = max(1, portamentoFrames - 1)
    performanceFrames = max(0, int(sampleRate * performanceBendDuration))
    performanceBendOffsetFrames = round(performanceBendOffset * sampleRate)
    performanceDivisor = max(1, performanceFrames - 1)
    performanceBendInFrames = max(0, int(sampleRate * performanceBendInDuration))
    performanceBendInDivisor = max(1, performanceBendInFrames - 1)
    performanceBendOutFrames = max(0, int(sampleRate * performanceBendOutDuration))
    performanceBendOutStart = max(0, performanceFrames - performanceBendOutFrames)
    performanceBendOutDivisor = max(1, performanceBendOutFrames - 1)
    trillFrames = max(1, int(sampleRate * performanceTrillLength))
    gateFrames = max(0, int(sampleRate * performanceTrillDuration))
    performanceOffsetFrames = round(performanceOffset * sampleRate)
    for index in range(count):
        bendFrame = bendOffsetFrames + index
        bendPercent = min(1.0, bendFrame / bendDivisor)
        currentAmplitude = startAmplitude
        if hasAmplitudeBend:
            amplitudeFrame = amplitudeOffsetFrames + index
            amplitudePercent = min(1.0, amplitudeFrame / amplitudeDivisor)
            amplitudePercent = ApplyEasing(amplitudePercent, amplitudeEasingId)
            currentAmplitude = startAmplitude + ((targetAmplitude - startAmplitude) * amplitudePercent)

        bentFreq = startFreq
        if hasBend:
            frequencyPercent = ApplyEasing(bendPercent, bendEasingId)
            bentFreq = startFreq + ((targetFreq - startFreq) * frequencyPercent)
        elif hasBendIn or hasBendOut:
            scopedFrame = bendOffsetFrames + index
            if hasBendIn and scopedFrame < bendInFrames:
                bendInPercent = min(1.0, scopedFrame / bendInDivisor)
                bendInPercent = ApplyEasing(bendInPercent, bendInEasingId)
                bentFreq = bendInFreq + (
                    (startFreq - bendInFreq) * bendInPercent
                )
            elif hasBendOut and scopedFrame >= bendOutStart:
                bendOutPercent = 1.0 if bendOutFrames == 1 else min(
                    1.0, (scopedFrame - bendOutStart) / bendOutDivisor
                )
                bendOutPercent = ApplyEasing(bendOutPercent, bendOutEasingId)
                bentFreq = startFreq + (
                    (bendOutFreq - startFreq) * bendOutPercent
                )

        if hasPerformancePortamento:
            portamentoFrame = portamentoOffsetFrames + index
            portamentoPercent = min(1.0, portamentoFrame / portamentoDivisor)
            portamentoFreq = performancePortamentoStartFreq * (
                (startFreq / performancePortamentoStartFreq) ** portamentoPercent
            )
            bentFreq *= portamentoFreq / startFreq

        if hasPerformanceBend:
            performanceFrame = performanceBendOffsetFrames + index
            performancePercent = min(1.0, performanceFrame / performanceDivisor)
            performancePercent = ApplyEasing(performancePercent, performanceBendEasingId)
            if performanceBendStepped and startFreq > 0.0:
                performancePercent = max(0.0, min(1.0, performancePercent))
                ratioIndex = math.floor(len(performanceBendRatios) * performancePercent)
                ratioIndex = max(0, min(len(performanceBendRatios) - 1, ratioIndex))
                if targetPerformanceFreq >= startFreq:
                    performanceFreq = startFreq * performanceBendRatios[ratioIndex]
                else:
                    performanceFreq = startFreq / performanceBendRatios[ratioIndex]
            else:
                performanceFreq = startFreq + (
                    (targetPerformanceFreq - startFreq) * performancePercent
                )
            if startFreq != 0.0:
                bentFreq *= performanceFreq / startFreq
        elif hasPerformanceBendIn or hasPerformanceBendOut:
            performanceFrame = performanceBendOffsetFrames + index
            performanceFreq = startFreq
            if (
                    hasPerformanceBendIn
                    and performanceFrame < performanceBendInFrames
                    ):
                bendInPercent = min(
                    1.0, performanceFrame / performanceBendInDivisor
                )
                bendInPercent = ApplyEasing(
                    bendInPercent, performanceBendInEasingId
                )
                performanceFreq = performanceBendInFreq + (
                    (startFreq - performanceBendInFreq) * bendInPercent
                )
            elif (
                    hasPerformanceBendOut
                    and performanceFrame >= performanceBendOutStart
                    ):
                bendOutPercent = (
                    1.0 if performanceBendOutFrames == 1 else min(
                        1.0,
                        (performanceFrame - performanceBendOutStart)
                        / performanceBendOutDivisor
                    )
                )
                bendOutPercent = ApplyEasing(
                    bendOutPercent, performanceBendOutEasingId
                )
                performanceFreq = startFreq + (
                    (performanceBendOutFreq - startFreq) * bendOutPercent
                )
            if startFreq != 0.0:
                bentFreq *= performanceFreq / startFreq

        if hasPerformanceTrill and performanceTrillLength > 0.0 and startFreq > 0.0:
            trillFrame = min(
                performanceOffsetFrames + index,
                max(0, gateFrames - 1)
            )
            if (trillFrame // trillFrames) % 2 == 1:
                bentFreq *= targetPerformanceTrillFreq / startFreq

        vibratoCents = GetLfoValue(vibratoWaveId, vibratoPhase, vibratoIncrement) * vibrato
        performanceVibratoCents = GetLfoValue(
            performanceVibratoWaveId,
            performanceVibratoPhase,
            performanceVibratoIncrement
        ) * performanceVibrato
        vibratoMultiplier = 2.0 ** ((vibratoCents + performanceVibratoCents) / 1200.0)
        currentFreq = max(minFreq, bentFreq * vibratoMultiplier)

        currentTremoloPhase = tremoloPhase + ((2.0 * math.pi * tremoloRate * index) / sampleRate)
        tremoloValue = (GetLfoValue(tremoloWaveId, currentTremoloPhase, tremoloIncrement) + 1.0) * 0.5
        tremoloGain = 1.0 - (tremolo * tremoloValue)

        phase += currentFreq / sampleRate
        carrierPhase = phase
        if modFreq > 0.0 and modDepth > 0.0:
            modValue = GetLfoValue(modWaveId, modPhase, modIncrement)
            carrierPhase += (modValue * modDepth) / (2.0 * math.pi)
            modPhase += modIncrement

        sample = GetWavePhaseValue(
            waveId, carrierPhase % 1.0, abs(currentFreq) / sampleRate
        )
        vibratoPhase += vibratoIncrement
        performanceVibratoPhase += performanceVibratoIncrement

        if fade > 0:
            if fadeIn and index < fade:
                sample *= index / max(1, fade - 1)
            elif fadeOut and index >= count - fade:
                sample *= (count - index - 1) / max(1, fade - 1)

        samples[index] = sample * currentAmplitude * tremoloGain

    return samples, vibratoPhase, phase, modPhase


# -----------------------------------
# Biquad Filters
# -----------------------------------

@CompileKernel
def GetBiquadCoefficients(frequency, sampleRate, filterTypeId, db, q):
    frequency = max(1.0, min(sampleRate * 0.499, frequency))
    q = max(0.0001, q)
    omega = 2.0 * math.pi * frequency / sampleRate
    sinOmega = math.sin(omega)
    cosOmega = math.cos(omega)
    alpha = sinOmega / (2.0 * q)
    amp = 10.0 ** (db / 40.0)

    if filterTypeId == FILTER_LOW_PASS:
        b0 = (1.0 - cosOmega) * 0.5
        b1 = 1.0 - cosOmega
        b2 = (1.0 - cosOmega) * 0.5
        a0 = 1.0 + alpha
        a1 = -2.0 * cosOmega
        a2 = 1.0 - alpha
    elif filterTypeId == FILTER_HIGH_PASS:
        b0 = (1.0 + cosOmega) * 0.5
        b1 = -(1.0 + cosOmega)
        b2 = (1.0 + cosOmega) * 0.5
        a0 = 1.0 + alpha
        a1 = -2.0 * cosOmega
        a2 = 1.0 - alpha
    elif filterTypeId == FILTER_BAND_PASS:
        b0 = alpha
        b1 = 0.0
        b2 = -alpha
        a0 = 1.0 + alpha
        a1 = -2.0 * cosOmega
        a2 = 1.0 - alpha
    elif filterTypeId == FILTER_NOTCH:
        b0 = 1.0
        b1 = -2.0 * cosOmega
        b2 = 1.0
        a0 = 1.0 + alpha
        a1 = -2.0 * cosOmega
        a2 = 1.0 - alpha
    elif filterTypeId == FILTER_PEAK:
        b0 = 1.0 + (alpha * amp)
        b1 = -2.0 * cosOmega
        b2 = 1.0 - (alpha * amp)
        a0 = 1.0 + (alpha / amp)
        a1 = -2.0 * cosOmega
        a2 = 1.0 - (alpha / amp)
    elif filterTypeId == FILTER_LOW_SHELF:
        beta = 2.0 * math.sqrt(amp) * alpha
        b0 = amp * ((amp + 1.0) - ((amp - 1.0) * cosOmega) + beta)
        b1 = 2.0 * amp * ((amp - 1.0) - ((amp + 1.0) * cosOmega))
        b2 = amp * ((amp + 1.0) - ((amp - 1.0) * cosOmega) - beta)
        a0 = (amp + 1.0) + ((amp - 1.0) * cosOmega) + beta
        a1 = -2.0 * ((amp - 1.0) + ((amp + 1.0) * cosOmega))
        a2 = (amp + 1.0) + ((amp - 1.0) * cosOmega) - beta
    else:
        beta = 2.0 * math.sqrt(amp) * alpha
        b0 = amp * ((amp + 1.0) + ((amp - 1.0) * cosOmega) + beta)
        b1 = -2.0 * amp * ((amp - 1.0) + ((amp + 1.0) * cosOmega))
        b2 = amp * ((amp + 1.0) + ((amp - 1.0) * cosOmega) - beta)
        a0 = (amp + 1.0) - ((amp - 1.0) * cosOmega) + beta
        a1 = 2.0 * ((amp - 1.0) - ((amp + 1.0) * cosOmega))
        a2 = (amp + 1.0) - ((amp - 1.0) * cosOmega) - beta

    return b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0


@CompileKernel
def ApplyBiquad(samples, coefficients, channels):
    filtered = np.empty(len(samples), dtype = np.float64)
    states = np.zeros((channels, 4), dtype = np.float64)
    b0, b1, b2, a1, a2 = coefficients

    for index in range(len(samples)):
        channel = index % channels
        x1 = states[channel, 0]
        x2 = states[channel, 1]
        y1 = states[channel, 2]
        y2 = states[channel, 3]
        output = (b0 * samples[index]) + (b1 * x1) + (b2 * x2) - (a1 * y1) - (a2 * y2)

        states[channel, 1] = x1
        states[channel, 0] = samples[index]
        states[channel, 3] = y1
        states[channel, 2] = output
        filtered[index] = output

    return filtered


@CompileKernel
def ApplyBiquadTrack(samples, frequencies, channels, sampleRate, filterTypeId, db, q):
    frameCount = (len(samples) + channels - 1) // channels
    filtered = np.empty(len(samples), dtype = np.float64)
    states = np.zeros((channels, 4), dtype = np.float64)

    for frame in range(frameCount):
        b0, b1, b2, a1, a2 = GetBiquadCoefficients(
            frequencies[frame], sampleRate, filterTypeId, db, q
        )
        for channel in range(channels):
            sampleIndex = (frame * channels) + channel
            if sampleIndex >= len(samples):
                break
            x1 = states[channel, 0]
            x2 = states[channel, 1]
            y1 = states[channel, 2]
            y2 = states[channel, 3]
            output = (b0 * samples[sampleIndex]) + (b1 * x1) + (b2 * x2) - (a1 * y1) - (a2 * y2)

            states[channel, 1] = x1
            states[channel, 0] = samples[sampleIndex]
            states[channel, 3] = y1
            states[channel, 2] = output
            filtered[sampleIndex] = output

    return filtered


@CompileKernel
def ApplyBiquadSweep(
        samples, channels, sampleRate, filterTypeId,
        startFreq, endFreq, db, q, easingId
        ):
    frameCount = (len(samples) + channels - 1) // channels
    filtered = np.empty(len(samples), dtype = np.float64)
    states = np.zeros((channels, 4), dtype = np.float64)
    q = max(0.0001, q)
    frameDivisor = max(1, frameCount - 1)
    frequencyRatio = endFreq / startFreq
    maxFreq = sampleRate * 0.499

    for frame in range(frameCount):
        percent = frame / frameDivisor
        percent = ApplyEasing(percent, easingId)
        frequency = startFreq * (frequencyRatio ** percent)
        frequency = max(1.0, min(maxFreq, frequency))
        b0, b1, b2, a1, a2 = GetBiquadCoefficients(
            frequency, sampleRate, filterTypeId, db, q
        )

        for channel in range(channels):
            sampleIndex = (frame * channels) + channel
            if sampleIndex >= len(samples):
                break
            x1 = states[channel, 0]
            x2 = states[channel, 1]
            y1 = states[channel, 2]
            y2 = states[channel, 3]
            output = (b0 * samples[sampleIndex]) + (b1 * x1) + (b2 * x2) - (a1 * y1) - (a2 * y2)

            states[channel, 1] = x1
            states[channel, 0] = samples[sampleIndex]
            states[channel, 3] = y1
            states[channel, 2] = output
            filtered[sampleIndex] = output

    return filtered


# -----------------------------------
# Reverb Filters
# -----------------------------------

@CompileKernel
def FeedbackCombFilter(samples, delaySamples, feedback):
    output = np.zeros(len(samples), dtype = np.float64)

    for index in range(len(samples)):
        delayed = (output[index - delaySamples] if index >= delaySamples else 0.0)
        output[index] = samples[index] + (delayed * feedback)

    return output


@CompileKernel
def DampedFeedbackCombFilter(samples, delayFrames, feedback, damping):
    output = np.zeros(len(samples), dtype = np.float64)
    filterState = 0.0

    for index in range(len(samples)):
        delayed = output[index - delayFrames] if index >= delayFrames else 0.0
        filterState = (delayed * (1.0 - damping)) + (filterState * damping)
        output[index] = samples[index] + (filterState * feedback)

    return output


@CompileKernel
def AllPassFilter(samples, delaySamples, feedback):
    output = np.zeros(len(samples), dtype = np.float64)

    for index in range(len(samples)):
        delayedInput = (samples[index - delaySamples] if index >= delaySamples else 0.0)
        delayedOutput = (output[index - delaySamples] if index >= delaySamples else 0.0)
        output[index] = ((-feedback * samples[index]) + delayedInput + (feedback * delayedOutput))

    return output


def ProcessChorus(samples, channels, modulation, delayFrames, depthFrames, feedback, mix):
    frameCount = len(samples) // channels
    voiceCount = modulation.shape[1]
    bufferSize = max(3, int(math.ceil(delayFrames + depthFrames)) + 2)
    delayLines = np.zeros((channels, voiceCount, bufferSize), dtype = np.float64)
    output = np.empty(len(samples), dtype = np.float64)

    for frame in range(frameCount):
        writeIndex = frame % bufferSize
        for channel in range(channels):
            sampleIndex = (frame * channels) + channel
            source = samples[sampleIndex]
            wet = 0.0

            for voiceIndex in range(voiceCount):
                currentDelay = delayFrames + (depthFrames * modulation[channel, voiceIndex, frame])
                currentDelay = max(1.0, min(bufferSize - 2.0, currentDelay))
                readPosition = writeIndex - currentDelay
                if readPosition < 0.0:
                    readPosition += bufferSize

                firstIndex = int(math.floor(readPosition))
                secondIndex = (firstIndex + 1) % bufferSize
                fraction = readPosition - firstIndex
                firstSample = delayLines[channel, voiceIndex, firstIndex]
                secondSample = delayLines[channel, voiceIndex, secondIndex]
                delayed = firstSample + ((secondSample - firstSample) * fraction)
                delayLines[channel, voiceIndex, writeIndex] = source + (delayed * feedback)
                wet += delayed

            wet /= voiceCount
            output[sampleIndex] = (source * (1.0 - mix)) + (wet * mix)

    return output


def ProcessPhaser(samples, channels, modulation, minFreq, maxFreq, stages, feedback, mix, sampleRate):
    frameCount = len(samples) // channels
    inputStates = np.zeros((channels, stages), dtype = np.float64)
    outputStates = np.zeros((channels, stages), dtype = np.float64)
    feedbackStates = np.zeros(channels, dtype = np.float64)
    output = np.empty(len(samples), dtype = np.float64)

    for frame in range(frameCount):
        for channel in range(channels):
            sampleIndex = (frame * channels) + channel
            source = samples[sampleIndex]
            progress = (modulation[channel, frame] + 1.0) * 0.5
            progress = max(0.0, min(1.0, progress))
            frequency = minFreq * ((maxFreq / minFreq) ** progress)
            tangent = math.tan(math.pi * frequency / sampleRate)
            coefficient = (1.0 - tangent) / (1.0 + tangent)
            stageInput = source + (feedbackStates[channel] * feedback)

            for stage in range(stages):
                stageOutput = (
                    (-coefficient * stageInput)
                    + inputStates[channel, stage]
                    + (coefficient * outputStates[channel, stage])
                )
                inputStates[channel, stage] = stageInput
                outputStates[channel, stage] = stageOutput
                stageInput = stageOutput

            feedbackStates[channel] = stageInput
            output[sampleIndex] = (source * (1.0 - mix)) + (stageInput * mix)

    return output


CompiledChorus = CompileKernel(ProcessChorus)
CompiledPhaser = CompileKernel(ProcessPhaser)


@CompileKernel
def MTEntranceFilter(samples, delayFrames, factor, lpfAmp):
    buffer = np.zeros(delayFrames, dtype = np.float64)
    output = np.empty(len(samples), dtype = np.float64)
    index = 0
    lpfState = 0.0

    for sampleIndex in range(len(samples)):
        delayed = buffer[index]
        lpfState = ((delayed * (1.0 - factor)) + (lpfState * factor))
        output[sampleIndex] = lpfState * lpfAmp
        buffer[index] = samples[sampleIndex]
        index = (index + 1) % delayFrames

    return output


@CompileKernel
def MTCombFilter(samples, delayFrames, feedback, factor):
    buffer = np.zeros(delayFrames, dtype = np.float64)
    output = np.empty(len(samples), dtype = np.float64)
    index = 0
    filterState = 0.0

    for sampleIndex in range(len(samples)):
        delayed = buffer[index]
        filterState = ((delayed * (1.0 - factor)) + (filterState * factor))
        output[sampleIndex] = delayed
        buffer[index] = samples[sampleIndex] + (filterState * feedback)
        index = (index + 1) % delayFrames

    return output


@CompileKernel
def MixMTVerb(
        sourceChannels, combOutputs, outLeft, outRight,
        sourceFrames, workingFrames, channels, dry, wet
        ):

    mixedChannels = np.empty((channels, workingFrames), dtype = np.float64)

    for frame in range(workingFrames):
        reverbLeft = 0.0
        reverbRight = 0.0

        for combIndex in range(len(combOutputs)):
            leftIndex = frame - outLeft[combIndex]
            rightIndex = frame - outRight[combIndex]
            if leftIndex >= 0:
                reverbLeft += combOutputs[combIndex, leftIndex]
            if rightIndex >= 0:
                reverbRight += combOutputs[combIndex, rightIndex]

        reverbLeft /= len(combOutputs)
        reverbRight /= len(combOutputs)

        if channels == 1:
            drySample = (sourceChannels[0, frame] if frame < sourceFrames else 0.0)
            wetSample = (reverbLeft + reverbRight) * 0.5
            mixedChannels[0, frame] = ((drySample * dry) + (wetSample * wet))
        else:
            dryLeft = (sourceChannels[0, frame] if frame < sourceFrames else 0.0)
            dryRight = (sourceChannels[1, frame] if frame < sourceFrames else 0.0)
            mixedChannels[0, frame] = ((dryLeft * dry) + (reverbLeft * wet))
            mixedChannels[1, frame] = ((dryRight * dry) + (reverbRight * wet))

    return mixedChannels


__all__ = [
    "NUMBA_AVAILABLE",
    "NUMBA_ENABLED",
    "SetNumbaEnabled",
]
