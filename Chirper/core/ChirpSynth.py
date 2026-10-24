import copy
import math
from numbers import Integral

import numpy as np

from . import ChirpKernels, Easing
from .ChirpConstants import Tremolo, Vibrato
from .ChirpDSP import ChirpDSP
from .ChirpOscillator import ChirpOscillator
from .ChirpRender import (
    ChirpRenderPlan,
    ChirpRenderState,
    InsertRenderEvent,
    ParsedTone,
    SilenceRenderEvent,
    ToneRenderEvent,
    ToneRenderSettings,
)
from .ChirpTone import (
    Control,
    Insert as InsertControl,
    PerformanceFrequency,
    Pitch as PitchControl,
    Seconds as SecondsControl,
    Tempo as TempoControl,
    Tone,
    TremoloDepth as TremoloDepthControl,
    TremoloRate as TremoloRateControl,
    TremoloWave as TremoloWaveControl,
    VibratoDepth as VibratoDepthControl,
    VibratoRate as VibratoRateControl,
    VibratoWave as VibratoWaveControl,
    Wave as WaveControl,
)

class ChirpSynth:
    SAMPLE_RATE = 44100
    BITS_PER_SAMPLE = 16
    MIN_FREQ = 20.0

    def __init__(self, channels = 2):
        if isinstance(channels, bool) or not isinstance(channels, Integral) or channels not in (1, 2):
            raise ValueError("ChirpSynth only supports 1 or 2 channels")

        self.channels = int(channels)
        self.oscillator = ChirpOscillator(sampleRate = self.SAMPLE_RATE)
        self.pitch = 1.0
        self.vibratoDepth = Vibrato.LIGHT
        self.vibratoRate = 6.0
        self.vibratoWave = self.oscillator.Sine
        self.tremoloDepth = Tremolo.LIGHT
        self.tremoloRate = 6.0
        self.tremoloWave = self.oscillator.Sine
        self.waveShape = self.oscillator.Sine

# -----------------------------------
# Make Sound
# -----------------------------------

    def ApplyScopedFades(
            self, samples, totalDuration, offset,
            fadeInDuration, fadeInEasing,
            fadeOutDuration, fadeOutEasing
            ):
        if fadeInDuration <= 0.0 and fadeOutDuration <= 0.0:
            return samples

        frameCount = len(samples)
        totalFrames = max(0, int(self.SAMPLE_RATE * totalDuration))
        offsetFrames = max(0, round(self.SAMPLE_RATE * offset))
        fadeInFrames = max(0, int(self.SAMPLE_RATE * fadeInDuration))
        fadeOutFrames = max(0, int(self.SAMPLE_RATE * fadeOutDuration))
        gains = ChirpDSP(channels = 1).GetScopedFadeGains(
            frameCount, totalFrames, offsetFrames,
            fadeInFrames, fadeInEasing,
            fadeOutFrames, fadeOutEasing
        )
        return samples * gains

    def _MakeTone(self, settings):
        if not isinstance(settings, ToneRenderSettings):
            raise TypeError("Expected ToneRenderSettings")

        freq = settings.freq
        duration = settings.duration
        wave = settings.wave
        pitch = settings.pitch
        amplitude = settings.amplitude
        vibrato = settings.vibrato
        vibratoRate = settings.vibratoRate
        vibratoPhase = settings.vibratoPhase
        vibratoWave = settings.vibratoWave
        tremolo = settings.tremolo
        tremoloRate = settings.tremoloRate
        tremoloWave = settings.tremoloWave
        modFreq = settings.modFreq
        modDepth = settings.modDepth
        modWave = settings.modWave
        modPhase = settings.modPhase
        bend = settings.bend
        bendEasing = settings.bendEasing
        bendIn = settings.bendIn
        bendInDuration = settings.bendInDuration
        bendInEasing = settings.bendInEasing
        bendOut = settings.bendOut
        bendOutDuration = settings.bendOutDuration
        bendOutEasing = settings.bendOutEasing
        amplitudeBend = settings.amplitudeBend
        amplitudeEasing = settings.amplitudeEasing
        fadeInDuration = settings.fadeInDuration
        fadeInEasing = settings.fadeInEasing
        fadeOutDuration = settings.fadeOutDuration
        fadeOutEasing = settings.fadeOutEasing
        scopedDuration = settings.scopedDuration
        oscillatorPhase = settings.oscillatorPhase
        fadeIn = settings.fadeIn
        fadeOut = settings.fadeOut
        phaseDegrees = settings.phaseDegrees
        tremoloPhase = settings.tremoloPhase
        performanceBend = settings.performanceBend
        performanceBendEasing = settings.performanceBendEasing
        performanceBendStepped = settings.performanceBendStepped
        performanceBendRatios = settings.performanceBendRatios
        performanceBendDuration = settings.performanceBendDuration
        performanceBendOffset = settings.performanceBendOffset
        performanceBendIn = settings.performanceBendIn
        performanceBendInDuration = settings.performanceBendInDuration
        performanceBendInEasing = settings.performanceBendInEasing
        performanceBendOut = settings.performanceBendOut
        performanceBendOutDuration = settings.performanceBendOutDuration
        performanceBendOutEasing = settings.performanceBendOutEasing
        performancePortamentoStart = settings.performancePortamentoStart
        performancePortamentoDuration = settings.performancePortamentoDuration
        performancePortamentoOffset = settings.performancePortamentoOffset
        performanceTrill = settings.performanceTrill
        performanceTrillLength = settings.performanceTrillLength
        performanceTrillDuration = settings.performanceTrillDuration
        performanceOffset = settings.performanceOffset
        performanceVibrato = settings.performanceVibrato
        performanceVibratoRate = settings.performanceVibratoRate
        performanceVibratoWave = settings.performanceVibratoWave
        bendDuration = settings.bendDuration
        amplitudeBendDuration = settings.amplitudeBendDuration
        bendOffset = settings.bendOffset
        amplitudeBendOffset = settings.amplitudeBendOffset
        fadeFrames = settings.fadeFrames

        if wave is None:
            wave = self.waveShape
        if pitch is None:
            pitch = self.pitch
        if vibratoRate is None:
            vibratoRate = self.vibratoRate
        if vibratoWave is None:
            vibratoWave = self.vibratoWave
        if performanceVibratoRate is None:
            performanceVibratoRate = self.vibratoRate
        if performanceVibratoWave is None:
            performanceVibratoWave = self.vibratoWave
        if tremoloRate is None:
            tremoloRate = self.tremoloRate
        if tremoloWave is None:
            tremoloWave = self.tremoloWave
        if modWave is None:
            modWave = self.oscillator.Sine
        amplitude = max(0.0, amplitude)
        if amplitudeBend is not None:
            amplitudeBend = max(0.0, min(1.0, amplitudeBend))
        vibrato = max(0.0, vibrato)
        performanceVibrato = max(0.0, performanceVibrato)
        tremolo = max(0.0, min(1.0, tremolo))
        modDepth = max(0.0, modDepth)
        if modFreq is not None:
            modFreq = max(0.0, modFreq * pitch)
        count = max(0, int(self.SAMPLE_RATE * duration))
        if bendDuration is None:
            bendDuration = duration
        if amplitudeBendDuration is None:
            amplitudeBendDuration = duration
        bendDuration = max(0.0, bendDuration)
        amplitudeBendDuration = max(0.0, amplitudeBendDuration)
        bendOffset = max(0.0, bendOffset)
        amplitudeBendOffset = max(0.0, amplitudeBendOffset)
        scopedDuration = max(0.0, scopedDuration)
        bendInDuration = (
            0.0 if bendIn is None
            else min(scopedDuration, max(0.0, bendInDuration))
        )
        bendOutDuration = (
            0.0 if bendOut is None
            else min(scopedDuration, max(0.0, bendOutDuration))
        )
        scopedBendDuration = bendInDuration + bendOutDuration
        if scopedBendDuration > scopedDuration and scopedBendDuration > 0.0:
            durationScale = scopedDuration / scopedBendDuration
            bendInDuration *= durationScale
            bendOutDuration *= durationScale
        if performanceBendDuration is None:
            performanceBendDuration = duration
        performanceBendDuration = max(0.0, performanceBendDuration)
        performanceBendOffset = max(0.0, performanceBendOffset)
        performanceBendInDuration = (
            0.0 if performanceBendIn is None
            else min(
                performanceBendDuration, max(0.0, performanceBendInDuration)
            )
        )
        performanceBendOutDuration = (
            0.0 if performanceBendOut is None
            else min(
                performanceBendDuration, max(0.0, performanceBendOutDuration)
            )
        )
        performanceScopedDuration = (
            performanceBendInDuration + performanceBendOutDuration
        )
        if (
                performanceScopedDuration > performanceBendDuration
                and performanceScopedDuration > 0.0
                ):
            durationScale = performanceBendDuration / performanceScopedDuration
            performanceBendInDuration *= durationScale
            performanceBendOutDuration *= durationScale
        performancePortamentoDuration = max(0.0, performancePortamentoDuration)
        performancePortamentoOffset = max(0.0, performancePortamentoOffset)
        if performanceTrillDuration is None:
            performanceTrillDuration = duration
        performanceTrillLength = max(0.0, performanceTrillLength)
        performanceTrillDuration = max(0.0, performanceTrillDuration)
        performanceOffset = max(0.0, performanceOffset)
        if fadeFrames is None:
            fade = min(int(self.SAMPLE_RATE * 0.003), count // 2)
        else:
            fade = max(0, int(fadeFrames))

        samples = np.empty(count, dtype = np.float64)
        isNoiseWave = self.oscillator.IsNoiseWave(wave)
        phase = oscillatorPhase
        startFreq = freq * pitch
        if isNoiseWave:
            startFreq = max(0.0, startFreq)
        else:
            startFreq = max(self.MIN_FREQ, startFreq)
            if phaseDegrees is not None:
                phase = ((phaseDegrees / 360.0) % 1.0) - (startFreq / self.SAMPLE_RATE)

        targetPerformanceFreq = startFreq
        performancePortamentoStartFreq = startFreq
        hasPerformancePortamento = (
            performancePortamentoStart is not None
            and performancePortamentoStart > 0.0
            and performancePortamentoDuration > 0.0
            and startFreq > 0.0
        )
        if hasPerformancePortamento:
            performancePortamentoStartFreq = max(
                self.MIN_FREQ, performancePortamentoStart * pitch
            )
        stepBendRatios = np.ones(1, dtype = np.float64)
        if performanceBend is not None:
            targetPerformanceFreq = performanceBend * pitch
            if performanceBendStepped and startFreq > 0.0:
                minimumTarget = 0.0 if isNoiseWave else self.MIN_FREQ
                targetPerformanceFreq = max(minimumTarget, targetPerformanceFreq)
                stepBendRatios = np.asarray(
                    PerformanceFrequency.GetStepBendRatios(
                        startFreq, targetPerformanceFreq, performanceBendRatios
                    ),
                    dtype = np.float64
                )

        waveId = self.oscillator.GetWaveId(wave)
        canVectorize = (
            not isNoiseWave
            and waveId is not None
            and vibrato <= 0.0
            and performanceVibrato <= 0.0
            and tremolo <= 0.0
            and (modFreq is None or modDepth <= 0.0 or modFreq <= 0.0)
            and bend is None
            and bendIn is None
            and bendOut is None
            and performanceBend is None
            and performanceBendIn is None
            and performanceBendOut is None
            and not hasPerformancePortamento
            and performanceTrill is None
            and amplitudeBend is None
        )

        if canVectorize and count > 0:
            phaseIncrement = startFreq / self.SAMPLE_RATE
            phases = phase + (np.arange(1, count + 1, dtype = np.float64) * phaseIncrement)
            samples = self.oscillator.RenderBuiltIn(waveId, phases, phaseIncrement)

            samples *= amplitude
            if fade > 0:
                if fadeIn:
                    fadeInGains = np.zeros(1, dtype = np.float64) if fade == 1 else np.linspace(
                        0.0, 1.0, fade, dtype = np.float64
                    )
                    samples[:fade] *= fadeInGains
                if fadeOut:
                    fadeOutGains = np.zeros(1, dtype = np.float64) if fade == 1 else np.linspace(
                        1.0, 0.0, fade, dtype = np.float64
                    )
                    samples[-fade:] *= fadeOutGains

            vibratoPhase += ((2.0 * math.pi * vibratoRate * count) / self.SAMPLE_RATE)
            phase += phaseIncrement * count
            samples = self.ApplyScopedFades(
                samples, scopedDuration, bendOffset,
                fadeInDuration, fadeInEasing,
                fadeOutDuration, fadeOutEasing
            )
            return samples, vibratoPhase, phase, modPhase

        vibratoWaveId = self.oscillator.GetWaveId(vibratoWave)
        performanceVibratoWaveId = self.oscillator.GetWaveId(performanceVibratoWave)
        tremoloWaveId = self.oscillator.GetWaveId(tremoloWave)
        modWaveId = self.oscillator.GetWaveId(modWave)
        modIsActive = (modFreq is not None and modDepth > 0.0 and modFreq > 0.0)
        canAccelerate = (
            ChirpKernels.NUMBA_ENABLED
            and not isNoiseWave
            and waveId is not None
            and vibratoWaveId is not None
            and performanceVibratoWaveId is not None
            and tremoloWaveId is not None
            and (not modIsActive or modWaveId is not None)
            and (bend is None or Easing.IsBuiltIn(bendEasing))
            and (bendIn is None or Easing.IsBuiltIn(bendInEasing))
            and (bendOut is None or Easing.IsBuiltIn(bendOutEasing))
            and (performanceBend is None or Easing.IsBuiltIn(performanceBendEasing))
            and (
                performanceBendIn is None
                or Easing.IsBuiltIn(performanceBendInEasing)
            )
            and (
                performanceBendOut is None
                or Easing.IsBuiltIn(performanceBendOutEasing)
            )
            and (amplitudeBend is None or Easing.IsBuiltIn(amplitudeEasing))
        )

        if canAccelerate:
            hasBend = bend is not None
            targetFreq = bend * pitch if hasBend else startFreq
            hasBendIn = bendIn is not None
            bendInFreq = bendIn * pitch if hasBendIn else startFreq
            hasBendOut = bendOut is not None
            bendOutFreq = bendOut * pitch if hasBendOut else startFreq

            hasPerformanceBend = performanceBend is not None
            hasPerformanceBendIn = performanceBendIn is not None
            performanceBendInFreq = (
                performanceBendIn * pitch if hasPerformanceBendIn else startFreq
            )
            hasPerformanceBendOut = performanceBendOut is not None
            performanceBendOutFreq = (
                performanceBendOut * pitch if hasPerformanceBendOut else startFreq
            )
            hasAmplitudeBend = amplitudeBend is not None
            targetAmplitude = (amplitudeBend if hasAmplitudeBend else amplitude)
            bendEasingId = (ChirpKernels.GetEasingId(bendEasing) if hasBend else ChirpKernels.EASING_LINEAR)
            bendInEasingId = (
                ChirpKernels.GetEasingId(bendInEasing)
                if hasBendIn else ChirpKernels.EASING_LINEAR
            )
            bendOutEasingId = (
                ChirpKernels.GetEasingId(bendOutEasing)
                if hasBendOut else ChirpKernels.EASING_LINEAR
            )
            amplitudeEasingId = (ChirpKernels.GetEasingId(amplitudeEasing) if hasAmplitudeBend else ChirpKernels.EASING_LINEAR)
            performanceBendEasingId = (
                ChirpKernels.GetEasingId(performanceBendEasing)
                if hasPerformanceBend else ChirpKernels.EASING_LINEAR
            )
            performanceBendInEasingId = (
                ChirpKernels.GetEasingId(performanceBendInEasing)
                if hasPerformanceBendIn else ChirpKernels.EASING_LINEAR
            )
            performanceBendOutEasingId = (
                ChirpKernels.GetEasingId(performanceBendOutEasing)
                if hasPerformanceBendOut else ChirpKernels.EASING_LINEAR
            )
            samples, vibratoPhase, phase, modPhase = ChirpKernels.MakeTone(
                ChirpKernels.KernelOscillatorSettings(
                    count = count,
                    sampleRate = self.SAMPLE_RATE,
                    minFreq = self.MIN_FREQ,
                    startFreq = startFreq,
                    waveId = waveId,
                    oscillatorPhase = phase
                ),
                ChirpKernels.KernelAmplitudeSettings(
                    amplitude = amplitude,
                    hasBend = hasAmplitudeBend,
                    target = targetAmplitude,
                    easingId = amplitudeEasingId,
                    duration = amplitudeBendDuration,
                    offset = amplitudeBendOffset
                ),
                ChirpKernels.KernelVibratoSettings(
                    depth = vibrato,
                    rate = vibratoRate,
                    phase = vibratoPhase,
                    waveId = vibratoWaveId,
                    performanceDepth = performanceVibrato,
                    performanceRate = performanceVibratoRate,
                    performanceWaveId = performanceVibratoWaveId,
                    performanceOffset = performanceOffset
                ),
                ChirpKernels.KernelTremoloSettings(
                    depth = tremolo,
                    rate = tremoloRate,
                    phase = tremoloPhase,
                    waveId = tremoloWaveId
                ),
                ChirpKernels.KernelModulationSettings(
                    freq = 0.0 if modFreq is None else modFreq,
                    depth = modDepth,
                    phase = modPhase,
                    waveId = ChirpKernels.WAVE_SINE if modWaveId is None else modWaveId
                ),
                ChirpKernels.KernelBendSettings(
                    hasBend = hasBend,
                    targetFreq = targetFreq,
                    easingId = bendEasingId,
                    duration = bendDuration,
                    offset = bendOffset,
                    hasBendIn = hasBendIn,
                    bendInFreq = bendInFreq,
                    bendInEasingId = bendInEasingId,
                    bendInDuration = bendInDuration,
                    hasBendOut = hasBendOut,
                    bendOutFreq = bendOutFreq,
                    bendOutEasingId = bendOutEasingId,
                    bendOutDuration = bendOutDuration,
                    scopedDuration = scopedDuration,
                    hasPerformanceBend = hasPerformanceBend,
                    targetPerformanceFreq = targetPerformanceFreq,
                    performanceEasingId = performanceBendEasingId,
                    performanceStepped = performanceBendStepped,
                    performanceRatios = stepBendRatios,
                    performanceDuration = performanceBendDuration,
                    performanceOffset = performanceBendOffset,
                    hasPerformanceBendIn = hasPerformanceBendIn,
                    performanceBendInFreq = performanceBendInFreq,
                    performanceBendInEasingId = performanceBendInEasingId,
                    performanceBendInDuration = performanceBendInDuration,
                    hasPerformanceBendOut = hasPerformanceBendOut,
                    performanceBendOutFreq = performanceBendOutFreq,
                    performanceBendOutEasingId = performanceBendOutEasingId,
                    performanceBendOutDuration = performanceBendOutDuration
                ),
                ChirpKernels.KernelPortamentoSettings(
                    enabled = hasPerformancePortamento,
                    startFreq = performancePortamentoStartFreq,
                    duration = performancePortamentoDuration,
                    offset = performancePortamentoOffset
                ),
                ChirpKernels.KernelTrillSettings(
                    enabled = performanceTrill is not None,
                    targetFreq = startFreq if performanceTrill is None else performanceTrill * pitch,
                    length = performanceTrillLength,
                    duration = performanceTrillDuration
                ),
                ChirpKernels.KernelFadeSettings(
                    frames = fade,
                    fadeIn = fadeIn,
                    fadeOut = fadeOut
                )
            )
            samples = self.ApplyScopedFades(
                samples, scopedDuration, bendOffset,
                fadeInDuration, fadeInEasing,
                fadeOutDuration, fadeOutEasing
            )
            return samples, vibratoPhase, phase, modPhase

        vibratoIncrement = ((2.0 * math.pi * vibratoRate) / self.SAMPLE_RATE)
        performanceVibratoIncrement = (
            (2.0 * math.pi * performanceVibratoRate) / self.SAMPLE_RATE
        )
        performanceVibratoPhase = (
            2.0 * math.pi * performanceVibratoRate * performanceOffset
        )
        tremoloIncrement = ((2.0 * math.pi * tremoloRate) / self.SAMPLE_RATE)
        modIncrement = (0.0 if modFreq is None else ((2.0 * math.pi * modFreq) / self.SAMPLE_RATE))

        bendFrames = max(0, int(self.SAMPLE_RATE * bendDuration))
        bendOffsetFrames = round(bendOffset * self.SAMPLE_RATE)
        bendDivisor = max(1, bendFrames - 1)
        scopedFrames = max(0, int(self.SAMPLE_RATE * scopedDuration))
        bendInFrames = max(0, int(self.SAMPLE_RATE * bendInDuration))
        bendInDivisor = max(1, bendInFrames - 1)
        bendOutFrames = max(0, int(self.SAMPLE_RATE * bendOutDuration))
        bendOutStart = max(0, scopedFrames - bendOutFrames)
        bendOutDivisor = max(1, bendOutFrames - 1)
        amplitudeFrames = max(0, int(self.SAMPLE_RATE * amplitudeBendDuration))
        amplitudeOffsetFrames = round(amplitudeBendOffset * self.SAMPLE_RATE)
        amplitudeDivisor = max(1, amplitudeFrames - 1)
        portamentoFrames = max(0, int(self.SAMPLE_RATE * performancePortamentoDuration))
        portamentoOffsetFrames = round(performancePortamentoOffset * self.SAMPLE_RATE)
        portamentoDivisor = max(1, portamentoFrames - 1)
        performanceFrames = max(0, int(self.SAMPLE_RATE * performanceBendDuration))
        performanceBendOffsetFrames = round(performanceBendOffset * self.SAMPLE_RATE)
        performanceDivisor = max(1, performanceFrames - 1)
        performanceBendInFrames = max(
            0, int(self.SAMPLE_RATE * performanceBendInDuration)
        )
        performanceBendInDivisor = max(1, performanceBendInFrames - 1)
        performanceBendOutFrames = max(
            0, int(self.SAMPLE_RATE * performanceBendOutDuration)
        )
        performanceBendOutStart = max(
            0, performanceFrames - performanceBendOutFrames
        )
        performanceBendOutDivisor = max(1, performanceBendOutFrames - 1)
        trillFrames = max(1, int(self.SAMPLE_RATE * performanceTrillLength))
        gateFrames = max(0, int(self.SAMPLE_RATE * performanceTrillDuration))
        performanceOffsetFrames = round(performanceOffset * self.SAMPLE_RATE)
        amplitudeEasingFunction = Easing.Resolve(amplitudeEasing) if amplitudeBend is not None else None
        bendEasingFunction = Easing.Resolve(bendEasing) if bend is not None else None
        bendInEasingFunction = (
            Easing.Resolve(bendInEasing) if bendIn is not None else None
        )
        bendOutEasingFunction = (
            Easing.Resolve(bendOutEasing) if bendOut is not None else None
        )
        performanceBendEasingFunction = (
            Easing.Resolve(performanceBendEasing) if performanceBend is not None else None
        )
        performanceBendInEasingFunction = (
            Easing.Resolve(performanceBendInEasing)
            if performanceBendIn is not None else None
        )
        performanceBendOutEasingFunction = (
            Easing.Resolve(performanceBendOutEasing)
            if performanceBendOut is not None else None
        )
        for i in range(count):
            bendFrame = bendOffsetFrames + i
            bendPercent = min(1.0, bendFrame / bendDivisor)
            startAmplitude = amplitude
            currentAmplitude = startAmplitude
            if amplitudeBend is not None:
                targetAmplitude = amplitudeBend
                amplitudeFrame = amplitudeOffsetFrames + i
                amplitudePercent = min(1.0, amplitudeFrame / amplitudeDivisor)
                amplitudePercent = Easing.ApplyResolved(
                    amplitudePercent, amplitudeEasingFunction
                )
                currentAmplitude = startAmplitude + ((targetAmplitude - startAmplitude) * amplitudePercent)
            bentFreq = startFreq
            if bend is not None:
                bendPercent = Easing.ApplyResolved(bendPercent, bendEasingFunction)
                targetFreq = bend * pitch
                bentFreq += (targetFreq - startFreq) * bendPercent
            elif bendIn is not None or bendOut is not None:
                scopedFrame = bendOffsetFrames + i
                if bendIn is not None and scopedFrame < bendInFrames:
                    bendInPercent = min(1.0, scopedFrame / bendInDivisor)
                    bendInPercent = Easing.ApplyResolved(
                        bendInPercent, bendInEasingFunction
                    )
                    bendInFreq = bendIn * pitch
                    bentFreq = bendInFreq + (
                        (startFreq - bendInFreq) * bendInPercent
                    )
                elif bendOut is not None and scopedFrame >= bendOutStart:
                    bendOutPercent = 1.0 if bendOutFrames == 1 else min(
                        1.0, (scopedFrame - bendOutStart) / bendOutDivisor
                    )
                    bendOutPercent = Easing.ApplyResolved(
                        bendOutPercent, bendOutEasingFunction
                    )
                    bendOutFreq = bendOut * pitch
                    bentFreq = startFreq + (
                        (bendOutFreq - startFreq) * bendOutPercent
                    )
            if hasPerformancePortamento:
                portamentoFrame = portamentoOffsetFrames + i
                portamentoPercent = min(1.0, portamentoFrame / portamentoDivisor)
                portamentoFreq = performancePortamentoStartFreq * (
                    (startFreq / performancePortamentoStartFreq) ** portamentoPercent
                )
                bentFreq *= portamentoFreq / startFreq
            if performanceBend is not None:
                performanceFrame = performanceBendOffsetFrames + i
                performancePercent = min(1.0, performanceFrame / performanceDivisor)
                performancePercent = Easing.ApplyResolved(
                    performancePercent, performanceBendEasingFunction
                )
                if performanceBendStepped and startFreq > 0.0:
                    performancePercent = max(0.0, min(1.0, performancePercent))
                    ratioIndex = math.floor(len(stepBendRatios) * performancePercent)
                    ratioIndex = max(0, min(len(stepBendRatios) - 1, ratioIndex))
                    if targetPerformanceFreq >= startFreq:
                        performanceFreq = startFreq * stepBendRatios[ratioIndex]
                    else:
                        performanceFreq = startFreq / stepBendRatios[ratioIndex]
                else:
                    performanceFreq = startFreq + (
                        (targetPerformanceFreq - startFreq) * performancePercent
                    )
                if startFreq != 0.0:
                    bentFreq *= performanceFreq / startFreq
            elif performanceBendIn is not None or performanceBendOut is not None:
                performanceFrame = performanceBendOffsetFrames + i
                performanceFreq = startFreq
                if (
                        performanceBendIn is not None
                        and performanceFrame < performanceBendInFrames
                        ):
                    bendInPercent = min(
                        1.0, performanceFrame / performanceBendInDivisor
                    )
                    bendInPercent = Easing.ApplyResolved(
                        bendInPercent, performanceBendInEasingFunction
                    )
                    performanceBendInFreq = performanceBendIn * pitch
                    performanceFreq = performanceBendInFreq + (
                        (startFreq - performanceBendInFreq) * bendInPercent
                    )
                elif (
                        performanceBendOut is not None
                        and performanceFrame >= performanceBendOutStart
                        ):
                    bendOutPercent = (
                        1.0 if performanceBendOutFrames == 1 else min(
                            1.0,
                            (performanceFrame - performanceBendOutStart)
                            / performanceBendOutDivisor
                        )
                    )
                    bendOutPercent = Easing.ApplyResolved(
                        bendOutPercent, performanceBendOutEasingFunction
                    )
                    performanceBendOutFreq = performanceBendOut * pitch
                    performanceFreq = startFreq + (
                        (performanceBendOutFreq - startFreq) * bendOutPercent
                    )
                if startFreq != 0.0:
                    bentFreq *= performanceFreq / startFreq

            if performanceTrill is not None and performanceTrillLength > 0.0 and startFreq > 0.0:
                trillFrame = min(
                    performanceOffsetFrames + i,
                    max(0, gateFrames - 1)
                )
                if (trillFrame // trillFrames) % 2 == 1:
                    bentFreq *= (performanceTrill * pitch) / startFreq

            vibratoCents = self.oscillator.GetLfoValue(vibratoWave, vibratoPhase, vibratoIncrement) * vibrato
            performanceVibratoCents = self.oscillator.GetLfoValue(
                performanceVibratoWave,
                performanceVibratoPhase,
                performanceVibratoIncrement
            ) * performanceVibrato
            vibratoMultiplier = 2.0 ** ((vibratoCents + performanceVibratoCents) / 1200.0)
            currentFreq = bentFreq * vibratoMultiplier
            currentTremoloPhase = tremoloPhase + ((2.0 * math.pi * tremoloRate * i) / self.SAMPLE_RATE)
            tremoloValue = (self.oscillator.GetLfoValue(tremoloWave, currentTremoloPhase, tremoloIncrement) + 1.0) * 0.5
            tremoloGain = 1.0 - (tremolo * tremoloValue)

            if isNoiseWave:
                currentFreq = max(0.0, currentFreq)
                sample = wave(i / self.SAMPLE_RATE, currentFreq)
            else:
                currentFreq = max(self.MIN_FREQ, currentFreq)
                phase += currentFreq / self.SAMPLE_RATE
                carrierPhase = phase
                if modFreq is not None and modDepth > 0.0 and modFreq > 0.0:
                    modValue = self.oscillator.GetLfoValue(modWave, modPhase, modIncrement)
                    carrierPhase += (modValue * modDepth) / (2.0 * math.pi)
                    modPhase += modIncrement
                sample = wave(carrierPhase / currentFreq, currentFreq)

            vibratoPhase += vibratoIncrement
            performanceVibratoPhase += performanceVibratoIncrement

            if fade > 0:
                if fadeIn and i < fade:
                    sample *= i / max(1, fade - 1)
                elif fadeOut and i >= count - fade:
                    sample *= (count - i - 1) / max(1, fade - 1)

            samples[i] = sample * currentAmplitude * tremoloGain

        samples = self.ApplyScopedFades(
            samples, scopedDuration, bendOffset,
            fadeInDuration, fadeInEasing,
            fadeOutDuration, fadeOutEasing
        )
        return samples, vibratoPhase, phase, modPhase

    def GetSoundSamples(self, sound):
        hasSamples = hasattr(sound, "_samples")
        if (not hasattr(sound, "channels") or (not hasSamples and not hasattr(sound, "pcm"))):
            raise ValueError("Expected a Sound object in sound command")

        dsp = ChirpDSP(channels = sound.channels)
        if hasattr(sound, "_samples"):
            samples = np.asarray(sound._samples, dtype = np.float64).reshape(-1).copy()
        else:
            samples = dsp.BytesToSamples(sound.pcm)

        if sound.channels == self.channels:
            return samples

        if self.channels == 1:
            return dsp.ApplySoundMono(samples)

        return dsp.ApplySoundStereo(samples)

    def ApplyControlCommand(
            self, control, wave, pitch, tempo, vibratoDepth, vibratoRate,
            vibratoWave, tremoloDepth, tremoloRate, tremoloWave
        ):
        if isinstance(control, WaveControl):
            wave = self.oscillator.GetWave(control.wave)
        elif isinstance(control, PitchControl):
            pitch = max(0.1, control.amount)
        elif isinstance(control, TempoControl):
            tempo = max(1.0, control.bpm)
        elif isinstance(control, SecondsControl):
            tempo = None
        elif isinstance(control, VibratoDepthControl):
            vibratoDepth = max(0.0, control.depth)
        elif isinstance(control, VibratoRateControl):
            vibratoRate = max(0.0, control.rate)
        elif isinstance(control, VibratoWaveControl):
            vibratoWave = self.oscillator.GetWave(control.wave)
        elif isinstance(control, TremoloDepthControl):
            tremoloDepth = max(0.0, min(1.0, control.depth))
        elif isinstance(control, TremoloRateControl):
            tremoloRate = max(0.0, control.rate)
        elif isinstance(control, TremoloWaveControl):
            tremoloWave = self.oscillator.GetWave(control.wave)
        else:
            raise ValueError("Unknown control command: " + str(control))

        return wave, pitch, tempo, vibratoDepth, vibratoRate, vibratoWave, tremoloDepth, tremoloRate, tremoloWave

    def ParseNote(
            self, note, wave, pitch, vibratoDepth = Vibrato.LIGHT, vibratoRate = 6.0,
            vibratoWave = None, tremoloDepth = Tremolo.LIGHT, tremoloRate = 6.0,
            tremoloWave = None
            ):

        if isinstance(note, Tone):
            amplitude = max(0.0, note.amplitude)
            vibrato = Vibrato.NONE
            toneVibratoRate = vibratoRate
            toneVibratoWave = vibratoWave
            modFreq = None
            modDepth = 0.0
            modWave = self.oscillator.Sine
            tremolo = Tremolo.NONE
            toneTremoloRate = tremoloRate
            toneTremoloWave = tremoloWave
            autoPanEnabled = note.autoPanEnabled
            autoPanDepth = max(0.0, min(1.0, note.autoPanDepth))
            autoPanRate = max(0.0, note.autoPanRate)
            autoPanWave = self.oscillator.GetWave(note.autoPanWave)
            autoPanOffset = note.autoPanOffset % 360.0
            performanceBend = None
            performanceBendEasing = "linear"
            performanceBendStepped = False
            performanceBendRatios = None
            performanceBendDuration = note.duration
            performanceBendIn = None
            performanceBendInDuration = 0.0
            performanceBendInEasing = "linear"
            performanceBendOut = None
            performanceBendOutDuration = 0.0
            performanceBendOutEasing = "linear"
            performancePortamentoStart = None
            performancePortamentoDuration = 0.0
            performanceTrill = None
            performanceTrillLength = 0.0
            performanceTrillDuration = note.duration
            performanceVibrato = Vibrato.NONE
            performanceVibratoRate = vibratoRate
            performanceVibratoWave = vibratoWave

            if note.wave is not None:
                wave = self.oscillator.GetWave(note.wave)
            isNoiseWave = self.oscillator.IsNoiseWave(wave)

            if note.performanceFrequency is not None:
                performance = note.performanceFrequency
                performanceBend = performance.ResolveBend(isNoiseWave)
                performanceBendEasing = performance.bendEasing
                performanceBendStepped = performance.bendStepped
                performanceBendRatios = performance.bendRatios
                performanceBendDuration = performance.duration
                performanceBendIn = performance.ResolveBendIn(isNoiseWave)
                performanceBendInDuration = performance.bendInDuration
                performanceBendInEasing = performance.bendInEasing
                performanceBendOut = performance.ResolveBendOut(isNoiseWave)
                performanceBendOutDuration = performance.bendOutDuration
                performanceBendOutEasing = performance.bendOutEasing
                performancePortamentoStart = performance.ResolvePortamentoStart(
                    isNoiseWave
                )
                performancePortamentoDuration = performance.portamentoDuration
                performanceTrill = performance.ResolveTrill(isNoiseWave)
                performanceTrillLength = performance.trillLength
                performanceTrillDuration = performance.duration
                if performance.vibratoEnabled:
                    depth = vibratoDepth if performance.vibratoDepth is None else performance.vibratoDepth
                    rate = vibratoRate if performance.vibratoRate is None else performance.vibratoRate
                    lfoWave = vibratoWave
                    if performance.vibratoWave is not None:
                        lfoWave = self.oscillator.GetWave(performance.vibratoWave)
                    if lfoWave is None:
                        lfoWave = self.vibratoWave
                    performanceVibrato = max(0.0, depth)
                    performanceVibratoRate = max(0.0, rate)
                    performanceVibratoWave = lfoWave

            if note.vibratoEnabled:
                depth = vibratoDepth if note.vibratoDepth is None else note.vibratoDepth
                rate = vibratoRate if note.vibratoRate is None else note.vibratoRate
                lfoWave = vibratoWave if note.vibratoWave is None else self.oscillator.GetWave(note.vibratoWave)
                if lfoWave is None:
                    lfoWave = self.vibratoWave
                vibrato = max(0.0, depth)
                toneVibratoRate = max(0.0, rate)
                toneVibratoWave = lfoWave

            if note.tremoloEnabled:
                depth = tremoloDepth if note.tremoloDepth is None else note.tremoloDepth
                rate = tremoloRate if note.tremoloRate is None else note.tremoloRate
                lfoWave = tremoloWave if note.tremoloWave is None else self.oscillator.GetWave(note.tremoloWave)
                if lfoWave is None:
                    lfoWave = self.tremoloWave
                tremolo = max(0.0, min(1.0, depth))
                toneTremoloRate = max(0.0, rate)
                toneTremoloWave = lfoWave

            if note.modEnabled:
                depth = max(0.0, note.modDepth)
                if depth > 0.0:
                    frequency = max(0.0, note.modFreq)
                    if frequency > 0.0:
                        modFreq = frequency
                        modDepth = depth
                        modWave = self.oscillator.GetWave(note.modWave)
                        if modWave is None:
                            modWave = self.oscillator.Sine

            pan = max(-1.0, min(1.0, note.pan))
            phaseDegrees = note.phaseDegrees
            bend = note.bend
            if isinstance(bend, PerformanceFrequency):
                bend = bend.value
            elif (
                    bend is not None
                    and not isNoiseWave
                    and 0.0 < bend < self.MIN_FREQ
                    ):
                bend = note.freq * bend
            bendEasing = note.bendEasing
            bendIn = note.bendInTarget
            if isinstance(bendIn, PerformanceFrequency):
                bendIn = bendIn.value
            elif (
                    bendIn is not None
                    and not isNoiseWave
                    and note.freq is not None
                    and 0.0 < bendIn < self.MIN_FREQ
                    ):
                bendIn = note.freq * bendIn
            bendOut = note.bendOutTarget
            if isinstance(bendOut, PerformanceFrequency):
                bendOut = bendOut.value
            elif (
                    bendOut is not None
                    and not isNoiseWave
                    and note.freq is not None
                    and 0.0 < bendOut < self.MIN_FREQ
                    ):
                bendOut = note.freq * bendOut
            amplitudeBend = None
            amplitudeEasing = "linear"
            unisonVoices = max(1, int(note.unisonVoices))
            unisonDetune = max(0.0, note.unisonDetune)
            unisonSpread = max(0.0, min(1.0, note.unisonSpread))

            if note.fadeTarget is not None:
                amplitudeBend = max(0.0, min(1.0, note.fadeTarget))
                amplitudeEasing = note.fadeEasing

            return ParsedTone(
                freq = note.freq,
                duration = note.duration,
                wave = wave,
                pitch = pitch,
                amplitude = amplitude,
                vibrato = vibrato,
                vibratoRate = toneVibratoRate,
                vibratoWave = toneVibratoWave,
                tremolo = tremolo,
                tremoloRate = toneTremoloRate,
                tremoloWave = toneTremoloWave,
                modFreq = modFreq,
                modDepth = modDepth,
                modWave = modWave,
                pan = pan,
                autoPanEnabled = autoPanEnabled,
                autoPanDepth = autoPanDepth,
                autoPanRate = autoPanRate,
                autoPanWave = autoPanWave,
                autoPanOffset = autoPanOffset,
                bend = bend,
                bendEasing = bendEasing,
                bendIn = bendIn,
                bendInDuration = note.bendInDuration,
                bendInEasing = note.bendInEasing,
                bendOut = bendOut,
                bendOutDuration = note.bendOutDuration,
                bendOutEasing = note.bendOutEasing,
                amplitudeBend = amplitudeBend,
                amplitudeEasing = amplitudeEasing,
                fadeInDuration = note.fadeInDuration,
                fadeInEasing = note.fadeInEasing,
                fadeOutDuration = note.fadeOutDuration,
                fadeOutEasing = note.fadeOutEasing,
                phaseDegrees = phaseDegrees,
                unisonVoices = unisonVoices,
                unisonDetune = unisonDetune,
                unisonSpread = unisonSpread,
                performanceBend = performanceBend,
                performanceBendEasing = performanceBendEasing,
                performanceBendStepped = performanceBendStepped,
                performanceBendRatios = performanceBendRatios,
                performanceBendDuration = performanceBendDuration,
                performanceBendIn = performanceBendIn,
                performanceBendInDuration = performanceBendInDuration,
                performanceBendInEasing = performanceBendInEasing,
                performanceBendOut = performanceBendOut,
                performanceBendOutDuration = performanceBendOutDuration,
                performanceBendOutEasing = performanceBendOutEasing,
                performancePortamentoStart = performancePortamentoStart,
                performancePortamentoDuration = performancePortamentoDuration,
                performanceTrill = performanceTrill,
                performanceTrillLength = performanceTrillLength,
                performanceTrillDuration = performanceTrillDuration,
                performanceVibrato = performanceVibrato,
                performanceVibratoRate = performanceVibratoRate,
                performanceVibratoWave = performanceVibratoWave
            )

        raise TypeError("Expected Tone, got: " + str(note))

    def MonoToOutputSamples(
            self, samples, pan = 0.0, autoPanEnabled = False,
            autoPanDepth = 1.0, autoPanRate = 1.0,
            autoPanWave = "Sine", autoPanOffset = 0.0
            ):
        samples = np.asarray(samples, dtype = np.float64).reshape(-1)
        if self.channels == 1:
            return samples

        if autoPanEnabled:
            dsp = ChirpDSP(channels = 1)
            return dsp.ApplySoundAutoPan(
                samples, autoPanDepth, autoPanRate,
                autoPanWave, autoPanOffset, pan
            )

        pan = max(-1.0, min(1.0, pan))
        angle = (pan + 1.0) * (math.pi * 0.25)
        leftGain = math.cos(angle)
        rightGain = math.sin(angle)
        stereo = np.empty(len(samples) * 2, dtype = np.float64)
        stereo[0::2] = samples * leftGain
        stereo[1::2] = samples * rightGain
        return stereo

    def RenderEventsAreCompatible(self, previousEvent, event):
        if previousEvent is None or event.phaseDegrees is not None:
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

        sameArpeggio = (
            event.arpeggioGroup is not None
            and event.arpeggioGroup is previousEvent.arpeggioGroup
        )
        properties = (
            "pitch", "amplitude", "pan", "bend", "amplitudeBend",
            "unisonVoices", "unisonDetune", "unisonSpread",
            "performanceBend", "performanceBendStepped", "performanceBendRatios",
            "performanceBendDuration", "performanceBendIn",
            "performanceBendInDuration", "performanceBendOut",
            "performanceBendOutDuration", "performanceTrill",
            "performanceTrillLength", "performanceTrillDuration",
            "performanceVibrato", "autoPanEnabled", "autoPanDepth",
            "autoPanRate", "autoPanOffset"
        )
        if not sameArpeggio:
            properties = ("freq",) + properties
        for propertyName in properties:
            if getattr(previousEvent, propertyName) != getattr(event, propertyName):
                return False

        if sameArpeggio and previousEvent.amplitudeBend is not None:
            if not math.isclose(
                    previousEvent.amplitudeBend, event.amplitude,
                    rel_tol = 0.0, abs_tol = 1e-12
                    ):
                return False

        if event.bend is not None and previousEvent.bendEasing != event.bendEasing:
            return False
        if (
                event.performanceBend is not None
                and previousEvent.performanceBendEasing != event.performanceBendEasing
                ):
            return False
        if (
                event.performanceBendIn is not None
                and previousEvent.performanceBendInEasing != event.performanceBendInEasing
                ):
            return False
        if (
                event.performanceBendOut is not None
                and previousEvent.performanceBendOutEasing != event.performanceBendOutEasing
                ):
            return False
        if (
                event.amplitudeBend is not None
                and previousEvent.amplitudeEasing != event.amplitudeEasing
                ):
            return False

        waveProperties = ("wave",)
        if event.vibrato > 0.0 or previousEvent.vibrato > 0.0:
            waveProperties += ("vibratoWave",)
            if (
                    previousEvent.vibrato != event.vibrato
                    or previousEvent.vibratoRate != event.vibratoRate
                    ):
                return False
        if event.performanceVibrato > 0.0 or previousEvent.performanceVibrato > 0.0:
            waveProperties += ("performanceVibratoWave",)
            if previousEvent.performanceVibratoRate != event.performanceVibratoRate:
                return False
        if event.tremolo > 0.0 or previousEvent.tremolo > 0.0:
            waveProperties += ("tremoloWave",)
            if (
                    previousEvent.tremolo != event.tremolo
                    or previousEvent.tremoloRate != event.tremoloRate
                    ):
                return False
        if event.modFreq is not None or previousEvent.modFreq is not None:
            waveProperties += ("modWave",)
            if (
                    previousEvent.modFreq != event.modFreq
                    or previousEvent.modDepth != event.modDepth
                ):
                return False
        if event.autoPanEnabled or previousEvent.autoPanEnabled:
            waveProperties += ("autoPanWave",)

        for propertyName in waveProperties:
            previousValue = getattr(previousEvent, propertyName)
            currentValue = getattr(event, propertyName)
            previousWave = getattr(previousValue, "__func__", previousValue)
            currentWave = getattr(currentValue, "__func__", currentValue)
            if previousWave != currentWave:
                return False

        return True

    def ExpandToneArpeggio(self, note, duration):
        if not isinstance(note, Tone) or note.arpeggio is None or note.freq is None:
            return [(note, duration)]

        frequencies = note.arpeggio.GetFrequencies(note.freq)
        dynamics = note.arpeggio.dynamics.GetGains(len(frequencies))
        totalFrames = max(0, int(self.SAMPLE_RATE * duration))
        stepFrameLength = self.SAMPLE_RATE * float(note.arpeggio.step)
        segments = []
        offsetFrames = 0
        arpeggioIndex = 0

        while offsetFrames < totalFrames or totalFrames == 0:
            nextOffsetFrames = min(
                totalFrames,
                max(offsetFrames + 1, int(stepFrameLength * (arpeggioIndex + 1)))
            )
            segmentFrames = nextOffsetFrames - offsetFrames
            segmentDuration = segmentFrames / self.SAMPLE_RATE
            patternIndex = arpeggioIndex % len(frequencies)
            frequency = frequencies[patternIndex]
            segment = copy.copy(note)
            segment.arpeggio = None
            segment.duration = segmentDuration
            segment.amplitude *= dynamics[patternIndex]
            if segment.fadeTarget is not None:
                segment.fadeTarget *= dynamics[patternIndex]

            if note.performanceFrequency is not None and note.arpeggio.usesRatios:
                frequencyRatio = 1.0
                if note.freq != 0.0:
                    frequencyRatio = frequency / note.freq
                segment.performanceFrequency = note.performanceFrequency * frequencyRatio
                segment.freq = segment.performanceFrequency.value
            else:
                segment.performanceFrequency = None
                segment.freq = frequency

            segments.append((segment, segmentDuration))
            if totalFrames == 0:
                break
            offsetFrames = nextOffsetFrames
            arpeggioIndex += 1

        return segments

    def CreateToneEvent(
            self, note, duration, wave, pitch,
            vibratoDepth, vibratoRate, vibratoWave,
            tremoloDepth, tremoloRate, tremoloWave
            ):
        parsed = self.ParseNote(
            note,
            wave,
            pitch,
            vibratoDepth,
            vibratoRate,
            vibratoWave,
            tremoloDepth,
            tremoloRate,
            tremoloWave
        )

        frameCount = max(0, int(self.SAMPLE_RATE * duration))
        if parsed.freq is None:
            return SilenceRenderEvent(
                duration = duration,
                sampleCount = frameCount * self.channels
            )

        isNoise = self.oscillator.IsNoiseWave(parsed.wave)
        if isNoise and parsed.unisonVoices > 1:
            raise ValueError("Unison requires a pitched wave")

        return ToneRenderEvent(
            freq = parsed.freq,
            duration = duration,
            wave = parsed.wave,
            pitch = parsed.pitch,
            amplitude = parsed.amplitude,
            vibrato = parsed.vibrato,
            vibratoRate = parsed.vibratoRate,
            vibratoWave = parsed.vibratoWave,
            tremolo = parsed.tremolo,
            tremoloRate = parsed.tremoloRate,
            tremoloWave = parsed.tremoloWave,
            modFreq = parsed.modFreq,
            modDepth = parsed.modDepth,
            modWave = parsed.modWave,
            pan = parsed.pan,
            autoPanEnabled = parsed.autoPanEnabled,
            autoPanDepth = parsed.autoPanDepth,
            autoPanRate = parsed.autoPanRate,
            autoPanWave = parsed.autoPanWave,
            autoPanOffset = parsed.autoPanOffset,
            continueAutoPan = False,
            arpeggioGroup = None,
            bend = parsed.bend,
            bendEasing = parsed.bendEasing,
            bendDuration = duration,
            bendOffset = 0.0,
            bendIn = parsed.bendIn,
            bendInDuration = parsed.bendInDuration,
            bendInEasing = parsed.bendInEasing,
            bendOut = parsed.bendOut,
            bendOutDuration = parsed.bendOutDuration,
            bendOutEasing = parsed.bendOutEasing,
            amplitudeBend = parsed.amplitudeBend,
            amplitudeEasing = parsed.amplitudeEasing,
            amplitudeBendDuration = duration,
            amplitudeBendOffset = 0.0,
            fadeInDuration = parsed.fadeInDuration,
            fadeInEasing = parsed.fadeInEasing,
            fadeOutDuration = parsed.fadeOutDuration,
            fadeOutEasing = parsed.fadeOutEasing,
            scopedDuration = duration,
            phaseDegrees = parsed.phaseDegrees,
            unisonVoices = parsed.unisonVoices,
            unisonDetune = parsed.unisonDetune,
            unisonSpread = parsed.unisonSpread,
            performanceBend = parsed.performanceBend,
            performanceBendEasing = parsed.performanceBendEasing,
            performanceBendStepped = parsed.performanceBendStepped,
            performanceBendRatios = parsed.performanceBendRatios,
            performanceBendDuration = parsed.performanceBendDuration,
            performanceBendOffset = (
                0.0 if note.performanceFrequency is None
                else note.performanceFrequency.offset
            ),
            performanceBendIn = parsed.performanceBendIn,
            performanceBendInDuration = parsed.performanceBendInDuration,
            performanceBendInEasing = parsed.performanceBendInEasing,
            performanceBendOut = parsed.performanceBendOut,
            performanceBendOutDuration = parsed.performanceBendOutDuration,
            performanceBendOutEasing = parsed.performanceBendOutEasing,
            performancePortamentoStart = parsed.performancePortamentoStart,
            performancePortamentoDuration = parsed.performancePortamentoDuration,
            performancePortamentoOffset = 0.0,
            performanceTrill = parsed.performanceTrill,
            performanceTrillLength = parsed.performanceTrillLength,
            performanceTrillDuration = parsed.performanceTrillDuration,
            performanceOffset = 0.0,
            performanceVibrato = parsed.performanceVibrato,
            performanceVibratoRate = parsed.performanceVibratoRate,
            performanceVibratoWave = parsed.performanceVibratoWave,
            isNoise = isNoise,
            fadeIn = True,
            fadeOut = True,
            fadeFrames = min(int(self.SAMPLE_RATE * 0.003), frameCount // 2),
            sampleCount = frameCount * self.channels
        )

    def CompileSequence(self, recipe):
        wave = self.waveShape
        pitch = self.pitch
        tempo = None
        vibratoDepth = self.vibratoDepth
        vibratoRate = self.vibratoRate
        vibratoWave = self.vibratoWave
        tremoloDepth = self.tremoloDepth
        tremoloRate = self.tremoloRate
        tremoloWave = self.tremoloWave
        events = []

        for note in recipe:
            if isinstance(note, Control):
                if isinstance(note, InsertControl):
                    insertedSamples = self.GetSoundSamples(note.sound)
                    events.append(InsertRenderEvent(
                        samples = insertedSamples,
                        sampleCount = len(insertedSamples)
                    ))
                    continue

                wave, pitch, tempo, vibratoDepth, vibratoRate, vibratoWave, \
                tremoloDepth, tremoloRate, tremoloWave = \
                self.ApplyControlCommand(
                    note,
                    wave,
                    pitch,
                    tempo,
                    vibratoDepth,
                    vibratoRate,
                    vibratoWave,
                    tremoloDepth,
                    tremoloRate,
                    tremoloWave
                )
                continue

            duration = note.duration
            durationScale = 1.0
            if tempo is not None:
                durationScale = 4.0 * (60.0 / tempo)
                duration *= durationScale
            segments = self.ExpandToneArpeggio(note, duration)
            arpeggioGroup = object() if note.arpeggio is not None else None
            performanceOffset = 0.0
            for segment, segmentDuration in segments:
                if durationScale != 1.0:
                    segment = copy.copy(segment)
                    segment.bendInDuration *= durationScale
                    segment.bendOutDuration *= durationScale
                    segment.fadeInDuration *= durationScale
                    segment.fadeOutDuration *= durationScale
                event = self.CreateToneEvent(
                    segment,
                    segmentDuration,
                    wave,
                    pitch,
                    vibratoDepth,
                    vibratoRate,
                    vibratoWave,
                    tremoloDepth,
                    tremoloRate,
                    tremoloWave
                )
                if isinstance(event, ToneRenderEvent):
                    event.arpeggioGroup = arpeggioGroup
                    event.performanceBendOffset += performanceOffset
                    event.performancePortamentoOffset = performanceOffset
                    event.performanceOffset = performanceOffset
                events.append(event)
                performanceOffset += segmentDuration

        previousEvent = None
        for event in events:
            if not isinstance(event, ToneRenderEvent) or event.isNoise:
                previousEvent = None
                continue

            sameArpeggio = (
                previousEvent is not None
                and event.arpeggioGroup is not None
                and event.arpeggioGroup is previousEvent.arpeggioGroup
            )
            if sameArpeggio and event.autoPanEnabled:
                event.continueAutoPan = True

            if self.RenderEventsAreCompatible(previousEvent, event):
                previousEvent.fadeOut = False
                event.fadeIn = False
                event.continueAutoPan = event.autoPanEnabled

            previousEvent = event

        sampleCount = sum(event.sampleCount for event in events)
        return ChirpRenderPlan(self, events, sampleCount)

    def RenderLayers(
            self, items, forceSeconds = False, requireToneWave = False,
            duration = None, targetFrames = None
            ):
        controls = []
        layers = []

        for item in items:
            if isinstance(item, InsertControl):
                layers.append(self.GetSoundSamples(item.sound))
                continue

            if isinstance(item, Tone):
                tone = copy.copy(item)
                if forceSeconds and tone.bend == tone.freq:
                    tone.bend = None

                recipe = controls + [tone]
                if forceSeconds:
                    recipe = controls + [SecondsControl(), tone]

                plan = self.CompileSequence(recipe)
                if duration is not None and targetFrames is not None and plan.events:
                    gateFrames = max(0, int(self.SAMPLE_RATE * duration))
                    planFrames = plan.sampleCount // self.channels
                    if planFrames >= gateFrames and planFrames < targetFrames:
                        events = [copy.copy(event) for event in plan.events]
                        extraFrames = targetFrames - planFrames
                        lastEventFrames = (events[-1].sampleCount // self.channels) + extraFrames
                        events[-1].duration = math.nextafter(
                            lastEventFrames / self.SAMPLE_RATE, math.inf
                        )
                        events[-1].sampleCount = lastEventFrames * self.channels
                        if isinstance(events[-1], ToneRenderEvent):
                            events[-1].fadeOut = False
                        plan = ChirpRenderPlan(
                            self, events, targetFrames * self.channels
                        )

                layers.append(self.RenderPlan(plan))
                continue

            if isinstance(item, WaveControl) and requireToneWave:
                raise ValueError(
                    "Patch recipes do not support Wave controls; use Tone.Wave "
                    "to override a Tone's default Sine wave"
                )

            if isinstance(item, Control):
                controls.append(item)
                continue

            raise TypeError(
                "Layered recipes may only contain Tone, Insert, or control objects"
            )

        return layers

    def GetToneRenderSettings(
            self, event, freq, amplitude, amplitudeBend,
            bend, bendIn, bendOut,
            performanceBend, performanceBendIn, performanceBendOut,
            performancePortamentoStart, performanceTrill,
            vibratoPhase, oscillatorPhase, modPhase, tremoloPhase
            ):
        return ToneRenderSettings(
            freq = freq,
            duration = event.duration,
            wave = event.wave,
            pitch = event.pitch,
            amplitude = amplitude,
            vibrato = event.vibrato,
            vibratoRate = event.vibratoRate,
            vibratoPhase = vibratoPhase,
            vibratoWave = event.vibratoWave,
            tremolo = event.tremolo,
            tremoloRate = event.tremoloRate,
            tremoloWave = event.tremoloWave,
            modFreq = event.modFreq,
            modDepth = event.modDepth,
            modWave = event.modWave,
            modPhase = modPhase,
            bend = bend,
            bendEasing = event.bendEasing,
            bendIn = bendIn,
            bendInDuration = event.bendInDuration,
            bendInEasing = event.bendInEasing,
            bendOut = bendOut,
            bendOutDuration = event.bendOutDuration,
            bendOutEasing = event.bendOutEasing,
            amplitudeBend = amplitudeBend,
            amplitudeEasing = event.amplitudeEasing,
            fadeInDuration = event.fadeInDuration,
            fadeInEasing = event.fadeInEasing,
            fadeOutDuration = event.fadeOutDuration,
            fadeOutEasing = event.fadeOutEasing,
            scopedDuration = event.scopedDuration,
            oscillatorPhase = oscillatorPhase,
            fadeIn = event.fadeIn,
            fadeOut = event.fadeOut,
            phaseDegrees = event.phaseDegrees,
            tremoloPhase = tremoloPhase,
            performanceBend = performanceBend,
            performanceBendEasing = event.performanceBendEasing,
            performanceBendStepped = event.performanceBendStepped,
            performanceBendRatios = event.performanceBendRatios,
            performanceBendDuration = event.performanceBendDuration,
            performanceBendOffset = event.performanceBendOffset,
            performanceBendIn = performanceBendIn,
            performanceBendInDuration = event.performanceBendInDuration,
            performanceBendInEasing = event.performanceBendInEasing,
            performanceBendOut = performanceBendOut,
            performanceBendOutDuration = event.performanceBendOutDuration,
            performanceBendOutEasing = event.performanceBendOutEasing,
            performancePortamentoStart = performancePortamentoStart,
            performancePortamentoDuration = event.performancePortamentoDuration,
            performancePortamentoOffset = event.performancePortamentoOffset,
            performanceTrill = performanceTrill,
            performanceTrillLength = event.performanceTrillLength,
            performanceTrillDuration = event.performanceTrillDuration,
            performanceOffset = event.performanceOffset,
            performanceVibrato = event.performanceVibrato,
            performanceVibratoRate = event.performanceVibratoRate,
            performanceVibratoWave = event.performanceVibratoWave,
            bendDuration = event.bendDuration,
            amplitudeBendDuration = event.amplitudeBendDuration,
            bendOffset = event.bendOffset,
            amplitudeBendOffset = event.amplitudeBendOffset,
            fadeFrames = event.fadeFrames
        )

    def GetRenderState(
            self, vibratoPhase, tremoloPhase, modPhase,
            autoPanPhaseDegrees, oscillatorPhases
            ):
        return ChirpRenderState(
            vibratoPhase = vibratoPhase,
            tremoloPhase = tremoloPhase,
            modPhase = modPhase,
            autoPanPhaseDegrees = autoPanPhaseDegrees,
            oscillatorPhases = list(oscillatorPhases)
        )

    def RenderPlan(self, plan, initialState = None, eventEndStates = None):
        if not isinstance(plan, ChirpRenderPlan):
            raise TypeError("Expected ChirpRenderPlan")
        if plan.synthesizer is not self:
            raise ValueError("Render plan belongs to a different ChirpSynth")

        samples = np.empty(plan.sampleCount, dtype = np.float64)
        sampleIndex = 0
        if initialState is None:
            self.oscillator.ResetState()
            vibratoPhase = 0.0
            tremoloPhase = 0.0
            tremoloNeedsReset = True
            previousTremoloSettings = None
            preserveInitialTremolo = False
            modPhase = 0.0
            autoPanPhaseDegrees = 0.0
            oscillatorPhases = [0.0]
        else:
            if not isinstance(initialState, ChirpRenderState):
                raise TypeError("Expected ChirpRenderState")
            vibratoPhase = initialState.vibratoPhase
            tremoloPhase = initialState.tremoloPhase
            tremoloNeedsReset = False
            previousTremoloSettings = None
            preserveInitialTremolo = True
            modPhase = initialState.modPhase
            autoPanPhaseDegrees = initialState.autoPanPhaseDegrees
            oscillatorPhases = list(initialState.oscillatorPhases)

        for event in plan.events:
            eventEnd = sampleIndex + event.sampleCount

            if isinstance(event, SilenceRenderEvent):
                samples[sampleIndex:eventEnd] = 0.0
                vibratoPhase = 0.0
                tremoloPhase = 0.0
                tremoloNeedsReset = True
                previousTremoloSettings = None
                preserveInitialTremolo = False
                modPhase = 0.0
                autoPanPhaseDegrees = 0.0
                oscillatorPhases = [0.0]
                sampleIndex = eventEnd
                if eventEndStates is not None:
                    eventEndStates.append(self.GetRenderState(
                        vibratoPhase, tremoloPhase, modPhase,
                        autoPanPhaseDegrees, oscillatorPhases
                    ))
                continue

            if isinstance(event, InsertRenderEvent):
                samples[sampleIndex:eventEnd] = event.samples
                vibratoPhase = 0.0
                tremoloPhase = 0.0
                tremoloNeedsReset = True
                previousTremoloSettings = None
                preserveInitialTremolo = False
                modPhase = 0.0
                autoPanPhaseDegrees = 0.0
                oscillatorPhases = [0.0]
                sampleIndex = eventEnd
                if eventEndStates is not None:
                    eventEndStates.append(self.GetRenderState(
                        vibratoPhase, tremoloPhase, modPhase,
                        autoPanPhaseDegrees, oscillatorPhases
                    ))
                continue

            if not isinstance(event, ToneRenderEvent):
                raise TypeError("Unknown render event: " + type(event).__name__)

            if not event.continueAutoPan:
                autoPanPhaseDegrees = event.autoPanOffset
            tremoloWave = getattr(event.tremoloWave, "__func__", event.tremoloWave)
            tremoloSettings = (event.tremolo, event.tremoloRate, tremoloWave)
            if event.tremolo <= 0.0:
                tremoloNeedsReset = True
                previousTremoloSettings = None
                preserveInitialTremolo = False
            elif preserveInitialTremolo:
                tremoloNeedsReset = False
                previousTremoloSettings = tremoloSettings
                preserveInitialTremolo = False
            elif tremoloNeedsReset or tremoloSettings != previousTremoloSettings:
                tremoloPhase = self.oscillator.GetMinimumPhase(
                    event.tremoloWave, event.tremoloRate
                )
                tremoloNeedsReset = False
                previousTremoloSettings = tremoloSettings

            if event.isNoise:
                settings = self.GetToneRenderSettings(
                    event,
                    freq = event.freq,
                    amplitude = event.amplitude,
                    amplitudeBend = event.amplitudeBend,
                    bend = event.bend,
                    bendIn = event.bendIn,
                    bendOut = event.bendOut,
                    performanceBend = event.performanceBend,
                    performanceBendIn = event.performanceBendIn,
                    performanceBendOut = event.performanceBendOut,
                    performancePortamentoStart = event.performancePortamentoStart,
                    performanceTrill = event.performanceTrill,
                    vibratoPhase = 0.0,
                    oscillatorPhase = 0.0,
                    modPhase = 0.0,
                    tremoloPhase = tremoloPhase
                )
                tone, _, _, _ = self._MakeTone(settings)
                outputSamples = self.MonoToOutputSamples(
                    tone, event.pan, event.autoPanEnabled,
                    event.autoPanDepth, event.autoPanRate,
                    event.autoPanWave, autoPanPhaseDegrees
                )
                vibratoPhase = 0.0
                tremoloPhase += (
                    (2.0 * math.pi * event.tremoloRate * len(tone))
                    / self.SAMPLE_RATE
                )
                modPhase = 0.0
                oscillatorPhases = [0.0]
            else:
                voiceCount = event.unisonVoices
                if len(oscillatorPhases) != voiceCount:
                    oscillatorPhases = [0.0] * voiceCount

                initialVibratoPhase = vibratoPhase
                initialModPhase = modPhase
                nextOscillatorPhases = []
                outputSamples = None

                for voiceIndex in range(voiceCount):
                    voicePosition = 0.0
                    if voiceCount > 1:
                        voicePosition = ((voiceIndex / (voiceCount - 1)) * 2.0) - 1.0

                    detuneRatio = 2.0 ** ((voicePosition * event.unisonDetune) / 1200.0)
                    voiceBend = event.bend
                    if isinstance(voiceBend, (int, float)):
                        voiceBend *= detuneRatio

                    voiceBendIn = event.bendIn
                    if voiceBendIn is not None:
                        voiceBendIn *= detuneRatio

                    voiceBendOut = event.bendOut
                    if voiceBendOut is not None:
                        voiceBendOut *= detuneRatio

                    voicePerformanceBend = event.performanceBend
                    if voicePerformanceBend is not None:
                        voicePerformanceBend *= detuneRatio

                    voicePerformanceBendIn = event.performanceBendIn
                    if voicePerformanceBendIn is not None:
                        voicePerformanceBendIn *= detuneRatio

                    voicePerformanceBendOut = event.performanceBendOut
                    if voicePerformanceBendOut is not None:
                        voicePerformanceBendOut *= detuneRatio

                    voicePerformancePortamentoStart = event.performancePortamentoStart
                    if voicePerformancePortamentoStart is not None:
                        voicePerformancePortamentoStart *= detuneRatio

                    voicePerformanceTrill = event.performanceTrill
                    if voicePerformanceTrill is not None:
                        voicePerformanceTrill *= detuneRatio

                    voiceAmplitude = event.amplitude / voiceCount
                    voiceAmplitudeBend = event.amplitudeBend
                    if voiceAmplitudeBend is not None:
                        voiceAmplitudeBend /= voiceCount

                    settings = self.GetToneRenderSettings(
                        event,
                        freq = event.freq * detuneRatio,
                        amplitude = voiceAmplitude,
                        amplitudeBend = voiceAmplitudeBend,
                        bend = voiceBend,
                        bendIn = voiceBendIn,
                        bendOut = voiceBendOut,
                        performanceBend = voicePerformanceBend,
                        performanceBendIn = voicePerformanceBendIn,
                        performanceBendOut = voicePerformanceBendOut,
                        performancePortamentoStart = voicePerformancePortamentoStart,
                        performanceTrill = voicePerformanceTrill,
                        vibratoPhase = initialVibratoPhase,
                        oscillatorPhase = oscillatorPhases[voiceIndex],
                        modPhase = initialModPhase,
                        tremoloPhase = tremoloPhase
                    )
                    tone, nextVibratoPhase, nextOscillatorPhase, nextModPhase = self._MakeTone(settings)

                    voicePan = event.pan + (
                        voicePosition * event.unisonSpread * (1.0 - abs(event.pan))
                    )
                    voiceSamples = self.MonoToOutputSamples(
                        tone, voicePan, event.autoPanEnabled,
                        event.autoPanDepth, event.autoPanRate,
                        event.autoPanWave, autoPanPhaseDegrees
                    )
                    outputSamples = voiceSamples if outputSamples is None else outputSamples + voiceSamples
                    nextOscillatorPhases.append(nextOscillatorPhase)

                vibratoPhase = nextVibratoPhase
                modPhase = nextModPhase
                oscillatorPhases = nextOscillatorPhases
                tremoloPhase += ((2.0 * math.pi * event.tremoloRate * len(tone)) / self.SAMPLE_RATE)

            autoPanPhaseDegrees = (
                autoPanPhaseDegrees
                + (360.0 * event.autoPanRate * (len(tone) / self.SAMPLE_RATE))
            ) % 360.0
            samples[sampleIndex:eventEnd] = outputSamples
            sampleIndex = eventEnd
            if eventEndStates is not None:
                eventEndStates.append(self.GetRenderState(
                    vibratoPhase, tremoloPhase, modPhase,
                    autoPanPhaseDegrees, oscillatorPhases
                ))

        return samples

    def RenderSamples(self, recipeOrPlan):
        if isinstance(recipeOrPlan, ChirpRenderPlan):
            return self.RenderPlan(recipeOrPlan)

        return self.RenderPlan(self.CompileSequence(recipeOrPlan))
