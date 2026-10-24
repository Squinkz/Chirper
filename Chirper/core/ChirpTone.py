import math
from numbers import Integral, Real

import numpy as np

from . import Easing
from .ChirpConstants import Dynamics, EqualNote, EqualScale, Vibrato


def _ValidateNumber(value, name, allowNone = False):
    if value is None and allowNone:
        return None
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(name + " must be numeric")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(name + " must be finite")
    return value


def _ValidatePositive(value, name, allowNone = False):
    if isinstance(value, PerformanceFrequency):
        if value.value <= 0.0:
            raise ValueError(name + " must be greater than zero")
        return value
    value = _ValidateNumber(value, name, allowNone)
    if value is not None and value <= 0.0:
        raise ValueError(name + " must be greater than zero")
    return value


def _ValidateInteger(value, name, minimum = None):
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise TypeError(name + " must be an integer")
    value = int(value)
    if minimum is not None and value < minimum:
        raise ValueError(name + " must be at least " + str(minimum))
    return value


def _ValidateEasing(easing):
    Easing.Resolve(easing)
    return easing


# -----------------------------------
# Pitch Patterns
# -----------------------------------

class _DynamicsCurve:
    def __init__(self, dynamics, patternName):
        if dynamics is None:
            self.values = None
            return
        if not isinstance(dynamics, list):
            raise TypeError(patternName + " dynamics must be a list")
        if not dynamics:
            raise ValueError(patternName + " dynamics must not be empty")

        values = []
        for value in dynamics:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(patternName + " dynamics must contain only numbers")
            value = float(value)
            if not math.isfinite(value) or value < 0.0:
                raise ValueError(
                    patternName + " dynamics must contain finite nonnegative numbers"
                )
            values.append(value)

        self.values = tuple(values)

    def GetGains(self, count):
        if count <= 0:
            return ()
        if self.values is None:
            return (1.0,) * count
        if len(self.values) == 1 or count == 1:
            return (self.values[0],) * count

        gains = []
        lastControlIndex = len(self.values) - 1
        for gainIndex in range(count):
            controlPosition = gainIndex * lastControlIndex / (count - 1)
            controlIndex = min(int(controlPosition), lastControlIndex - 1)
            position = controlPosition - controlIndex
            startGain = self.values[controlIndex]
            endGain = self.values[controlIndex + 1]

            if position == 0.0:
                gains.append(startGain)
            elif startGain == 0.0 and endGain == 0.0:
                gains.append(0.0)
            elif position == 1.0:
                gains.append(endGain)
            else:
                interpolatedStart = max(startGain, Dynamics.D01)
                interpolatedEnd = max(endGain, Dynamics.D01)
                gains.append(interpolatedStart * ((interpolatedEnd / interpolatedStart) ** position))

        return tuple(gains)


class _PitchPattern:
    def __init__(self, pattern, patternName):
        if not isinstance(pattern, (list, tuple)):
            raise TypeError(patternName + " pattern must be a list")

        values = []
        for value in pattern:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(patternName + " pattern must contain only numbers")
            value = float(value)
            if not math.isfinite(value) or value <= 0.0:
                raise ValueError(
                    patternName + " pattern must contain finite positive numbers"
                )
            values.append(value)

        hasRatios = any(value < 20.0 for value in values)
        hasFrequencies = any(value >= 20.0 for value in values)
        if hasRatios and hasFrequencies:
            raise ValueError(
                patternName + " pattern cannot mix ratios and frequencies"
            )

        self.values = tuple(values)
        self.usesRatios = hasRatios or not hasFrequencies

    def ResolveFrequencies(self, baseFrequency):
        baseFrequency = float(baseFrequency)
        return [
            baseFrequency * value if self.usesRatios else value
            for value in self.values
        ]


class ArpeggioPattern(_PitchPattern):
    def __init__(self, pattern, step, dynamics = None, rotation = 0):
        super().__init__(pattern, "Arpeggio")

        if isinstance(step, bool):
            raise TypeError("Arpeggio step must be numeric")
        try:
            numericStep = float(step)
        except (TypeError, ValueError) as error:
            raise TypeError("Arpeggio step must be numeric") from error
        if not math.isfinite(numericStep) or numericStep <= 0.0:
            raise ValueError("Arpeggio step must be finite and greater than zero")

        self.step = numericStep
        self.dynamics = _DynamicsCurve(dynamics, "Arpeggio")
        if rotation is None:
            rotation = 0
        self.rotation = _ValidateInteger(rotation, "Arpeggio rotation")

    def GetFrequencies(self, baseFrequency):
        if baseFrequency is None:
            return (None,)

        baseFrequency = float(baseFrequency)
        frequencies = self.ResolveFrequencies(baseFrequency)
        startsAtBase = frequencies and math.isclose(
            frequencies[0], baseFrequency, rel_tol = 1e-9, abs_tol = 1e-12
        )
        if not startsAtBase:
            frequencies.insert(0, baseFrequency)

        if frequencies and self.rotation != 0:
            rotation = self.rotation % len(frequencies)
            frequencies = frequencies[rotation:] + frequencies[:rotation]
        return tuple(frequencies)


class _ChordPattern(_PitchPattern):
    def __init__(self, pattern, roll = 0.0, dynamics = None, inversion = 0):
        super().__init__(pattern, "Chord")

        if inversion is None:
            inversion = 0
        self.inversion = _ValidateInteger(inversion, "Chord inversion")

        if isinstance(roll, bool):
            raise TypeError("Chord roll must be numeric")
        try:
            numericRoll = float(roll)
        except (TypeError, ValueError) as error:
            raise TypeError("Chord roll must be numeric") from error
        if not math.isfinite(numericRoll):
            raise ValueError("Chord roll must be finite")
        self.roll = numericRoll
        self.dynamics = _DynamicsCurve(dynamics, "Chord")

    def ApplyInversion(self, frequencies):
        frequencies = list(frequencies)
        if not frequencies or self.inversion == 0:
            return frequencies

        octaveCount, rotation = divmod(abs(self.inversion), len(frequencies))
        octaveShift = octaveCount if self.inversion > 0 else -octaveCount
        shifted = []
        for frequency in frequencies:
            try:
                frequency = math.ldexp(float(frequency), octaveShift)
            except OverflowError as error:
                raise ValueError(
                    "Chord inversion produces frequencies outside the numeric range"
                ) from error
            if not math.isfinite(frequency) or frequency <= 0.0:
                raise ValueError(
                    "Chord inversion produces frequencies outside the numeric range"
                )
            shifted.append(frequency)

        if rotation == 0:
            return shifted

        if self.inversion > 0:
            moved = [frequency * 2.0 for frequency in shifted[:rotation]]
            shifted = shifted[rotation:] + moved
        else:
            moved = [frequency * 0.5 for frequency in shifted[-rotation:]]
            shifted = moved + shifted[:-rotation]

        if any(not math.isfinite(frequency) or frequency <= 0.0 for frequency in shifted):
            raise ValueError(
                "Chord inversion produces frequencies outside the numeric range"
            )
        return shifted

    def GetFrequencies(self, baseFrequency):
        if baseFrequency is None:
            return (None,)

        baseFrequency = float(baseFrequency)
        frequencies = [baseFrequency]
        for frequency in self.ResolveFrequencies(baseFrequency):
            if any(
                    math.isclose(
                        frequency, existingFrequency,
                        rel_tol = 1e-9, abs_tol = 1e-12
                    )
                    for existingFrequency in frequencies
                    ):
                continue
            frequencies.append(frequency)
        if self.inversion != 0:
            frequencies.sort()
        frequencies = self.ApplyInversion(frequencies)

        uniqueFrequencies = []
        for frequency in frequencies:
            if any(
                    math.isclose(
                        frequency, existingFrequency,
                        rel_tol = 1e-9, abs_tol = 1e-12
                    )
                    for existingFrequency in uniqueFrequencies
                    ):
                continue
            uniqueFrequencies.append(frequency)
        return tuple(uniqueFrequencies)


# -----------------------------------
# Performance Frequency
# -----------------------------------

class PerformanceFrequency:
    def __init__(
            self, value, bend = None, bendEasing = "linear",
            bendStepped = False, bendRatios = None, duration = 0.0,
            bendIn = None, bendInDuration = 0.0, bendInEasing = "linear",
            bendOut = None, bendOutDuration = 0.0, bendOutEasing = "linear",
            offset = 0.0,
            portamentoStart = None, portamentoDuration = 0.0,
            trill = None, trillLength = 0.0,
            vibratoEnabled = False, vibratoDepth = None,
            vibratoRate = None, vibratoWave = None,
            operations = None
            ):
        self.baseValue = _ValidateNumber(value, "frequency")
        self.bend = _ValidatePositive(bend, "bend", allowNone = True)
        self.bendEasing = _ValidateEasing(bendEasing)
        if not isinstance(bendStepped, bool):
            raise TypeError("bendStepped must be a boolean")
        self.bendStepped = bendStepped

        if bendRatios is None:
            self.bendRatios = None
        else:
            if isinstance(bendRatios, (str, bytes)):
                raise TypeError("bendRatios must be a list of numbers")
            try:
                bendRatios = tuple(bendRatios)
            except TypeError as error:
                raise TypeError("bendRatios must be a list of numbers") from error

            normalizedRatios = []
            for ratio in bendRatios:
                normalizedRatios.append(_ValidatePositive(ratio, "bend ratio"))
            self.bendRatios = tuple(normalizedRatios)

        self.duration = max(0.0, _ValidateNumber(duration, "duration"))
        self.bendIn = _ValidatePositive(bendIn, "bendIn", allowNone = True)
        self.bendInDuration = max(
            0.0, _ValidateNumber(bendInDuration, "bendInDuration")
        )
        self.bendInEasing = _ValidateEasing(bendInEasing)
        self.bendOut = _ValidatePositive(bendOut, "bendOut", allowNone = True)
        self.bendOutDuration = max(
            0.0, _ValidateNumber(bendOutDuration, "bendOutDuration")
        )
        self.bendOutEasing = _ValidateEasing(bendOutEasing)
        self.offset = max(0.0, _ValidateNumber(offset, "offset"))
        self.portamentoStart = _ValidatePositive(
            portamentoStart, "portamentoStart", allowNone = True
        )
        self.portamentoDuration = max(
            0.0, _ValidateNumber(portamentoDuration, "portamentoDuration")
        )
        self.trill = _ValidatePositive(trill, "trill", allowNone = True)
        self.trillLength = max(
            0.0,
            _ValidateNumber(
                0.0 if trillLength is None else trillLength,
                "trillLength"
            )
        )
        if not isinstance(vibratoEnabled, bool):
            raise TypeError("vibratoEnabled must be a boolean")
        self.vibratoEnabled = vibratoEnabled
        self.vibratoDepth = _ValidateNumber(
            vibratoDepth, "vibratoDepth", allowNone = True
        )
        self.vibratoRate = _ValidateNumber(
            vibratoRate, "vibratoRate", allowNone = True
        )
        self.vibratoWave = vibratoWave
        self.operations = [] if operations is None else list(operations)

    @staticmethod
    def GetStepBendRatios(startFreq, targetFreq, ratios = None):
        if startFreq <= 0.0 or targetFreq <= 0.0:
            return (1.0,)

        if ratios is None:
            ratios = EqualScale.CHROMATIC
        baseRatios = {1.0}
        for ratio in ratios:
            ratio = float(ratio)
            if math.isfinite(ratio) and ratio >= 1.0:
                baseRatios.add(ratio)
        baseRatios = sorted(baseRatios)
        ratioLimit = max(startFreq, targetFreq) / min(startFreq, targetFreq)
        expandedRatios = []
        octaveMultiplier = 1.0
        tolerance = 1e-4

        while octaveMultiplier <= ratioLimit * (1.0 + tolerance):
            for ratio in baseRatios:
                expandedRatio = ratio * octaveMultiplier
                if expandedRatio > ratioLimit * (1.0 + tolerance):
                    break
                if expandedRatios and expandedRatio < expandedRatios[-1]:
                    continue
                if (
                        expandedRatios
                        and math.isclose(
                            expandedRatio, expandedRatios[-1],
                            rel_tol = tolerance
                        )
                        ):
                    continue
                expandedRatios.append(expandedRatio)

            nextMultiplier = octaveMultiplier * 2.0
            if not math.isfinite(nextMultiplier) or nextMultiplier <= octaveMultiplier:
                break
            octaveMultiplier = nextMultiplier

        return tuple(expandedRatios or [1.0])

    @staticmethod
    def GetStepBendTarget(startFreq, targetFreq, ratios = None):
        bendRatios = PerformanceFrequency.GetStepBendRatios(
            startFreq, targetFreq, ratios
        )
        if targetFreq >= startFreq:
            return startFreq * bendRatios[-1]
        return startFreq / bendRatios[-1]

    @property
    def value(self):
        return self.Resolve(self.baseValue)

    def Resolve(self, value):
        value = float(value)
        for operation, operand in self.operations:
            if operation == "multiply":
                value *= operand
            elif operation == "divide":
                value /= operand
            elif operation == "add":
                value += operand
            elif operation == "subtract":
                value -= operand
            elif operation == "reverseSubtract":
                value = operand - value
            elif operation == "reverseDivide":
                value = operand / value

        return value

    def ResolveTarget(self, target, isNoise = False):
        if target is None:
            return None

        target = float(target)
        if not isNoise and 0.0 < target < 20.0:
            return self.Resolve(self.baseValue * target)
        return self.Resolve(target)

    def ResolveBend(self, isNoise = False):
        return self.ResolveTarget(self.bend, isNoise)

    def ResolveBendIn(self, isNoise = False):
        return self.ResolveTarget(self.bendIn, isNoise)

    def ResolveBendOut(self, isNoise = False):
        return self.ResolveTarget(self.bendOut, isNoise)

    def GetBendFrequency(self, frameOffset, sampleRate, isNoise = False):
        frameOffset = _ValidateInteger(frameOffset, "frameOffset", 0)
        sampleRate = _ValidatePositive(sampleRate, "sampleRate")
        startFreq = self.value
        bendFrame = round(self.offset * sampleRate) + frameOffset
        bendFrames = max(0, int(sampleRate * self.duration))

        bendTarget = self.ResolveBend(isNoise)
        if bendTarget is not None:
            progress = min(1.0, bendFrame / max(1, bendFrames - 1))
            progress = Easing.Apply(progress, self.bendEasing)
            if self.bendStepped:
                ratios = self.GetStepBendRatios(
                    startFreq, bendTarget, self.bendRatios
                )
                ratioIndex = math.floor(len(ratios) * progress)
                ratioIndex = max(0, min(len(ratios) - 1, ratioIndex))
                if bendTarget >= startFreq:
                    return startFreq * ratios[ratioIndex]
                return startFreq / ratios[ratioIndex]

            return startFreq + ((bendTarget - startFreq) * progress)

        bendInDuration = self.bendInDuration if self.bendIn is not None else 0.0
        bendOutDuration = self.bendOutDuration if self.bendOut is not None else 0.0
        scopedDuration = bendInDuration + bendOutDuration
        if scopedDuration > self.duration and scopedDuration > 0.0:
            durationScale = self.duration / scopedDuration
            bendInDuration *= durationScale
            bendOutDuration *= durationScale

        bendInFrames = max(0, int(sampleRate * bendInDuration))
        bendOutFrames = max(0, int(sampleRate * bendOutDuration))
        bendOutStart = max(0, bendFrames - bendOutFrames)
        bendStart = self.ResolveBendIn(isNoise)
        if bendStart is not None and bendFrame < bendInFrames:
            progress = min(1.0, bendFrame / max(1, bendInFrames - 1))
            progress = Easing.Apply(progress, self.bendInEasing)
            return bendStart + ((startFreq - bendStart) * progress)

        bendTarget = self.ResolveBendOut(isNoise)
        if bendTarget is not None and bendFrame >= bendOutStart:
            progress = 1.0 if bendOutFrames == 1 else min(
                1.0, (bendFrame - bendOutStart) / max(1, bendOutFrames - 1)
            )
            progress = Easing.Apply(progress, self.bendOutEasing)
            return startFreq + ((bendTarget - startFreq) * progress)

        return startFreq

    def GetFrequencyTrack(
            self, frameCount, sampleRate, oscillator = None,
            defaultVibratoDepth = Vibrato.LIGHT,
            defaultVibratoRate = 6.0,
            defaultVibratoWave = "Sine"
            ):
        frameCount = _ValidateInteger(frameCount, "frameCount", 0)
        sampleRate = _ValidatePositive(sampleRate, "sampleRate")
        if frameCount == 0:
            return np.empty(0, dtype = np.float64)

        startFreq = self.value
        frequencies = np.full(frameCount, startFreq, dtype = np.float64)

        portamentoStart = self.ResolvePortamentoStart()
        if (
                portamentoStart is not None
                and portamentoStart > 0.0
                and self.portamentoDuration > 0.0
                and startFreq > 0.0
                ):
            portamentoFrames = max(0, int(sampleRate * self.portamentoDuration))
            portamentoDivisor = max(1, portamentoFrames - 1)
            for frame in range(frameCount):
                progress = min(1.0, frame / portamentoDivisor)
                portamentoFreq = portamentoStart * (
                    (startFreq / portamentoStart) ** progress
                )
                frequencies[frame] *= portamentoFreq / startFreq

        bendTarget = self.ResolveBend()
        bendOffsetFrames = round(self.offset * sampleRate)
        bendFrames = max(0, int(sampleRate * self.duration))
        bendDivisor = max(1, bendFrames - 1)
        if bendTarget is not None:
            easingFunction = Easing.Resolve(self.bendEasing)
            bendRatios = None
            if self.bendStepped:
                bendRatios = self.GetStepBendRatios(
                    startFreq, bendTarget, self.bendRatios
                )

            for frame in range(frameCount):
                bendFrame = bendOffsetFrames + frame
                progress = min(1.0, bendFrame / bendDivisor)
                progress = Easing.ApplyResolved(progress, easingFunction)
                if bendRatios is not None:
                    progress = max(0.0, min(1.0, progress))
                    ratioIndex = math.floor(len(bendRatios) * progress)
                    ratioIndex = max(0, min(len(bendRatios) - 1, ratioIndex))
                    if bendTarget >= startFreq:
                        currentFreq = startFreq * bendRatios[ratioIndex]
                    else:
                        currentFreq = startFreq / bendRatios[ratioIndex]
                else:
                    currentFreq = startFreq + (
                        (bendTarget - startFreq) * progress
                    )
                frequencies[frame] *= currentFreq / startFreq
        elif self.bendIn is not None or self.bendOut is not None:
            bendInDuration = self.bendInDuration if self.bendIn is not None else 0.0
            bendOutDuration = self.bendOutDuration if self.bendOut is not None else 0.0
            scopedDuration = bendInDuration + bendOutDuration
            if scopedDuration > self.duration and scopedDuration > 0.0:
                durationScale = self.duration / scopedDuration
                bendInDuration *= durationScale
                bendOutDuration *= durationScale

            bendInFrames = max(0, int(sampleRate * bendInDuration))
            bendInDivisor = max(1, bendInFrames - 1)
            bendOutFrames = max(0, int(sampleRate * bendOutDuration))
            bendOutStart = max(0, bendFrames - bendOutFrames)
            bendOutDivisor = max(1, bendOutFrames - 1)
            bendInTarget = self.ResolveBendIn()
            bendOutTarget = self.ResolveBendOut()
            bendInEasing = (
                None if bendInTarget is None else Easing.Resolve(self.bendInEasing)
            )
            bendOutEasing = (
                None if bendOutTarget is None else Easing.Resolve(self.bendOutEasing)
            )

            for frame in range(frameCount):
                bendFrame = bendOffsetFrames + frame
                currentFreq = startFreq
                if bendInTarget is not None and bendFrame < bendInFrames:
                    progress = min(1.0, bendFrame / bendInDivisor)
                    progress = Easing.ApplyResolved(progress, bendInEasing)
                    currentFreq = bendInTarget + (
                        (startFreq - bendInTarget) * progress
                    )
                elif bendOutTarget is not None and bendFrame >= bendOutStart:
                    progress = 1.0 if bendOutFrames == 1 else min(
                        1.0, (bendFrame - bendOutStart) / bendOutDivisor
                    )
                    progress = Easing.ApplyResolved(progress, bendOutEasing)
                    currentFreq = startFreq + (
                        (bendOutTarget - startFreq) * progress
                    )
                frequencies[frame] *= currentFreq / startFreq

        trillTarget = self.ResolveTrill()
        if trillTarget is not None and self.trillLength > 0.0 and startFreq > 0.0:
            trillFrames = max(1, int(sampleRate * self.trillLength))
            gateFrames = max(0, int(sampleRate * self.duration))
            offsetFrames = round(self.offset * sampleRate)
            for frame in range(frameCount):
                trillFrame = min(offsetFrames + frame, max(0, gateFrames - 1))
                if (trillFrame // trillFrames) % 2 == 1:
                    frequencies[frame] *= trillTarget / startFreq

        if self.vibratoEnabled:
            if oscillator is None:
                from .ChirpOscillator import ChirpOscillator
                oscillator = ChirpOscillator(sampleRate = int(sampleRate))

            depth = (
                defaultVibratoDepth
                if self.vibratoDepth is None else self.vibratoDepth
            )
            rate = (
                defaultVibratoRate
                if self.vibratoRate is None else self.vibratoRate
            )
            wave = (
                defaultVibratoWave
                if self.vibratoWave is None else self.vibratoWave
            )
            wave = oscillator.GetWave(wave)
            phaseIncrement = (2.0 * math.pi * rate) / sampleRate
            phase = 2.0 * math.pi * rate * self.offset
            for frame in range(frameCount):
                cents = oscillator.GetLfoValue(
                    wave, phase, phaseIncrement
                ) * depth
                frequencies[frame] *= 2.0 ** (cents / 1200.0)
                phase += phaseIncrement

        return frequencies

    def ResolvePortamentoStart(self, isNoise = False):
        if isNoise or self.portamentoStart is None:
            return None
        return self.Resolve(self.portamentoStart)

    def ResolveTrill(self, isNoise = False):
        if isNoise:
            return None
        return self.ResolveTarget(self.trill)

    def WithOperation(self, operation, operand):
        if isinstance(operand, bool) or not isinstance(operand, Real):
            return NotImplemented
        operand = float(operand)
        if not math.isfinite(operand):
            raise ValueError("Frequency operand must be finite")
        if operation == "divide" and operand == 0.0:
            raise ZeroDivisionError("Frequency division by zero")

        operations = self.operations + [(operation, operand)]
        return PerformanceFrequency(
            self.baseValue,
            bend = self.bend,
            bendEasing = self.bendEasing,
            bendStepped = self.bendStepped,
            bendRatios = self.bendRatios,
            duration = self.duration,
            bendIn = self.bendIn,
            bendInDuration = self.bendInDuration,
            bendInEasing = self.bendInEasing,
            bendOut = self.bendOut,
            bendOutDuration = self.bendOutDuration,
            bendOutEasing = self.bendOutEasing,
            offset = self.offset,
            portamentoStart = self.portamentoStart,
            portamentoDuration = self.portamentoDuration,
            trill = self.trill,
            trillLength = self.trillLength,
            vibratoEnabled = self.vibratoEnabled,
            vibratoDepth = self.vibratoDepth,
            vibratoRate = self.vibratoRate,
            vibratoWave = self.vibratoWave,
            operations = operations
        )

    def __float__(self):
        return self.value

    def __lt__(self, operand):
        if isinstance(operand, bool) or not isinstance(operand, Real):
            return NotImplemented
        return self.value < float(operand)

    def __le__(self, operand):
        if isinstance(operand, bool) or not isinstance(operand, Real):
            return NotImplemented
        return self.value <= float(operand)

    def __eq__(self, operand):
        if isinstance(operand, bool) or not isinstance(operand, Real):
            return NotImplemented
        return self.value == float(operand)

    def __gt__(self, operand):
        if isinstance(operand, bool) or not isinstance(operand, Real):
            return NotImplemented
        return self.value > float(operand)

    def __ge__(self, operand):
        if isinstance(operand, bool) or not isinstance(operand, Real):
            return NotImplemented
        return self.value >= float(operand)

    def __mul__(self, operand):
        return self.WithOperation("multiply", operand)

    def __rmul__(self, operand):
        return self.WithOperation("multiply", operand)

    def __truediv__(self, operand):
        return self.WithOperation("divide", operand)

    def __rtruediv__(self, operand):
        return self.WithOperation("reverseDivide", operand)

    def __add__(self, operand):
        return self.WithOperation("add", operand)

    def __radd__(self, operand):
        return self.WithOperation("add", operand)

    def __sub__(self, operand):
        return self.WithOperation("subtract", operand)

    def __rsub__(self, operand):
        return self.WithOperation("reverseSubtract", operand)


Real.register(PerformanceFrequency)


# -----------------------------------
# Tone Class
# -----------------------------------

class Tone:
    def __init__(self, freq = EqualNote.C4, duration = 0.25, amplitude = 1.0):
        self.performanceFrequency = freq if isinstance(freq, PerformanceFrequency) else None
        self.freq = freq.value if self.performanceFrequency is not None else _ValidateNumber(
            freq, "freq", allowNone = True
        )
        self.duration = _ValidateNumber(duration, "duration")
        self.amplitude = _ValidateNumber(amplitude, "amplitude")
        self.wave = None
        self.vibratoEnabled = False
        self.vibratoDepth = None
        self.vibratoRate = None
        self.vibratoWave = None
        self.modEnabled = False
        self.modFreq = None
        self.modDepth = 1.0
        self.modWave = "Sine"
        self.tremoloEnabled = False
        self.tremoloDepth = None
        self.tremoloRate = None
        self.tremoloWave = None
        self.pan = 0.0
        self.autoPanEnabled = False
        self.autoPanDepth = 1.0
        self.autoPanRate = 1.0
        self.autoPanWave = "Sine"
        self.autoPanOffset = 0.0
        self.phaseDegrees = None
        self.bend = None
        self.bendEasing = "linear"
        self.bendInTarget = None
        self.bendInDuration = 0.0
        self.bendInEasing = "linear"
        self.bendOutTarget = None
        self.bendOutDuration = 0.0
        self.bendOutEasing = "linear"
        self.fadeTarget = None
        self.fadeEasing = "linear"
        self.fadeInDuration = 0.0
        self.fadeInEasing = "linear"
        self.fadeOutDuration = 0.0
        self.fadeOutEasing = "linear"
        self.unisonVoices = 1
        self.unisonDetune = 0.0
        self.unisonSpread = 0.0
        self.arpeggio = None

    def Wave(self, wave):
        self.wave = wave
        return self

    def Vibrato(self, depth = None, rate = None, wave = None):
        self.vibratoEnabled = True
        self.vibratoDepth = _ValidateNumber(depth, "depth", allowNone = True)
        self.vibratoRate = _ValidateNumber(rate, "rate", allowNone = True)
        self.vibratoWave = wave
        return self

    def Tremolo(self, depth = None, rate = None, wave = None):
        self.tremoloEnabled = True
        self.tremoloDepth = _ValidateNumber(depth, "depth", allowNone = True)
        self.tremoloRate = _ValidateNumber(rate, "rate", allowNone = True)
        self.tremoloWave = wave
        return self

    def Mod(self, freq, depth = 1.0, wave = "Sine"):
        self.modEnabled = True
        self.modFreq = _ValidateNumber(freq, "freq")
        self.modDepth = _ValidateNumber(depth, "depth")
        self.modWave = wave
        return self

    def Pan(self, amount):
        amount = _ValidateNumber(amount, "amount")
        self.pan = max(-1.0, min(1.0, amount))
        return self

    def AutoPan(self, depth = 1.0, rate = 1.0, wave = "Sine", offset = 0.0):
        self.autoPanEnabled = True
        self.autoPanDepth = _ValidateNumber(depth, "depth")
        self.autoPanRate = _ValidateNumber(rate, "rate")
        self.autoPanWave = wave
        self.autoPanOffset = _ValidateNumber(offset, "offset")
        return self

    def Phase(self, degrees):
        self.phaseDegrees = _ValidateNumber(degrees, "degrees")
        return self

    def Bend(self, target, easing = "linear"):
        self.bend = _ValidatePositive(target, "target")
        self.bendEasing = _ValidateEasing(easing)
        self.bendInTarget = None
        self.bendInDuration = 0.0
        self.bendOutTarget = None
        self.bendOutDuration = 0.0
        return self

    def BendIn(self, start, duration, easing = "linear"):
        self.bendInTarget = _ValidatePositive(start, "start")
        self.bendInDuration = max(0.0, _ValidateNumber(duration, "duration"))
        self.bendInEasing = _ValidateEasing(easing)
        self.bend = None
        return self

    def BendOut(self, target, duration, easing = "linear"):
        self.bendOutTarget = _ValidatePositive(target, "target")
        self.bendOutDuration = max(0.0, _ValidateNumber(duration, "duration"))
        self.bendOutEasing = _ValidateEasing(easing)
        self.bend = None
        return self

    def Arpeggio(self, pattern, step = 0.125, dynamics = None, rotation = 0):
        self.arpeggio = ArpeggioPattern(pattern, step, dynamics, rotation)
        return self

    def Fade(self, target, easing = "linear"):
        self.fadeTarget = _ValidateNumber(target, "target")
        self.fadeEasing = _ValidateEasing(easing)
        return self

    def FadeIn(self, duration, easing = "linear"):
        self.fadeInDuration = max(0.0, _ValidateNumber(duration, "duration"))
        self.fadeInEasing = _ValidateEasing(easing)
        return self

    def FadeOut(self, duration, easing = "linear"):
        self.fadeOutDuration = max(0.0, _ValidateNumber(duration, "duration"))
        self.fadeOutEasing = _ValidateEasing(easing)
        return self

    def Unison(self, voices = 3, detune = 10.0, spread = 1.0):
        self.unisonVoices = _ValidateInteger(voices, "voices", 1)
        self.unisonDetune = _ValidateNumber(detune, "detune")
        self.unisonSpread = _ValidateNumber(spread, "spread")
        return self

    @staticmethod
    def Rest(duration):
        return Tone(None, duration, 0.0)


# -----------------------------------
# Control Commands
# -----------------------------------

class Control:
    pass


class Wave(Control):
    def __init__(self, wave):
        self.wave = wave


class Pitch(Control):
    def __init__(self, amount):
        self.amount = _ValidateNumber(amount, "Pitch amount")


class Tempo(Control):
    def __init__(self, bpm):
        self.bpm = _ValidateNumber(bpm, "Tempo")
        if self.bpm <= 0.0:
            raise ValueError("Tempo must be greater than zero")


class Seconds(Control):
    pass


class VibratoDepth(Control):
    def __init__(self, depth):
        self.depth = _ValidateNumber(depth, "VibratoDepth")


class VibratoRate(Control):
    def __init__(self, rate):
        self.rate = _ValidateNumber(rate, "VibratoRate")


class VibratoWave(Control):
    def __init__(self, wave):
        self.wave = wave


class TremoloDepth(Control):
    def __init__(self, depth):
        self.depth = _ValidateNumber(depth, "TremoloDepth")


class TremoloRate(Control):
    def __init__(self, rate):
        self.rate = _ValidateNumber(rate, "TremoloRate")


class TremoloWave(Control):
    def __init__(self, wave):
        self.wave = wave


class Insert(Control):
    def __init__(self, sound):
        self.sound = sound

__all__ = [
    "Tone",
    "Control",
    "Wave",
    "Pitch",
    "Tempo",
    "Seconds",
    "VibratoDepth",
    "VibratoRate",
    "VibratoWave",
    "TremoloDepth",
    "TremoloRate",
    "TremoloWave",
    "Insert",
]
