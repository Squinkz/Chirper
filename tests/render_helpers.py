from Chirper.core.ChirpConstants import Tremolo, Vibrato
from Chirper.core.ChirpRender import ToneRenderSettings


def MakeTone(
        synthesizer, freq, duration, wave = None, pitch = None,
        amplitude = 1.0, vibrato = Vibrato.NONE, vibratoRate = None,
        vibratoPhase = 0.0, vibratoWave = None,
        tremolo = Tremolo.NONE, tremoloRate = None, tremoloWave = None,
        modFreq = None, modDepth = 0.0, modWave = None, modPhase = 0.0,
        bend = None, bendEasing = "linear",
        bendIn = None, bendInDuration = 0.0, bendInEasing = "linear",
        bendOut = None, bendOutDuration = 0.0, bendOutEasing = "linear",
        amplitudeBend = None, amplitudeEasing = "linear",
        fadeInDuration = 0.0, fadeInEasing = "linear",
        fadeOutDuration = 0.0, fadeOutEasing = "linear",
        scopedDuration = None, oscillatorPhase = 0.0, fadeIn = True,
        fadeOut = True, phaseDegrees = None, tremoloPhase = 0.0,
        performanceBend = None, performanceBendEasing = "linear",
        performanceBendStepped = False, performanceBendRatios = None,
        performanceBendDuration = None, performanceBendOffset = 0.0,
        performanceBendIn = None, performanceBendInDuration = 0.0,
        performanceBendInEasing = "linear", performanceBendOut = None,
        performanceBendOutDuration = 0.0,
        performanceBendOutEasing = "linear",
        performancePortamentoStart = None,
        performancePortamentoDuration = 0.0,
        performancePortamentoOffset = 0.0,
        performanceTrill = None, performanceTrillLength = 0.0,
        performanceTrillDuration = None, performanceOffset = 0.0,
        performanceVibrato = Vibrato.NONE, performanceVibratoRate = None,
        performanceVibratoWave = None, bendDuration = None,
        amplitudeBendDuration = None, bendOffset = 0.0,
        amplitudeBendOffset = 0.0, fadeFrames = None
        ):
    if wave is None:
        wave = synthesizer.waveShape
    if pitch is None:
        pitch = synthesizer.pitch
    if vibratoRate is None:
        vibratoRate = synthesizer.vibratoRate
    if vibratoWave is None:
        vibratoWave = synthesizer.vibratoWave
    if performanceVibratoRate is None:
        performanceVibratoRate = synthesizer.vibratoRate
    if performanceVibratoWave is None:
        performanceVibratoWave = synthesizer.vibratoWave
    if tremoloRate is None:
        tremoloRate = synthesizer.tremoloRate
    if tremoloWave is None:
        tremoloWave = synthesizer.tremoloWave
    if modWave is None:
        modWave = synthesizer.oscillator.Sine
    if bendDuration is None:
        bendDuration = duration
    if amplitudeBendDuration is None:
        amplitudeBendDuration = duration
    if scopedDuration is None:
        scopedDuration = duration
    if performanceBendDuration is None:
        performanceBendDuration = duration
    if performanceTrillDuration is None:
        performanceTrillDuration = duration
    if fadeFrames is None:
        sampleCount = max(0, int(synthesizer.SAMPLE_RATE * duration))
        fadeFrames = min(int(synthesizer.SAMPLE_RATE * 0.003), sampleCount // 2)

    settings = ToneRenderSettings(
        freq = freq,
        duration = duration,
        wave = wave,
        pitch = pitch,
        amplitude = amplitude,
        vibrato = vibrato,
        vibratoRate = vibratoRate,
        vibratoPhase = vibratoPhase,
        vibratoWave = vibratoWave,
        tremolo = tremolo,
        tremoloRate = tremoloRate,
        tremoloWave = tremoloWave,
        modFreq = modFreq,
        modDepth = modDepth,
        modWave = modWave,
        modPhase = modPhase,
        bend = bend,
        bendEasing = bendEasing,
        bendIn = bendIn,
        bendInDuration = bendInDuration,
        bendInEasing = bendInEasing,
        bendOut = bendOut,
        bendOutDuration = bendOutDuration,
        bendOutEasing = bendOutEasing,
        amplitudeBend = amplitudeBend,
        amplitudeEasing = amplitudeEasing,
        fadeInDuration = fadeInDuration,
        fadeInEasing = fadeInEasing,
        fadeOutDuration = fadeOutDuration,
        fadeOutEasing = fadeOutEasing,
        scopedDuration = scopedDuration,
        oscillatorPhase = oscillatorPhase,
        fadeIn = fadeIn,
        fadeOut = fadeOut,
        phaseDegrees = phaseDegrees,
        tremoloPhase = tremoloPhase,
        performanceBend = performanceBend,
        performanceBendEasing = performanceBendEasing,
        performanceBendStepped = performanceBendStepped,
        performanceBendRatios = performanceBendRatios,
        performanceBendDuration = performanceBendDuration,
        performanceBendOffset = performanceBendOffset,
        performanceBendIn = performanceBendIn,
        performanceBendInDuration = performanceBendInDuration,
        performanceBendInEasing = performanceBendInEasing,
        performanceBendOut = performanceBendOut,
        performanceBendOutDuration = performanceBendOutDuration,
        performanceBendOutEasing = performanceBendOutEasing,
        performancePortamentoStart = performancePortamentoStart,
        performancePortamentoDuration = performancePortamentoDuration,
        performancePortamentoOffset = performancePortamentoOffset,
        performanceTrill = performanceTrill,
        performanceTrillLength = performanceTrillLength,
        performanceTrillDuration = performanceTrillDuration,
        performanceOffset = performanceOffset,
        performanceVibrato = performanceVibrato,
        performanceVibratoRate = performanceVibratoRate,
        performanceVibratoWave = performanceVibratoWave,
        bendDuration = bendDuration,
        amplitudeBendDuration = amplitudeBendDuration,
        bendOffset = bendOffset,
        amplitudeBendOffset = amplitudeBendOffset,
        fadeFrames = fadeFrames
    )
    return synthesizer._MakeTone(settings)


__all__ = ["MakeTone"]
