import copy
import math

import numpy as np

from ..core.ChirpRender import ChirpRenderPlan, ToneRenderEvent
from ..core.ChirpSynth import ChirpSynth
from ..core.ChirpTone import Control, Insert, Seconds, Tone, Wave
from .ChirpSchedule import EnvelopeRenderInfo, PatchToneLayer


class Envelope:
    __slots__ = (
        "attack", "decay", "sustain", "release", "retrigger",
        "attackCurve", "decayCurve", "releaseCurve"
    )

    def __init__(
            self, attack, decay, sustain, release, retrigger = True,
            attackCurve = -5.0, decayCurve = 5.0, releaseCurve = 5.0
            ):
        self.attack = self.ValidateDuration(attack, "attack")
        self.decay = self.ValidateDuration(decay, "decay")
        self.sustain = self.ValidateSustain(sustain)
        self.release = self.ValidateDuration(release, "release")
        if not isinstance(retrigger, bool):
            raise TypeError("retrigger must be a boolean")
        self.retrigger = retrigger
        self.attackCurve = self.ValidateNumber(attackCurve, "attackCurve")
        self.decayCurve = self.ValidateNumber(decayCurve, "decayCurve")
        self.releaseCurve = self.ValidateNumber(releaseCurve, "releaseCurve")

    def __setattr__(self, name, value):
        if hasattr(self, name):
            raise AttributeError("Envelope objects cannot be modified")
        object.__setattr__(self, name, value)

    def __delattr__(self, name):
        raise AttributeError("Envelope objects cannot be modified")

    @staticmethod
    def ValidateNumber(value, name):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(name + " must be numeric")
        if not math.isfinite(value):
            raise ValueError(name + " must be finite")
        return float(value)

    @classmethod
    def ValidateDuration(cls, value, name):
        return max(0.0, cls.ValidateNumber(value, name))

    @classmethod
    def ValidateSustain(cls, value):
        if value is None:
            return 0.0
        return max(0.0, cls.ValidateNumber(value, "sustain"))

    @staticmethod
    def GetCurveValues(count, curve):
        if count <= 0:
            return np.empty(0, dtype = np.float64)

        percentages = np.linspace(0.0, 1.0, count, dtype = np.float64)
        if curve == 0.0:
            return percentages

        if curve > 0.0:
            return np.expm1(-curve * percentages) / math.expm1(-curve)

        strength = -curve
        numerator = np.exp(strength * (percentages - 1.0))
        numerator *= -np.expm1(-strength * percentages)
        return numerator / -math.expm1(-strength)


class Patch:
    SAMPLE_RATE = 44100
    __slots__ = (
        "_frozen", "transientRecipe", "bodyRecipe", "transientGain",
        "bodyGain", "polyphonic", "portamento", "envelope"
    )

    def __init__(
            self, transient = None, body = None,
            transientGain = 1.0, bodyGain = 1.0, envelope = None,
            polyphonic = True, portamento = False
            ):
        object.__setattr__(self, "_frozen", False)

        if transient is None:
            transientMethod = getattr(self, "Transient", None)
            if callable(transientMethod):
                transient = transientMethod
        if body is None:
            bodyMethod = getattr(self, "Body", None)
            if callable(bodyMethod):
                body = bodyMethod

        self.ValidateRecipe(transient, "transient")
        self.ValidateRecipe(body, "body")
        self.transientRecipe = transient
        self.bodyRecipe = body
        self.transientGain = self.ValidateGain(transientGain, "transientGain")
        self.bodyGain = self.ValidateGain(bodyGain, "bodyGain")
        if not isinstance(polyphonic, bool):
            raise TypeError("polyphonic must be a boolean")
        self.polyphonic = polyphonic
        if not isinstance(portamento, bool):
            raise TypeError("portamento must be a boolean")
        self.portamento = portamento
        if envelope is not None and not isinstance(envelope, Envelope):
            raise TypeError("envelope must be an Envelope or None")
        self.envelope = envelope

    def __setattr__(self, name, value):
        if getattr(self, "_frozen", False):
            raise AttributeError("Built-in Patch objects cannot be modified")
        object.__setattr__(self, name, value)

    def __delattr__(self, name):
        if getattr(self, "_frozen", False):
            raise AttributeError("Built-in Patch objects cannot be modified")
        object.__delattr__(self, name)

    def _Freeze(self):
        object.__setattr__(self, "_frozen", True)
        return self

# -----------------------------------
# Recipe Rendering
# -----------------------------------

    def ValidateRecipe(self, recipe, name):
        if recipe is not None and not callable(recipe):
            raise TypeError("Patch " + name + " recipe must be callable or None")

    @staticmethod
    def ValidateGain(gain, name):
        if isinstance(gain, bool) or not isinstance(gain, (int, float)):
            raise TypeError(name + " must be numeric")
        if not math.isfinite(gain):
            raise ValueError(name + " must be finite")
        return float(gain)

    @staticmethod
    def ValidateBalance(balance):
        if isinstance(balance, bool) or not isinstance(balance, (int, float)):
            raise TypeError("balance must be numeric")
        if not math.isfinite(balance):
            raise ValueError("balance must be finite")
        return max(-1.0, min(1.0, float(balance)))

    def GetBalancedGains(self, balance = 0.0):
        balance = self.ValidateBalance(balance)
        if balance < 0.0:
            return self.transientGain, self.bodyGain * (balance + 1.0)

        return self.transientGain * (1.0 - balance), self.bodyGain

    def GetRecipeItems(self, recipe, freq, duration, amplitude):
        if recipe is None:
            return []

        items = recipe(freq, duration, amplitude)
        if items is None:
            raise ValueError("Patch recipe must return a list")

        try:
            return list(items)
        except TypeError as error:
            raise TypeError("Patch recipe must return a list") from error

    def GetEnvelopeGains(self, duration):
        if self.envelope is None:
            return None

        envelope = self.envelope
        attackFrames = max(0, int(self.SAMPLE_RATE * envelope.attack))
        decayFrames = max(0, int(self.SAMPLE_RATE * envelope.decay))

        gateFrames = max(0, int(self.SAMPLE_RATE * duration))
        releaseFrames = max(0, int(self.SAMPLE_RATE * envelope.release))
        gains = np.full(
            gateFrames + releaseFrames, envelope.sustain, dtype = np.float64
        )

        attackCount = min(attackFrames, gateFrames)
        if attackCount > 0:
            attackProgress = envelope.GetCurveValues(
                attackFrames, envelope.attackCurve
            )
            gains[:attackCount] = attackProgress[:attackCount]

        decayStart = attackFrames
        decayCount = min(decayFrames, max(0, gateFrames - decayStart))
        if decayCount > 0:
            decayProgress = envelope.GetCurveValues(
                decayFrames, envelope.decayCurve
            )
            gains[decayStart:decayStart + decayCount] = 1.0 + (
                (envelope.sustain - 1.0) * decayProgress[:decayCount]
            )

        if releaseFrames > 0:
            if gateFrames > 0:
                releaseStart = gains[gateFrames - 1]
            elif attackFrames > 0:
                releaseStart = 0.0
            elif decayFrames > 0:
                releaseStart = 1.0
            else:
                releaseStart = envelope.sustain
            releaseProgress = envelope.GetCurveValues(
                releaseFrames, envelope.releaseCurve
            )
            if releaseFrames == 1:
                releaseProgress[0] = 1.0
            gains[gateFrames:] = releaseStart * (1.0 - releaseProgress)

        return gains

    def ApplyEnvelope(self, samples, channels, gains, offsetFrames = 0):
        if gains is None:
            return samples

        availableFrames = max(0, len(gains) - offsetFrames)
        frameCount = min(len(samples) // channels, availableFrames)
        samples = samples[:frameCount * channels].copy()
        if frameCount > 0:
            gainSlice = gains[offsetFrames:offsetFrames + frameCount]
            samples *= np.repeat(gainSlice, channels)
        return samples

# -----------------------------------
# Monophonic Rendering
# -----------------------------------

    def GetMonophonicEnvelopeInfo(self, requests, compatibilityBreaks = None):
        envelopeInfo = [None] * len(requests)
        if self.envelope is None:
            return envelopeInfo
        if compatibilityBreaks is None:
            compatibilityBreaks = set()

        if self.envelope.retrigger:
            for requestIndex, request in enumerate(requests):
                envelopeInfo[requestIndex] = EnvelopeRenderInfo(
                    gains = self.GetEnvelopeGains(request.duration),
                    offsetFrames = 0,
                    extend = True
                )
            return envelopeInfo

        runStart = 0
        while runStart < len(requests):
            runEnd = runStart
            while runEnd + 1 < len(requests):
                if runEnd + 1 in compatibilityBreaks:
                    break
                requestEndFrame = requests[runEnd].startFrame + int(
                    self.SAMPLE_RATE * requests[runEnd].duration
                )
                if requestEndFrame != requests[runEnd + 1].startFrame:
                    break
                runEnd += 1

            startFrame = requests[runStart].startFrame
            endFrame = requests[runEnd].startFrame + int(
                self.SAMPLE_RATE * requests[runEnd].duration
            )
            gains = self.GetEnvelopeGains(
                (endFrame - startFrame) / self.SAMPLE_RATE
            )
            for requestIndex in range(runStart, runEnd + 1):
                envelopeInfo[requestIndex] = EnvelopeRenderInfo(
                    gains = gains,
                    offsetFrames = requests[requestIndex].startFrame - startFrame,
                    extend = requestIndex == runEnd
                )
            runStart = runEnd + 1

        return envelopeInfo

    def GetEnvelopeCompatibilityBreaks(self, requests, toneLayers, channels):
        breaks = set()
        bodyLayers = {
            layerKey: layers
            for layerKey, layers in toneLayers.items()
            if layerKey[0] == "body"
        }
        for requestIndex in range(1, len(requests)):
            if requests[requestIndex].forceEnvelopeRetrigger:
                breaks.add(requestIndex)
                continue

            previousEnd = requests[requestIndex - 1].startFrame + int(
                self.SAMPLE_RATE * requests[requestIndex - 1].duration
            )
            if previousEnd != requests[requestIndex].startFrame:
                breaks.add(requestIndex)
                continue

            for layers in bodyLayers.values():
                previousLayers = [
                    layer for layer in layers
                    if layer.requestIndex == requestIndex - 1
                ]
                currentLayers = [
                    layer for layer in layers
                    if layer.requestIndex == requestIndex
                ]
                if not previousLayers or not currentLayers:
                    breaks.add(requestIndex)
                    break

                previousLayer = previousLayers[0]
                for layer in previousLayers[1:]:
                    if layer.startFrame > previousLayer.startFrame:
                        previousLayer = layer

                currentLayer = currentLayers[0]
                for layer in currentLayers[1:]:
                    if layer.startFrame < currentLayer.startFrame:
                        currentLayer = layer
                if not self.LayerEventsAreCompatible(
                        previousLayer, currentLayer, channels
                        ):
                    breaks.add(requestIndex)
                    break

        return breaks

    def GetEnvelopeEventTarget(self, layer, channels):
        info = layer.envelopeInfo
        if layer.sectionName != "body" or info is None or not info.extend:
            return None

        eventFrames = layer.event.sampleCount // channels
        requestOffsetFrames = layer.requestOffsetFrames
        gateFrames = max(0, int(self.SAMPLE_RATE * layer.request.duration))
        targetFrames = max(0, len(info.gains) - info.offsetFrames)
        eventEndFrame = requestOffsetFrames + eventFrames
        if eventEndFrame < gateFrames or eventEndFrame >= targetFrames:
            return None
        return targetFrames - requestOffsetFrames

    def RenderLayerTail(self, synthesizer, event, initialState, targetFrames, channels):
        originalFrames = event.sampleCount // channels
        tailFrames = max(0, targetFrames - originalFrames)
        if tailFrames == 0:
            return np.empty(0, dtype = np.float64)

        elapsed = originalFrames / self.SAMPLE_RATE
        tailEvent = copy.copy(event)
        tailEvent.duration = math.nextafter(tailFrames / self.SAMPLE_RATE, math.inf)
        tailEvent.sampleCount = tailFrames * channels
        tailEvent.bendOffset += elapsed
        tailEvent.amplitudeBendOffset += elapsed
        tailEvent.performanceBendOffset += elapsed
        tailEvent.performancePortamentoOffset += elapsed
        tailEvent.performanceOffset += elapsed
        tailEvent.continueAutoPan = tailEvent.autoPanEnabled
        tailEvent.fadeIn = False
        tailEvent.fadeOut = False
        tailEvent.fadeFrames = 0
        return synthesizer.RenderPlan(
            ChirpRenderPlan(synthesizer, [tailEvent], tailEvent.sampleCount),
            initialState = initialState
        )

    def AddLayerSamples(self, noteSamples, layerSamples, gain, offsetSamples = 0):
        requiredSamples = offsetSamples + len(layerSamples)
        if requiredSamples > len(noteSamples):
            extended = np.zeros(requiredSamples, dtype = np.float64)
            extended[:len(noteSamples)] = noteSamples
            noteSamples = extended

        noteSamples[offsetSamples:requiredSamples] += layerSamples * gain
        return noteSamples

    def WavesAreCompatible(self, previousWave, wave):
        previousFunction = getattr(previousWave, "__func__", previousWave)
        waveFunction = getattr(wave, "__func__", wave)
        if previousFunction is waveFunction:
            return True

        if hasattr(previousWave, "samples") and hasattr(wave, "samples"):
            return np.array_equal(previousWave.samples, wave.samples)

        return False

    def LayerEventsAreCompatible(self, previous, current, channels):
        previousEvent = previous.event
        event = current.event
        previousRequest = previous.request
        request = current.request

        if current.requestIndex not in (
                previous.requestIndex, previous.requestIndex + 1
                ):
            return False
        previousEndFrame = previous.startFrame + (previousEvent.sampleCount // channels)
        if previousEndFrame != current.startFrame:
            return False
        if not isinstance(previousEvent, ToneRenderEvent) or not isinstance(event, ToneRenderEvent):
            return False
        if previousEvent.isNoise or event.isNoise:
            return False
        if previousEvent.phaseDegrees is not None or event.phaseDegrees is not None:
            return False
        if any((
                previousEvent.bendIn is not None,
                previousEvent.bendOut is not None,
                event.bendIn is not None,
                event.bendOut is not None,
                previousEvent.fadeInDuration > 0.0,
                previousEvent.fadeOutDuration > 0.0,
                event.fadeInDuration > 0.0,
                event.fadeOutDuration > 0.0,
                )):
            return False
        if previousRequest.note.pan != request.note.pan:
            return False
        if previousRequest.noteTremolo != request.noteTremolo:
            return False
        if (
                previousEvent.performanceTrill is not None
                or event.performanceTrill is not None
                ):
            return False
        if not self.WavesAreCompatible(previousEvent.wave, event.wave):
            return False

        previousAmplitude = previousEvent.amplitude
        if previousEvent.amplitudeBend is not None:
            previousAmplitude = previousEvent.amplitudeBend
        previousNoteGain = 1.0
        noteGain = 1.0
        sameArpeggio = (
            request.arpeggioGroup is not None
            and request.arpeggioGroup is previousRequest.arpeggioGroup
        )
        if previous.requestIndex != current.requestIndex and not sameArpeggio:
            if previousRequest.fadeTarget is not None:
                if previousRequest.renderAmplitude > 0.0:
                    previousNoteGain = (
                        previousRequest.fadeTarget / previousRequest.renderAmplitude
                    )
                else:
                    previousNoteGain = 0.0

            if request.fadeTarget is not None:
                if request.renderAmplitude > 0.0:
                    noteAmplitude = max(0.0, request.note.amplitude)
                    noteGain = noteAmplitude / request.renderAmplitude
                else:
                    noteGain = 0.0

        previousAmplitude *= previousNoteGain * previous.gain
        amplitude = event.amplitude * noteGain * current.gain
        if not math.isclose(previousAmplitude, amplitude, rel_tol = 0.0, abs_tol = 1e-12):
            return False

        properties = (
            "pan", "vibrato", "vibratoRate", "tremolo", "tremoloRate",
            "modFreq", "modDepth", "unisonVoices", "unisonDetune",
            "unisonSpread", "performanceVibrato", "performanceVibratoRate",
            "autoPanEnabled", "autoPanDepth", "autoPanRate", "autoPanOffset"
        )
        for propertyName in properties:
            if getattr(previousEvent, propertyName) != getattr(event, propertyName):
                return False

        for propertyName in (
                "vibratoWave", "tremoloWave", "modWave", "performanceVibratoWave",
                "autoPanWave"
            ):
            if not self.WavesAreCompatible(
                    getattr(previousEvent, propertyName), getattr(event, propertyName)
                    ):
                return False

        return True

    def RenderLayerRun(self, synthesizer, layerRun, noteSamples, channels):
        events = [copy.copy(layer.event) for layer in layerRun]
        elapsedFrames = 0
        for event in events:
            event.performanceOffset = max(
                event.performanceOffset, elapsedFrames / self.SAMPLE_RATE
            )
            elapsedFrames += event.sampleCount // channels
        for index in range(1, len(events)):
            events[index - 1].fadeOut = False
            events[index].fadeIn = False
            events[index].continueAutoPan = events[index].autoPanEnabled

        lastTarget = self.GetEnvelopeEventTarget(layerRun[-1], channels)
        if lastTarget is not None:
            events[-1].duration = math.nextafter(
                lastTarget / self.SAMPLE_RATE, math.inf
            )
            events[-1].sampleCount = lastTarget * channels
            events[-1].fadeOut = False

        sampleCount = sum(event.sampleCount for event in events)
        eventEndStates = []
        rendered = synthesizer.RenderPlan(
            ChirpRenderPlan(synthesizer, events, sampleCount),
            eventEndStates = eventEndStates
        )
        sampleIndex = 0
        for layerIndex, (layer, event) in enumerate(zip(layerRun, events)):
            eventEnd = sampleIndex + event.sampleCount
            requestIndex = layer.requestIndex
            layerSamples = rendered[sampleIndex:eventEnd]
            targetFrames = self.GetEnvelopeEventTarget(layer, channels)
            if targetFrames is not None and layerIndex < len(layerRun) - 1:
                tail = self.RenderLayerTail(
                    synthesizer, event, eventEndStates[layerIndex], targetFrames, channels
                )
                layerSamples = np.concatenate((layerSamples, tail))
            if layer.sectionName == "body":
                info = layer.envelopeInfo
                if info is not None:
                    layerSamples = self.ApplyEnvelope(
                        layerSamples,
                        channels,
                        info.gains,
                        info.offsetFrames + layer.requestOffsetFrames
                    )
            noteSamples[requestIndex] = self.AddLayerSamples(
                noteSamples[requestIndex],
                layerSamples,
                layer.gain,
                layer.requestOffsetFrames * channels
            )
            sampleIndex = eventEnd

    def RenderMonophonic(self, requests, channels):
        noteSamples = [np.empty(0, dtype = np.float64) for _ in requests]
        layerSynthesizers = {}
        toneLayers = {}
        bodyInserts = []
        insertSynthesizer = ChirpSynth(channels = channels)

        for requestIndex, request in enumerate(requests):
            transientGain, bodyGain = self.GetBalancedGains(request.balance)
            sections = (
                ("transient", self.transientRecipe, transientGain),
                ("body", self.bodyRecipe, bodyGain),
            )
            for sectionName, recipe, gain in sections:
                items = self.GetRecipeItems(
                    recipe,
                    request.freq,
                    request.duration,
                    request.renderAmplitude
                )
                controls = []
                layerIndex = 0

                for item in items:
                    if isinstance(item, Insert):
                        inserted = insertSynthesizer.GetSoundSamples(item.sound)
                        if sectionName == "body":
                            bodyInserts.append((requestIndex, inserted, gain))
                        else:
                            noteSamples[requestIndex] = self.AddLayerSamples(
                                noteSamples[requestIndex], inserted, gain
                            )
                        layerIndex += 1
                        continue

                    if isinstance(item, Tone):
                        tone = copy.copy(item)
                        if tone.bend == tone.freq:
                            tone.bend = None

                        layerKey = (sectionName, layerIndex)
                        synthesizer = layerSynthesizers.get(layerKey)
                        if synthesizer is None:
                            synthesizer = ChirpSynth(channels = channels)
                            layerSynthesizers[layerKey] = synthesizer
                        plan = synthesizer.CompileSequence(controls + [Seconds(), tone])
                        requestOffsetFrames = 0
                        for planEvent in plan.events:
                            toneLayers.setdefault(layerKey, []).append(PatchToneLayer(
                                event = planEvent,
                                gain = gain,
                                request = request,
                                requestIndex = requestIndex,
                                requestOffsetFrames = requestOffsetFrames,
                                startFrame = request.startFrame + requestOffsetFrames,
                                sectionName = sectionName
                            ))
                            requestOffsetFrames += planEvent.sampleCount // channels
                        layerIndex += 1
                        continue

                    if isinstance(item, Wave):
                        raise ValueError(
                            "Patch recipes do not support Wave controls; use Tone.Wave "
                            "to override a Tone's default Sine wave"
                        )

                    if isinstance(item, Control):
                        controls.append(item)
                        continue

                    raise TypeError("Patch recipes may only contain Tone, Insert, or control objects")

        compatibilityBreaks = self.GetEnvelopeCompatibilityBreaks(
            requests, toneLayers, channels
        )
        envelopeInfo = self.GetMonophonicEnvelopeInfo(
            requests, compatibilityBreaks
        )
        for requestIndex, inserted, gain in bodyInserts:
            info = envelopeInfo[requestIndex]
            if info is not None:
                inserted = self.ApplyEnvelope(
                    inserted, channels, info.gains, info.offsetFrames
                )
            noteSamples[requestIndex] = self.AddLayerSamples(
                noteSamples[requestIndex], inserted, gain
            )

        for layers in toneLayers.values():
            for layer in layers:
                layer.envelopeInfo = envelopeInfo[layer.requestIndex]

        for layerKey, layers in toneLayers.items():
            synthesizer = layerSynthesizers[layerKey]
            layerRun = []
            for layer in layers:
                if layerRun and not self.LayerEventsAreCompatible(
                        layerRun[-1], layer, channels
                        ):
                    self.RenderLayerRun(
                        synthesizer, layerRun, noteSamples, channels
                    )
                    layerRun = []
                layerRun.append(layer)

            if layerRun:
                self.RenderLayerRun(
                    synthesizer, layerRun, noteSamples, channels
                )

        return noteSamples

    def RenderAmplitude(
            self, freq, duration, amplitude, channels, transientGain, bodyGain
            ):
        synthesizer = ChirpSynth(channels = channels)
        transient = self.GetRecipeItems(
            self.transientRecipe, freq, duration, amplitude
        )
        body = self.GetRecipeItems(self.bodyRecipe, freq, duration, amplitude)
        envelopeGains = self.GetEnvelopeGains(duration)
        transientLayers = synthesizer.RenderLayers(
            transient, forceSeconds = True, requireToneWave = True
        )
        bodyLayers = synthesizer.RenderLayers(
            body,
            forceSeconds = True,
            requireToneWave = True,
            duration = duration,
            targetFrames = None if envelopeGains is None else len(envelopeGains)
        )

        if len(transientLayers) == 0 and len(bodyLayers) == 0:
            return np.empty(0, dtype = np.float64)

        transientSamples = np.empty(0, dtype = np.float64)
        if transientLayers:
            transientSamples = np.zeros(
                max(len(layer) for layer in transientLayers), dtype = np.float64
            )
        for layer in transientLayers:
            transientSamples[:len(layer)] += layer * transientGain

        bodySamples = np.empty(0, dtype = np.float64)
        if bodyLayers:
            bodySamples = np.zeros(
                max(len(layer) for layer in bodyLayers), dtype = np.float64
            )
        for layer in bodyLayers:
            bodySamples[:len(layer)] += layer * bodyGain
        bodySamples = self.ApplyEnvelope(
            bodySamples, channels, envelopeGains
        )

        sampleCount = max(len(transientSamples), len(bodySamples))
        samples = np.zeros(sampleCount, dtype = np.float64)
        samples[:len(transientSamples)] += transientSamples
        samples[:len(bodySamples)] += bodySamples

        return samples

    def RenderSamples(
            self, freq, duration, amplitude = 1.0, channels = 2,
            transientGain = None, bodyGain = None
            ):
        duration = max(0.0, duration)
        amplitude = max(0.0, amplitude)
        transientGain = self.transientGain if transientGain is None else self.ValidateGain(
            transientGain, "transientGain"
        )
        bodyGain = self.bodyGain if bodyGain is None else self.ValidateGain(
            bodyGain, "bodyGain"
        )
        return self.RenderAmplitude(
            freq, duration, amplitude, channels, transientGain, bodyGain
        )

    def Render(
            self, freq, duration, amplitude = 1.0, channels = 2,
            transientGain = None, bodyGain = None
            ):
        from ..core.ChirpSound import Sound

        samples = self.RenderSamples(
            freq, duration, amplitude, channels, transientGain, bodyGain
        )
        return Sound(samples = samples, channels = channels)


__all__ = [
    "Envelope",
    "Patch",
]
