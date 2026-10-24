import copy
import math
from numbers import Integral
import operator
import warnings
from fractions import Fraction

import numpy as np

from ..core.ChirpConstants import EqualScale, NoteLength, Tremolo
from ..core.ChirpDSP import ChirpDSP
from ..core.ChirpTone import (
    _ChordPattern, _ValidateEasing, _ValidateNumber, _ValidatePositive,
    ArpeggioPattern, PerformanceFrequency, Tempo
)
from .ChirpPatch import Patch
from .ChirpSchedule import ScheduledNote, SequenceSegment


class Meter:
    def __init__(self, beats, unit):
        if isinstance(beats, bool) or isinstance(unit, bool):
            raise TypeError("Meter values must be integers")

        try:
            beats = Fraction(str(beats))
            unit = Fraction(str(unit))
        except (TypeError, ValueError, ZeroDivisionError) as error:
            raise TypeError("Meter values must be integers") from error

        if beats.denominator != 1 or unit.denominator != 1:
            raise ValueError("Meter values must be integers")
        if beats <= 0 or unit <= 0:
            raise ValueError("Meter values must be greater than zero")

        self.beats = int(beats)
        self.unit = int(unit)


class SetPatch:
    def __init__(self, patch, balance = 0.0, polyphonic = None, portamento = None):
        if not isinstance(patch, Patch):
            raise TypeError("SetPatch expects a Patch")
        if polyphonic is not None and not isinstance(polyphonic, bool):
            raise TypeError("polyphonic must be a boolean or None")
        if portamento is not None and not isinstance(portamento, bool):
            raise TypeError("portamento must be a boolean or None")

        self.patch = patch
        self.balance = Patch.ValidateBalance(balance)
        self.polyphonic = patch.polyphonic if polyphonic is None else polyphonic
        self.portamento = patch.portamento if portamento is None else portamento


class Note:
    def __init__(self, bar, beat, freq, duration, amplitude = 1.0):
        self.bar = _ValidateNumber(bar, "bar")
        self.beat = _ValidateNumber(beat, "beat")
        self.freq = _ValidatePositive(freq, "freq")
        self.duration = _ValidateNumber(duration, "duration")
        self.amplitude = _ValidateNumber(amplitude, "amplitude")
        self.bend = None
        self.bendEasing = "linear"
        self.bendStepped = False
        self.bendRatios = None
        self.bendInTarget = None
        self.bendInDuration = 0.0
        self.bendInEasing = "linear"
        self.bendOutTarget = None
        self.bendOutDuration = 0.0
        self.bendOutEasing = "linear"
        self.trillTarget = None
        self.trillLength = None
        self.pan = 0.0
        self.autoPanEnabled = False
        self.autoPanDepth = 1.0
        self.autoPanRate = 1.0
        self.autoPanWave = "Sine"
        self.autoPanOffset = 0.0
        self.fadeTarget = None
        self.fadeEasing = "linear"
        self.fadeInDuration = 0.0
        self.fadeInEasing = "linear"
        self.fadeOutDuration = 0.0
        self.fadeOutEasing = "linear"
        self.vibratoEnabled = False
        self.vibratoDepth = None
        self.vibratoRate = None
        self.vibratoWave = None
        self.tremoloEnabled = False
        self.tremoloDepth = None
        self.tremoloRate = None
        self.tremoloWave = None
        self.chord = None
        self.arpeggio = None

    def Bend(self, target, easing = "linear"):
        self.bend = _ValidatePositive(target, "target")
        self.bendEasing = _ValidateEasing(easing)
        self.bendStepped = False
        self.bendRatios = None
        self.bendInTarget = None
        self.bendInDuration = 0.0
        self.bendOutTarget = None
        self.bendOutDuration = 0.0
        return self

    def StepBend(self, target, ratios = None, easing = "linear"):
        if ratios is None:
            ratios = EqualScale.CHROMATIC
        if isinstance(ratios, (str, bytes)):
            raise TypeError("ratios must be a list of numbers")

        try:
            ratios = list(ratios)
        except TypeError as error:
            raise TypeError("ratios must be a list of numbers") from error

        normalizedRatios = [1.0]
        for ratio in ratios:
            if isinstance(ratio, bool) or not isinstance(ratio, (int, float)):
                raise TypeError("ratios must contain only numbers")
            ratio = float(ratio)
            if not math.isfinite(ratio) or ratio <= 0.0:
                raise ValueError("ratios must contain finite positive numbers")
            if ratio >= 1.0:
                normalizedRatios.append(ratio)

        self.bend = _ValidatePositive(target, "target")
        self.bendEasing = _ValidateEasing(easing)
        self.bendStepped = True
        self.bendRatios = tuple(sorted(set(normalizedRatios)))
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
        self.bendStepped = False
        self.bendRatios = None
        return self

    def BendOut(self, target, duration, easing = "linear"):
        self.bendOutTarget = _ValidatePositive(target, "target")
        self.bendOutDuration = max(0.0, _ValidateNumber(duration, "duration"))
        self.bendOutEasing = _ValidateEasing(easing)
        self.bend = None
        self.bendStepped = False
        self.bendRatios = None
        return self

    def Trill(self, target, length = NoteLength.L32):
        if isinstance(target, bool) or not isinstance(target, (int, float)):
            raise TypeError("Trill target must be numeric")
        if not math.isfinite(target) or target <= 0.0:
            raise ValueError("Trill target must be finite and greater than zero")

        self.trillTarget = float(target)
        self.trillLength = _ValidatePositive(length, "length")
        return self

    def Chord(self, pattern, roll = 0.0, dynamics = None, inversion = 0):
        self.chord = _ChordPattern(pattern, roll, dynamics, inversion)
        self.arpeggio = None
        return self

    def Arpeggio(self, pattern, step = NoteLength.L16, dynamics = None, rotation = 0):
        self.arpeggio = ArpeggioPattern(pattern, step, dynamics, rotation)
        self.chord = None
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


class Sequence:
    SAMPLE_RATE = 44100

    def __init__(self, events = None):
        self.events = [] if events is None else list(events)
        self._start = None
        self._end = None
        self._components = None
        self._repeat = 1

# -----------------------------------
# Sequence Composition
# -----------------------------------

    def CopyStructure(self, deep = False):
        if not deep or self._components is None:
            copied = Sequence()
            copied.events = [copy.copy(event) for event in self.events]
            copied._components = self._components
            copied._repeat = self._repeat
            copied._start = copy.copy(self._start)
            copied._end = copy.copy(self._end)
            return copied

        copies = {}
        stack = [(self, False)]
        while stack:
            sequence, visited = stack.pop()
            sequenceId = id(sequence)
            if sequenceId in copies:
                continue
            if not visited and sequence._components is not None:
                stack.append((sequence, True))
                for component in sequence._components:
                    if id(component) not in copies:
                        stack.append((component, False))
                continue

            copied = Sequence([copy.copy(event) for event in sequence.events])
            if sequence._components is not None:
                copied._components = tuple(
                    copies[id(component)] for component in sequence._components
                )
            copied._repeat = sequence._repeat
            copied._start = copy.copy(sequence._start)
            copied._end = copy.copy(sequence._end)
            copies[sequenceId] = copied

        return copies[id(self)]

    def Start(self, bar, beat):
        selected = self.CopyStructure()
        selected._start = (bar, beat)
        return selected

    def End(self, bar, beat):
        selected = self.CopyStructure()
        selected._end = (bar, beat)
        return selected

    def FirstBar(self):
        return self._GetOccupiedBarRange()[0]

    def LastBar(self):
        return self._GetOccupiedBarRange()[1]

    def Trim(self):
        firstBar, lastBar = self._GetOccupiedBarRange()
        if firstBar is None:
            return Sequence()

        selected = Sequence()
        selected._components = (self.CopyStructure(),)
        selected._start = (firstBar, 0)
        selected._end = (lastBar + 1, 0)
        return selected

    def Gain(self, amount):
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise TypeError("Sequence gain must be numeric")
        if not math.isfinite(amount):
            raise ValueError("Sequence gain must be finite")
        if amount < 0.0:
            raise ValueError("Sequence gain cannot be negative")

        gained = self.CopyStructure(deep = True)
        sequences = [gained]
        while sequences:
            sequence = sequences.pop()
            if sequence._components is not None:
                sequences.extend(sequence._components)
                continue

            for event in sequence.events:
                if not isinstance(event, Note):
                    continue
                event.amplitude *= amount
                if event.fadeTarget is not None:
                    event.fadeTarget *= amount

        return gained

    def __add__(self, other):
        if not isinstance(other, Sequence):
            return NotImplemented

        combined = Sequence()
        left = self if self._components is not None else self.CopyStructure()
        right = other if other._components is not None else other.CopyStructure()
        combined._components = (left, right)
        return combined

    def __mul__(self, count):
        if isinstance(count, bool) or not isinstance(count, int):
            return NotImplemented

        repeated = Sequence()
        source = self if self._components is not None else self.CopyStructure()
        repeated._components = (source,)
        repeated._repeat = max(0, count)
        return repeated

    def __rmul__(self, count):
        return self * count

# -----------------------------------
# Musical Time
# -----------------------------------

    def GetFraction(self, value, name):
        if isinstance(value, bool):
            raise TypeError(name + " must be numeric")

        try:
            value = Fraction(str(value))
        except (TypeError, ValueError, ZeroDivisionError) as error:
            raise TypeError(name + " must be numeric") from error

        return value

    def GetNotePositionWholeNotes(self, bar, beat, meter):
        bar = self.GetFraction(bar, "Bar")
        beat = self.GetFraction(beat, "Beat")
        if bar.denominator != 1:
            raise ValueError("Bar must be an integer")
        if bar < 0 or beat < 0 or beat >= meter.beats:
            return None

        return ((bar * meter.beats) + beat) / meter.unit

    def GetSelectionPosition(self, position, name, segments):
        if not isinstance(position, (tuple, list)) or len(position) != 2:
            raise TypeError(name + " must be a (bar, beat) pair")

        bar = self.GetFraction(position[0], name + " bar")
        beat = self.GetFraction(position[1], name + " beat")
        if bar.denominator != 1:
            raise ValueError(name + " bar must be an integer")

        bar = max(Fraction(0), bar)
        beat = max(Fraction(0), beat)
        remainingBars = int(bar)
        meter = Meter(4, 4) if not segments else segments[-1].meter

        for index, segment in enumerate(segments):
            meter = segment.meter
            barLength = Fraction(meter.beats, meter.unit)
            span = segment.end - segment.start
            barCount = math.ceil(span / barLength) if span > 0 else 0
            if remainingBars >= barCount:
                remainingBars -= barCount
                continue

            if beat >= meter.beats:
                raise ValueError(
                    name + " beat must be less than " + str(meter.beats)
                    + " for Meter(" + str(meter.beats) + ", "
                    + str(meter.unit) + ")"
                )

            offset = (remainingBars * barLength) + (beat / meter.unit)
            if offset > span:
                raise ValueError(name + " falls beyond the end of a partial bar")

            sourcePosition = segment.start + offset
            if sourcePosition == segment.end:
                return index + 1, None, (bar, beat)
            return index, sourcePosition, (bar, beat)

        if beat >= meter.beats:
            raise ValueError(
                name + " beat must be less than " + str(meter.beats)
                + " for Meter(" + str(meter.beats) + ", "
                + str(meter.unit) + ")"
            )
        return len(segments), None, (bar, beat)

    def GetDurationWholeNotes(self, duration):
        return max(Fraction(0), self.GetFraction(duration, "Duration"))

    def GetDurationSeconds(self, duration, tempo):
        return float(self.GetDurationWholeNotes(duration)) * (4.0 * (60.0 / tempo))

    def GetTiming(self):
        tempoCommands = [event for event in self.events if isinstance(event, Tempo)]
        meterCommands = [event for event in self.events if isinstance(event, Meter)]
        if len(tempoCommands) > 1:
            raise ValueError("Sequence may only contain one Tempo command")
        if len(meterCommands) > 1:
            raise ValueError("Sequence may only contain one Meter command")

        tempo = 120.0
        if tempoCommands:
            bpm = tempoCommands[0].bpm
            if isinstance(bpm, bool) or not isinstance(bpm, (int, float)):
                raise TypeError("Tempo must be numeric")
            if not math.isfinite(bpm) or bpm <= 0.0:
                raise ValueError("Tempo must be greater than zero")
            tempo = float(bpm)

        meter = Meter(4, 4) if not meterCommands else meterCommands[0]
        return tempo, meter

    def GetFullRange(self, meter):
        latestEnd = Fraction(0)
        for event in self.events:
            if not isinstance(event, Note):
                continue

            position = self.GetNotePositionWholeNotes(event.bar, event.beat, meter)
            if position is None:
                continue
            latestEnd = max(latestEnd, position + self.GetDurationWholeNotes(event.duration))

        if latestEnd <= 0:
            return Fraction(0), Fraction(0)

        barLength = Fraction(meter.beats, meter.unit)
        barPosition = latestEnd / barLength
        completeBars = math.ceil(barPosition)
        return Fraction(0), completeBars * barLength

    def _GetOccupiedBarRange(self):
        firstBar = None
        lastBar = None
        barOffset = 0

        for segment in self.GetSegments():
            barLength = Fraction(segment.meter.beats, segment.meter.unit)
            span = segment.end - segment.start
            barCount = math.ceil(span / barLength) if span > 0 else 0

            for event in segment.section.events:
                if not isinstance(event, Note):
                    continue

                position = segment.section.GetNotePositionWholeNotes(
                    event.bar, event.beat, segment.meter
                )
                if (
                        position is None
                        or position < segment.start
                        or position >= segment.end
                        ):
                    continue

                localBar = int((position - segment.start) // barLength)
                occupiedBar = barOffset + localBar
                if firstBar is None or occupiedBar < firstBar:
                    firstBar = occupiedBar
                if lastBar is None or occupiedBar > lastBar:
                    lastBar = occupiedBar

            barOffset += barCount

        return firstBar, lastBar

    def ApplySelection(self, segments):
        if self._start is None and self._end is None:
            return segments

        startIndex = 0
        startPosition = None
        startKey = (Fraction(0), Fraction(0))
        if self._start is not None:
            startIndex, startPosition, startKey = self.GetSelectionPosition(
                self._start, "Sequence start", segments
            )

        endIndex = len(segments)
        endPosition = None
        endKey = None
        if self._end is not None:
            endIndex, endPosition, endKey = self.GetSelectionPosition(
                self._end, "Sequence end", segments
            )

        if endKey is not None and endKey < startKey:
            raise ValueError("Sequence end cannot be before its start")

        selected = []
        lastIndex = endIndex if endPosition is None else endIndex + 1
        for index in range(startIndex, min(lastIndex, len(segments))):
            segment = segments[index]
            segmentStart = segment.start
            segmentEnd = segment.end
            if index == startIndex and startPosition is not None:
                segmentStart = startPosition
            if index == endIndex and endPosition is not None:
                segmentEnd = endPosition
            if segmentEnd <= segmentStart:
                continue

            selectedSegment = copy.copy(segment)
            selectedSegment.start = segmentStart
            selectedSegment.end = segmentEnd
            selected.append(selectedSegment)

        return selected

    def GetSegments(self):
        segments = []
        stack = [("sequence", self, segments)]
        while stack:
            action, value, target = stack.pop()
            if action == "selection":
                target.extend(value[0].ApplySelection(value[1]))
                continue

            sequence = value
            destination = target
            if sequence._start is not None or sequence._end is not None:
                selectedSegments = []
                stack.append(("selection", (sequence, selectedSegments), destination))
                destination = selectedSegments

            if sequence._components is None:
                tempo, meter = sequence.GetTiming()
                start, end = sequence.GetFullRange(meter)
                segment = SequenceSegment(
                    section = sequence,
                    tempo = tempo,
                    meter = meter,
                    start = start,
                    end = end
                )
                destination.extend(copy.copy(segment) for _ in range(sequence._repeat))
                continue

            for _ in range(sequence._repeat):
                for component in reversed(sequence._components):
                    stack.append(("sequence", component, destination))

        return segments

# -----------------------------------
# Sequence Rendering
# -----------------------------------

    def ScheduleSection(
            self, sectionStartFrame, firstEventIndex,
            tempo, meter, start, end
            ):
        from .ChirpPatches import Patches

        secondsPerWholeNote = 4.0 * (60.0 / tempo)
        spanSeconds = float(end - start) * secondsPerWholeNote
        spanFrames = max(0, round(spanSeconds * self.SAMPLE_RATE))
        patch = Patches.SuperSine
        balance = 0.0
        polyphonic = patch.polyphonic
        portamento = patch.portamento
        scheduledNotes = []
        invalidNotes = []
        eventIndex = firstEventIndex

        for event in self.events:
            if isinstance(event, (Tempo, Meter)):
                continue

            if isinstance(event, SetPatch):
                patch = event.patch
                balance = event.balance
                polyphonic = event.polyphonic
                portamento = event.portamento
                continue

            if not isinstance(event, Note):
                raise TypeError("Sequence entries must be Tempo, Meter, SetPatch, or Note")

            currentEventIndex = eventIndex
            eventIndex += 1
            position = self.GetNotePositionWholeNotes(
                event.bar, event.beat, meter
            )
            if position is None:
                invalidNotes.append((
                    event.bar, event.beat, meter.beats, meter.unit
                ))
                continue
            if position < start or position >= end:
                continue

            localSeconds = float(position - start) * secondsPerWholeNote
            startFrame = sectionStartFrame + max(0, round(localSeconds * self.SAMPLE_RATE))
            duration = self.GetDurationSeconds(event.duration, tempo)
            durationFrames = max(0, int(self.SAMPLE_RATE * duration))
            bendInDuration = self.GetDurationSeconds(event.bendInDuration, tempo)
            bendOutDuration = self.GetDurationSeconds(event.bendOutDuration, tempo)
            fadeInDuration = self.GetDurationSeconds(event.fadeInDuration, tempo)
            fadeOutDuration = self.GetDurationSeconds(event.fadeOutDuration, tempo)
            trillLength = None
            if event.trillTarget is not None:
                trillLength = self.GetDurationSeconds(event.trillLength, tempo)

            if event.chord is not None:
                frequencies = list(event.chord.GetFrequencies(event.freq))
                dynamics = event.chord.dynamics.GetGains(len(frequencies))
                gainByFrequency = dict(zip(sorted(frequencies), dynamics))
                roll = event.chord.roll
                rollFrames = 0
                if roll != 0.0:
                    rollSeconds = self.GetDurationSeconds(abs(roll), tempo)
                    rollFrames = max(1, int(self.SAMPLE_RATE * rollSeconds))
                    frequencies.sort(reverse = roll < 0.0)

                for chordIndex, frequency in enumerate(frequencies):
                    offsetFrames = chordIndex * rollFrames
                    if chordIndex > 0 and offsetFrames >= durationFrames:
                        break

                    remainingFrames = max(0, durationFrames - offsetFrames)
                    scheduledEvent = copy.copy(event)
                    scheduledEvent.freq = frequency
                    scheduledEvent.amplitude *= gainByFrequency[frequency]
                    if scheduledEvent.fadeTarget is not None:
                        scheduledEvent.fadeTarget *= gainByFrequency[frequency]
                    scheduledEvent.chord = None

                    if chordIndex > 0:
                        currentEventIndex = eventIndex
                        eventIndex += 1

                    scheduledNotes.append(ScheduledNote(
                        note = scheduledEvent,
                        patch = patch,
                        balance = balance,
                        polyphonic = polyphonic,
                        portamento = portamento,
                        portamentoStart = None,
                        portamentoDuration = 0.0,
                        startFrame = startFrame + offsetFrames,
                        duration = remainingFrames / self.SAMPLE_RATE,
                        performanceOffsetFrames = offsetFrames,
                        performanceDuration = duration,
                        bendInDuration = bendInDuration,
                        bendOutDuration = bendOutDuration,
                        fadeInDuration = fadeInDuration,
                        fadeOutDuration = fadeOutDuration,
                        forceEnvelopeRetrigger = False,
                        arpeggioGroup = None,
                        trillLength = trillLength,
                        eventIndex = currentEventIndex
                    ))
                continue

            if event.arpeggio is None:
                scheduledNotes.append(ScheduledNote(
                    note = event,
                    patch = patch,
                    balance = balance,
                    polyphonic = polyphonic,
                    portamento = portamento,
                    portamentoStart = None,
                    portamentoDuration = 0.0,
                    startFrame = startFrame,
                    duration = duration,
                    performanceOffsetFrames = 0,
                    performanceDuration = duration,
                    bendInDuration = bendInDuration,
                    bendOutDuration = bendOutDuration,
                    fadeInDuration = fadeInDuration,
                    fadeOutDuration = fadeOutDuration,
                    forceEnvelopeRetrigger = False,
                    arpeggioGroup = None,
                    trillLength = trillLength,
                    eventIndex = currentEventIndex
                ))
                continue

            frequencies = event.arpeggio.GetFrequencies(event.freq)
            dynamics = event.arpeggio.dynamics.GetGains(len(frequencies))
            stepSeconds = self.GetDurationSeconds(event.arpeggio.step, tempo)
            stepFrameLength = self.SAMPLE_RATE * stepSeconds
            offsetFrames = 0
            arpeggioIndex = 0
            arpeggioGroup = object()
            while offsetFrames < durationFrames or durationFrames == 0:
                nextOffsetFrames = min(
                    durationFrames,
                    max(offsetFrames + 1, int(stepFrameLength * (arpeggioIndex + 1)))
                )
                segmentFrames = nextOffsetFrames - offsetFrames
                scheduledEvent = copy.copy(event)
                patternIndex = arpeggioIndex % len(frequencies)
                scheduledEvent.freq = frequencies[patternIndex]
                scheduledEvent.amplitude *= dynamics[patternIndex]
                if scheduledEvent.fadeTarget is not None:
                    scheduledEvent.fadeTarget *= dynamics[patternIndex]
                scheduledEvent.arpeggio = None

                if arpeggioIndex > 0:
                    currentEventIndex = eventIndex
                    eventIndex += 1

                scheduledNotes.append(ScheduledNote(
                    note = scheduledEvent,
                    patch = patch,
                    balance = balance,
                    polyphonic = polyphonic,
                    portamento = portamento,
                    portamentoStart = None,
                    portamentoDuration = 0.0,
                    startFrame = startFrame + offsetFrames,
                    duration = segmentFrames / self.SAMPLE_RATE,
                    performanceOffsetFrames = offsetFrames,
                    performanceDuration = duration,
                    bendInDuration = bendInDuration,
                    bendOutDuration = bendOutDuration,
                    fadeInDuration = fadeInDuration,
                    fadeOutDuration = fadeOutDuration,
                    forceEnvelopeRetrigger = True,
                    arpeggioGroup = arpeggioGroup,
                    trillLength = trillLength,
                    eventIndex = currentEventIndex
                ))

                if durationFrames == 0:
                    break
                offsetFrames = nextOffsetFrames
                arpeggioIndex += 1

        return scheduledNotes, spanFrames, eventIndex, invalidNotes

    def ScheduleNotes(self):
        scheduledNotes = []
        invalidNotes = []
        sectionStartFrame = 0
        eventIndex = 0

        for segment in self.GetSegments():
            section = segment.section
            sectionResult = section.ScheduleSection(
                sectionStartFrame, eventIndex,
                segment.tempo, segment.meter,
                segment.start, segment.end
            )
            sectionNotes, spanFrames, eventIndex, sectionInvalid = sectionResult
            scheduledNotes.extend(sectionNotes)
            invalidNotes.extend(sectionInvalid)
            sectionStartFrame += spanFrames

        if invalidNotes:
            preview = ", ".join(
                "(" + str(bar) + ", " + str(beat) + ") in Meter("
                + str(beats) + ", " + str(unit) + ")"
                for bar, beat, beats, unit in invalidNotes[:5]
            )
            if len(invalidNotes) > 5:
                preview += ", ..."
            noteWord = "Note" if len(invalidNotes) == 1 else "Notes"
            warnings.warn(
                "Ignored " + str(len(invalidNotes)) + " " + noteWord
                + " with positions outside their bars: " + preview,
                stacklevel = 3
            )

        return self.ResolveMonophonicNotes(scheduledNotes)

    def ResolveMonophonicNotes(self, scheduledNotes):
        notesByPatch = {}
        for scheduled in scheduledNotes:
            if scheduled.polyphonic:
                continue
            notesByPatch.setdefault(scheduled.patch, []).append(scheduled)

        for patchNotes in notesByPatch.values():
            notesByStart = {}
            for scheduled in patchNotes:
                notesByStart.setdefault(scheduled.startFrame, []).append(scheduled)

            selectedNotes = []
            for startFrame in sorted(notesByStart):
                simultaneous = notesByStart[startFrame]
                selected = min(
                    (
                        float(item.note.freq),
                        item.eventIndex,
                        item
                    )
                    for item in simultaneous
                )[2]
                selectedNotes.append(selected)
                for scheduled in simultaneous:
                    if scheduled is not selected:
                        scheduled.discarded = True

            for index, scheduled in enumerate(selectedNotes[:-1]):
                nextScheduled = selectedNotes[index + 1]
                nextStartFrame = nextScheduled.startFrame
                endFrame = scheduled.startFrame + int(self.SAMPLE_RATE * scheduled.duration)
                nextEndFrame = nextStartFrame + int(
                    self.SAMPLE_RATE * nextScheduled.duration
                )
                overlapFrames = max(
                    0, min(endFrame, nextEndFrame) - nextStartFrame
                )
                if nextScheduled.portamento and overlapFrames > 0:
                    performance = PerformanceFrequency(
                        scheduled.note.freq,
                        bend = scheduled.note.bend,
                        bendEasing = scheduled.note.bendEasing,
                        bendStepped = scheduled.note.bendStepped,
                        bendRatios = scheduled.note.bendRatios,
                        duration = scheduled.performanceDuration,
                        bendIn = scheduled.note.bendInTarget,
                        bendInDuration = scheduled.bendInDuration,
                        bendInEasing = scheduled.note.bendInEasing,
                        bendOut = scheduled.note.bendOutTarget,
                        bendOutDuration = scheduled.bendOutDuration,
                        bendOutEasing = scheduled.note.bendOutEasing,
                        offset = scheduled.performanceOffsetFrames / self.SAMPLE_RATE
                    )
                    startFrequency = performance.GetBendFrequency(
                        nextStartFrame - scheduled.startFrame,
                        self.SAMPLE_RATE
                    )

                    targetFrequency = float(nextScheduled.note.freq)
                    if (
                            startFrequency > 0.0
                            and targetFrequency > 0.0
                            and not math.isclose(
                                startFrequency, targetFrequency,
                                rel_tol = 1e-9, abs_tol = 1e-12
                            )
                            ):
                        nextScheduled.portamentoStart = startFrequency
                        nextScheduled.portamentoDuration = (
                            overlapFrames / self.SAMPLE_RATE
                        )
                if nextStartFrame < endFrame:
                    scheduled.duration = (
                        nextStartFrame - scheduled.startFrame
                    ) / self.SAMPLE_RATE

        return [scheduled for scheduled in scheduledNotes if not scheduled.discarded]

    def ResolveModulationPhases(self, scheduledNotes):
        notesByPatch = {}
        oscillator = ChirpDSP(channels = 1).oscillator
        for scheduled in scheduledNotes:
            scheduled.tremoloPhaseDegrees = 0.0
            autoPan = scheduled.noteAutoPan
            scheduled.autoPanOffset = 0.0 if autoPan is None else autoPan[3]

            if scheduled.noteTremolo is not None:
                _, rate, wave = scheduled.noteTremolo
                scheduled.tremoloPhaseDegrees = math.degrees(
                    oscillator.GetMinimumPhase(wave, rate)
                )

            if scheduled.arpeggioGroup is not None:
                performanceOffset = (
                    scheduled.performanceOffsetFrames / self.SAMPLE_RATE
                )
                if scheduled.noteTremolo is not None:
                    rate = scheduled.noteTremolo[1]
                    scheduled.tremoloPhaseDegrees = (
                        scheduled.tremoloPhaseDegrees
                        + (360.0 * rate * performanceOffset)
                    ) % 360.0
                if autoPan is not None:
                    rate = autoPan[1]
                    scheduled.autoPanOffset = (
                        autoPan[3] + (360.0 * rate * performanceOffset)
                    ) % 360.0

            if not scheduled.polyphonic:
                notesByPatch.setdefault(scheduled.patch, []).append(scheduled)

        for patchNotes in notesByPatch.values():
            patchNotes.sort(key = operator.attrgetter("startFrame", "eventIndex"))
            for previous, scheduled in zip(patchNotes, patchNotes[1:]):
                if (
                        scheduled.arpeggioGroup is not None
                        and scheduled.arpeggioGroup is previous.arpeggioGroup
                        ):
                    continue

                previousEndFrame = previous.startFrame + int(
                    self.SAMPLE_RATE * previous.duration
                )
                if previousEndFrame != scheduled.startFrame:
                    continue

                if (
                        previous.noteTremolo is not None
                        and previous.noteTremolo == scheduled.noteTremolo
                        and previous.note.pan == scheduled.note.pan
                        ):
                    rate = scheduled.noteTremolo[1]
                    scheduled.tremoloPhaseDegrees = (
                        previous.tremoloPhaseDegrees
                        + (360.0 * rate * previous.duration)
                    ) % 360.0

                if (
                        previous.noteAutoPan is not None
                        and previous.noteAutoPan == scheduled.noteAutoPan
                        and previous.note.pan == scheduled.note.pan
                        ):
                    rate = scheduled.noteAutoPan[1]
                    scheduled.autoPanOffset = (
                        previous.autoPanOffset
                        + (360.0 * rate * previous.duration)
                    ) % 360.0

    def ApplyNoteControls(self, scheduled, noteSamples, channels):
        event = scheduled.note
        amplitude = max(0.0, event.amplitude)
        renderAmplitude = scheduled.renderAmplitude
        fadeTarget = scheduled.fadeTarget

        if len(noteSamples) > 0:
            dsp = ChirpDSP(channels = channels)
            frameCount = len(noteSamples) // channels

            if scheduled.noteTremolo is not None:
                depth, rate, wave = scheduled.noteTremolo
                modulation = dsp.GetModulationValues(
                    wave,
                    rate,
                    frameCount,
                    [scheduled.tremoloPhaseDegrees]
                )[0]
                tremoloGain = 1.0 - (depth * ((modulation + 1.0) * 0.5))
                noteSamples *= np.repeat(tremoloGain, channels)

            if fadeTarget is not None:
                if renderAmplitude > 0.0:
                    startGain = amplitude / renderAmplitude
                    targetGain = fadeTarget / renderAmplitude
                else:
                    startGain = 0.0
                    targetGain = 0.0

                fadeFrames = max(0, int(self.SAMPLE_RATE * scheduled.performanceDuration))
                fadeOffset = scheduled.performanceOffsetFrames
                progress = np.ones(frameCount, dtype = np.float64)
                if fadeFrames > fadeOffset:
                    progressCount = min(frameCount, fadeFrames - fadeOffset)
                    progress[:progressCount] = dsp.GetEasingValues(
                        fadeFrames, event.fadeEasing, fadeOffset, progressCount
                    )
                gains = startGain + ((targetGain - startGain) * progress)
                noteSamples *= np.repeat(gains, channels)

            if scheduled.fadeInDuration > 0.0 or scheduled.fadeOutDuration > 0.0:
                totalFrames = max(
                    0, int(self.SAMPLE_RATE * scheduled.performanceDuration)
                )
                fadeInFrames = max(
                    0, int(self.SAMPLE_RATE * scheduled.fadeInDuration)
                )
                fadeOutFrames = max(
                    0, int(self.SAMPLE_RATE * scheduled.fadeOutDuration)
                )
                gains = dsp.GetScopedFadeGains(
                    frameCount, totalFrames, scheduled.performanceOffsetFrames,
                    fadeInFrames, event.fadeInEasing,
                    fadeOutFrames, event.fadeOutEasing
                )
                noteSamples *= np.repeat(gains, channels)

            if channels == 2:
                if scheduled.noteAutoPan is not None:
                    depth, rate, wave, _ = scheduled.noteAutoPan
                    noteSamples = dsp.ApplySoundAutoPan(
                        noteSamples, depth, rate, wave,
                        scheduled.autoPanOffset, event.pan
                    )
                elif event.pan != 0.0:
                    noteSamples = dsp.ApplySoundPan(noteSamples, event.pan)

        return noteSamples

    def RenderSamples(self, channels = 2):
        if isinstance(channels, bool) or not isinstance(channels, Integral) or channels not in (1, 2):
            raise ValueError("Sequence only supports 1 or 2 channels")
        channels = int(channels)

        scheduledNotes = self.ScheduleNotes()
        renderedNotes = []
        sampleCount = 0

        for scheduled in scheduledNotes:
            event = scheduled.note
            duration = scheduled.duration
            amplitude = max(0.0, event.amplitude)
            fadeTarget = None
            renderAmplitude = amplitude
            if event.fadeTarget is not None:
                fadeTarget = max(0.0, min(1.0, event.fadeTarget))
                renderAmplitude = max(amplitude, fadeTarget)

            freq = event.freq
            if (
                    event.bend is not None
                    or event.bendInTarget is not None
                    or event.bendOutTarget is not None
                    or event.trillTarget is not None
                    or event.vibratoEnabled
                    or scheduled.portamentoStart is not None
                    ):
                freq = PerformanceFrequency(
                    event.freq,
                    bend = event.bend,
                    bendEasing = event.bendEasing,
                    bendStepped = event.bendStepped,
                    bendRatios = event.bendRatios,
                    duration = scheduled.performanceDuration,
                    bendIn = event.bendInTarget,
                    bendInDuration = scheduled.bendInDuration,
                    bendInEasing = event.bendInEasing,
                    bendOut = event.bendOutTarget,
                    bendOutDuration = scheduled.bendOutDuration,
                    bendOutEasing = event.bendOutEasing,
                    offset = scheduled.performanceOffsetFrames / self.SAMPLE_RATE,
                    portamentoStart = scheduled.portamentoStart,
                    portamentoDuration = scheduled.portamentoDuration,
                    trill = event.trillTarget,
                    trillLength = scheduled.trillLength,
                    vibratoEnabled = event.vibratoEnabled,
                    vibratoDepth = event.vibratoDepth,
                    vibratoRate = event.vibratoRate,
                    vibratoWave = event.vibratoWave
                )

            scheduled.fadeTarget = fadeTarget
            scheduled.renderAmplitude = renderAmplitude
            scheduled.freq = freq
            scheduled.noteTremolo = None
            if event.tremoloEnabled:
                depth = Tremolo.LIGHT if event.tremoloDepth is None else event.tremoloDepth
                rate = 6.0 if event.tremoloRate is None else event.tremoloRate
                wave = "Sine" if event.tremoloWave is None else event.tremoloWave
                if isinstance(wave, str):
                    wave = wave.replace("_", "").replace("-", "").lower()
                scheduled.noteTremolo = (
                    max(0.0, min(1.0, depth)), max(0.0, rate), wave
                )

            scheduled.noteAutoPan = None
            if event.autoPanEnabled:
                wave = event.autoPanWave
                if isinstance(wave, str):
                    wave = wave.replace("_", "").replace("-", "").lower()
                scheduled.noteAutoPan = (
                    max(0.0, min(1.0, event.autoPanDepth)),
                    max(0.0, event.autoPanRate),
                    wave,
                    event.autoPanOffset % 360.0,
                )

        self.ResolveModulationPhases(scheduledNotes)

        monophonicByPatch = {}
        for scheduled in scheduledNotes:
            if scheduled.polyphonic:
                transientGain, bodyGain = scheduled.patch.GetBalancedGains(
                    scheduled.balance
                )
                scheduled.samples = scheduled.patch.RenderSamples(
                    scheduled.freq,
                    scheduled.duration,
                    scheduled.renderAmplitude,
                    channels,
                    transientGain,
                    bodyGain
                )
            else:
                monophonicByPatch.setdefault(scheduled.patch, []).append(scheduled)

        for patch, patchNotes in monophonicByPatch.items():
            patchNotes.sort(key = operator.attrgetter("startFrame", "eventIndex"))
            rendered = patch.RenderMonophonic(patchNotes, channels)
            for scheduled, noteSamples in zip(patchNotes, rendered):
                scheduled.samples = noteSamples

        for scheduled in scheduledNotes:
            noteSamples = scheduled.samples
            noteSamples = self.ApplyNoteControls(scheduled, noteSamples, channels)

            startSample = scheduled.startFrame * channels
            renderedNotes.append((startSample, noteSamples))
            sampleCount = max(sampleCount, startSample + len(noteSamples))

        samples = np.zeros(sampleCount, dtype = np.float64)
        for startSample, noteSamples in renderedNotes:
            samples[startSample:startSample + len(noteSamples)] += noteSamples

        return samples

    def Render(self, channels = 2):
        from ..core.ChirpSound import Sound

        return Sound(samples = self.RenderSamples(channels), channels = channels)


__all__ = [
    "Meter",
    "SetPatch",
    "Note",
    "Sequence",
]
