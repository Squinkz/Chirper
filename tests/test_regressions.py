from pathlib import Path
import json
import math
import struct
import tempfile
import unittest
from unittest import mock
import wave

import numpy as np


from Chirper.core import ChirpKernels
from Chirper.core.ChirpConstants import D, N, Dynamics
from Chirper.core.ChirpTone import (
    Insert, PerformanceFrequency, Pitch, Seconds, Tempo, Tone, TremoloDepth,
    TremoloRate, TremoloWave, VibratoDepth, VibratoRate, VibratoWave, Wave
)
from Chirper.core.ChirpDSP import ChirpDSP
from Chirper.core.ChirpOscillator import ChirpOscillator, WaveTable
from Chirper.core.ChirpSound import Sound
from Chirper.core.ChirpSynth import ChirpSynth
from Chirper.io import ChirpAudioData, ChirpFile
from Chirper.playback.ChirpPlayer import ChirpPlayer
from tests.render_helpers import MakeTone


class ChirpRegressionTests(unittest.TestCase):
    def test_ScopedFadesOnlyEvaluateTheRequestedCurveSlice(self):
        dsp = ChirpDSP(channels = 1)
        calls = []

        def CustomEasing(value):
            calls.append(value)
            return value

        fadeInGains = dsp.GetScopedFadeGains(
            128, 2_000_000, 1_000_000,
            1_000_000, CustomEasing
        )
        np.testing.assert_array_equal(fadeInGains, np.ones(128))
        self.assertEqual(calls, [])

        fadeOutGains = dsp.GetScopedFadeGains(
            128, 2_000_000, 0,
            0, "linear", 1_000_000, CustomEasing
        )
        np.testing.assert_array_equal(fadeOutGains, np.ones(128))
        self.assertEqual(calls, [])

        fullCurve = dsp.GetEasingValues(10, "inQuad")
        curveSlice = dsp.GetEasingValues(10, "inQuad", 3, 4)
        np.testing.assert_array_equal(curveSlice, fullCurve[3:7])

    def test_PerformanceFrequencyRejectsInvalidState(self):
        invalidValues = (
            ({"duration": math.nan}, ValueError),
            ({"duration": math.inf}, ValueError),
            ({"bend": math.nan}, ValueError),
            ({"bendEasing": "invalid"}, ValueError),
            ({"bendStepped": 1}, TypeError),
            ({"bendRatios": [1.0, math.inf]}, ValueError),
            ({"portamentoStart": math.nan}, ValueError),
            ({"portamentoDuration": math.inf}, ValueError),
            ({"trill": math.nan}, ValueError),
            ({"trillLength": math.inf}, ValueError),
            ({"vibratoEnabled": 1}, TypeError),
            ({"vibratoDepth": math.nan}, ValueError),
            ({"vibratoRate": math.inf}, ValueError),
        )

        for arguments, errorType in invalidValues:
            with self.subTest(arguments = arguments):
                with self.assertRaises(errorType):
                    PerformanceFrequency(440.0, **arguments)

        clamped = PerformanceFrequency(440.0, duration = -1.0)
        self.assertEqual(clamped.duration, 0.0)

    def test_ControlCommandsRejectInvalidNumbers(self):
        controls = (Pitch, Tempo, VibratoDepth, VibratoRate, TremoloDepth, TremoloRate)
        for control in controls:
            with self.subTest(control = control.__name__, value = "bad"):
                with self.assertRaises(TypeError):
                    control("bad")
            with self.subTest(control = control.__name__, value = True):
                with self.assertRaises(TypeError):
                    control(True)
            with self.subTest(control = control.__name__, value = math.nan):
                with self.assertRaises(ValueError):
                    control(math.nan)
            with self.subTest(control = control.__name__, value = math.inf):
                with self.assertRaises(ValueError):
                    control(math.inf)

        with self.assertRaises(ValueError):
            Tempo(0.0)

    def test_OscillatorRejectsInvalidRenderArguments(self):
        for sampleRate in (True, 44100.5, "44100"):
            with self.subTest(sampleRate = sampleRate):
                with self.assertRaises(TypeError):
                    ChirpOscillator(sampleRate)
        for sampleRate in (0, -1):
            with self.subTest(sampleRate = sampleRate):
                with self.assertRaises(ValueError):
                    ChirpOscillator(sampleRate)

        oscillator = ChirpOscillator()
        for frameCount in (True, 1.5, "10"):
            with self.subTest(frameCount = frameCount):
                with self.assertRaises(TypeError):
                    oscillator.RenderWave("Sine", 440.0, frameCount)
        with self.assertRaises(ValueError):
            oscillator.RenderWave("Sine", 440.0, -1)

        for frequency in (True, "440"):
            with self.subTest(frequency = frequency):
                with self.assertRaises(TypeError):
                    oscillator.RenderWave("Sine", frequency, 10)
        for frequency in (math.nan, math.inf):
            with self.subTest(frequency = frequency):
                with self.assertRaises(ValueError):
                    oscillator.RenderWave("Sine", frequency, 10)

        for phaseDegrees in (True, "90"):
            with self.subTest(phaseDegrees = phaseDegrees):
                with self.assertRaises(TypeError):
                    oscillator.RenderWave(
                        "Sine", 440.0, 10, phaseDegrees = phaseDegrees
                    )
        for phaseDegrees in (math.nan, math.inf):
            with self.subTest(phaseDegrees = phaseDegrees):
                with self.assertRaises(ValueError):
                    oscillator.RenderWave(
                        "Sine", 440.0, 10, phaseDegrees = phaseDegrees
                    )

    def test_SoundAppendConcatenatesWithoutCrossfade(self):
        first = Sound(samples = [1.0, 2.0], channels = 1)
        second = Sound(samples = [3.0, 4.0], channels = 1)

        appended = first.Append(second)

        np.testing.assert_array_equal(appended.samples, [1.0, 2.0, 3.0, 4.0])
        np.testing.assert_array_equal(first.samples, [1.0, 2.0])
        np.testing.assert_array_equal(second.samples, [3.0, 4.0])

    def test_SoundAppendSupportsEqualPowerAndLinearCrossfades(self):
        first = Sound(samples = np.ones(4), channels = 1)
        second = Sound(samples = np.ones(4), channels = 1)

        appended = first.Append(second, crossfade = 3.0 / 44100.0)
        linear = first.Append(
            second, crossfade = 3.0 / 44100.0, easing = "linear"
        )

        self.assertAlmostEqual(appended.samples[2], math.sqrt(2.0))
        np.testing.assert_allclose(linear.samples, np.ones(5), atol = 1e-12)
        self.assertEqual(len(appended.samples), 5)

    def test_SoundAppendClampsCrossfadeAndHandlesOneFrame(self):
        first = Sound(samples = [1.0, 1.0], channels = 1)
        second = Sound(samples = [1.0], channels = 1)

        clamped = first.Append(second, crossfade = 1.0)
        oneFrame = first.Append(second, crossfade = 1.0 / 44100.0)

        expected = [1.0, math.sqrt(2.0)]
        np.testing.assert_allclose(clamped.samples, expected, atol = 1e-12)
        np.testing.assert_allclose(oneFrame.samples, expected, atol = 1e-12)

    def test_SoundAppendPromotesMonoToStereo(self):
        mono = Sound(samples = [1.0], channels = 1)
        stereo = Sound(samples = [1.0, 0.0], channels = 2)

        appended = mono.Append(stereo)

        self.assertEqual(appended.channels, 2)
        np.testing.assert_allclose(
            appended.samples,
            [math.sqrt(0.5), math.sqrt(0.5), 1.0, 0.0],
            atol = 1e-12
        )

    def test_SoundAppendValidatesArgumentsAndSupportsEmptySounds(self):
        sound = Sound(samples = [1.0], channels = 1)

        np.testing.assert_array_equal(Sound(channels = 1).Append(sound).samples, [1.0])
        np.testing.assert_array_equal(sound.Append(Sound(channels = 1)).samples, [1.0])
        with self.assertRaises(TypeError):
            sound.Append([1.0])
        with self.assertRaises(TypeError):
            sound.Append(sound, crossfade = "invalid")
        with self.assertRaises(ValueError):
            sound.Append(sound, crossfade = math.inf)
        with self.assertRaises(ValueError):
            sound.Append(sound, crossfade = 1.0, easing = "invalid")
        with self.assertRaises(ValueError):
            sound.Append(sound, crossfade = 1.0, easing = "cosine")
        with self.assertRaises(TypeError):
            sound.Append(sound, crossfade = 1.0, easing = lambda t: t)

    def test_FrequencyLimitsAreOrdinaryNumericValues(self):
        self.assertEqual(N.MIN, 20.0)
        self.assertEqual(N.MAX, 20000.0)
        self.assertEqual(N.MAX * 2.0, 40000.0)

        pitched = Sound([
            Tone(N.MAX, 0.001).Wave("Sine"),
        ], channels = 1)
        filteredNoise = Sound([
            Tone(N.MAX, 0.001).Wave("NoiseLP").Bend(N.MIN),
        ], channels = 1)

        self.assertTrue(np.all(np.isfinite(pitched.samples)))
        self.assertTrue(np.all(np.isfinite(filteredNoise.samples)))

    def test_PitchedAndNoiseFrequenciesAreNotUpperClamped(self):
        receivedFrequencies = []

        def CaptureFrequency(time, frequency):
            receivedFrequencies.append(frequency)
            return 0.0

        highSine = Sound([
            Tone(40000.0, 0.001).Wave("Sine"),
        ], channels = 1)
        maxSine = Sound([
            Tone(20000.0, 0.001).Wave("Sine"),
        ], channels = 1)
        Sound([
            Tone(40000.0, 4.0 / 44100.0).Wave(CaptureFrequency),
            Tone(40000.0, 4.0 / 44100.0).Wave("NoiseStep"),
        ], channels = 1)

        self.assertFalse(np.allclose(highSine.samples, maxSine.samples))
        self.assertEqual(receivedFrequencies, [40000.0] * 4)

    def test_SoundChannelsIsTheSecondConstructorArgument(self):
        sound = Sound([], 1)

        self.assertEqual(sound.channels, 1)

        with self.assertRaises(TypeError):
            Sound([], 1, None)

    def test_SoundRecipesAreLayeredByDefault(self):
        first = Sound(samples = [1.0, 1.0], channels = 1)
        second = Sound(samples = [2.0, 2.0, 2.0], channels = 1)

        sound = Sound([Insert(first), Insert(second)], channels = 1)

        np.testing.assert_array_equal(sound.samples, [3.0, 3.0, 2.0])

    def test_SoundRecipesCanBeSequential(self):
        first = Sound(samples = [1.0, 1.0], channels = 1)
        second = Sound(samples = [2.0, 2.0, 2.0], channels = 1)

        sound = Sound(
            [Insert(first), Insert(second)], channels = 1, layered = False
        )

        np.testing.assert_array_equal(
            sound.samples, [1.0, 1.0, 2.0, 2.0, 2.0]
        )

    def test_SoundDefaultsOnlyConfigureChannels(self):
        defaultChannels = Sound.CHANNELS
        try:
            Sound.SetDefaults(channels = 1)
            self.assertEqual(Sound().channels, 1)

            with self.assertRaises(TypeError):
                Sound.SetDefaults(sampleRate = 44100)
        finally:
            Sound.SetDefaults(channels = defaultChannels)

    def test_RawPcmUsesExplicitChannelsAndValidatesDuration(self):
        pcm = b"\x00\x00" * 44100
        sound = Sound(pcm = pcm, channels = 1)

        self.assertEqual(sound.channels, 1)
        self.assertEqual(sound.duration, 1.0)

        metadata = ChirpFile.MakePcmMetadata(1.0, 1)
        loaded = ChirpFile.PcmFileData(pcm, metadata)

        self.assertEqual(loaded.duration, 1.0)
        self.assertEqual(loaded.metadata["duration"], 1.0)

        with self.assertRaisesRegex(ValueError, "declared duration"):
            ChirpFile.PcmFileData(pcm, ChirpFile.MakePcmMetadata(99.0, 1))

    def test_PlayerReturnsValidatedPcmPlaybackData(self):
        pcm = b"\x00\x00" * 44100
        metadata = ChirpFile.MakePcmMetadata(1.0, 1)
        sound = ChirpFile.PcmFileData(pcm, metadata)
        player = ChirpPlayer.__new__(ChirpPlayer)
        player.channels = 1
        player.sampleRate = 44100
        player.bitsPerSample = 16

        playbackData = player.GetPlaybackData(sound)

        self.assertEqual(playbackData[1:], (1, 44100, 16))

    def test_StereoPanRotatesStereoImage(self):
        dsp = ChirpDSP(channels = 2)
        pcm = dsp.SamplesToBytes([1.0, 0.0, 0.0, 1.0])

        panned = dsp.BytesToSamples(dsp.ApplySoundPan(pcm, 0.5))

        self.assertAlmostEqual(panned[0], 0.7071, places = 4)
        self.assertAlmostEqual(panned[1], 0.7071, places = 4)
        self.assertEqual(panned[2], 0.0)
        self.assertAlmostEqual(panned[3], 1.0, places = 4)

    def test_StereoPanPreservesCenterAndCollapsesAtEdges(self):
        sound = Sound(samples = [0.25, 0.5, -0.5, 0.25], channels = 2)

        centered = sound.Pan(0.0)
        right = sound.Pan(1.0)
        left = sound.Pan(-1.0)

        np.testing.assert_array_equal(centered.samples, sound.samples)
        np.testing.assert_allclose(right.samples, [0.0, 0.75, 0.0, -0.25], atol = 0.000000000001)
        np.testing.assert_allclose(left.samples, [0.75, 0.0, -0.25, 0.0], atol = 0.000000000001)
        np.testing.assert_array_equal(sound.samples, [0.25, 0.5, -0.5, 0.25])

    def test_StereoPanClampsAmount(self):
        sound = Sound(samples = [0.25, 0.5], channels = 2)

        np.testing.assert_array_equal(sound.Pan(2.0).samples, sound.Pan(1.0).samples)
        np.testing.assert_array_equal(sound.Pan(-2.0).samples, sound.Pan(-1.0).samples)

    def test_DefaultDelayTimesAreQuarterSecond(self):
        source = Sound(samples = [1.0], channels = 1)

        delayed = source.Delay(decay = 0.5, count = 1)
        pingPong = source.PingPong(decay = 0.5, count = 1)

        np.testing.assert_array_equal(np.flatnonzero(delayed.samples), [0, 11025])
        pingPongFrames = pingPong.samples.reshape(-1, 2)
        echoFrames = np.flatnonzero(np.any(pingPongFrames != 0.0, axis = 1))
        np.testing.assert_array_equal(echoFrames, [0, 11025])

    def test_DSPNoOpsReturnIndependentArrays(self):
        dsp = ChirpDSP(channels = 2)
        source = np.array([0.25, -0.5, 0.75, -1.0], dtype = np.float64)
        noOps = {
            "gain": dsp.ApplySoundGain(source),
            "fadeIn": dsp.ApplySoundFadeIn(source, 0.0),
            "ring": dsp.ApplySoundRing(source, 440.0, mix = 0.0),
            "pan": dsp.ApplySoundPan(source, 0.0),
            "delay": dsp.ApplySoundDelay(source),
        }

        for effectName, processed in noOps.items():
            with self.subTest(effect = effectName):
                self.assertIsNot(processed, source)
                self.assertFalse(np.shares_memory(processed, source))
                np.testing.assert_array_equal(processed, source)

        mutablePcm = bytearray(struct.pack("<hh", -32768, 32767))
        copiedPcm = dsp.ApplySoundGain(mutablePcm)
        mutablePcm[:] = b"\x00\x00\x00\x00"
        self.assertEqual(copiedPcm, struct.pack("<hh", -32768, 32767))

    def test_DSPRejectsIncompleteFramesAndNonFiniteParameters(self):
        dsp = ChirpDSP(channels = 2)

        for operation in (
                lambda: dsp.ApplySoundGain([1.0]),
                lambda: dsp.ApplySoundLowPass([1.0], 1000.0),
                lambda: dsp.ApplySoundLowPassSweep([1.0], 100.0, 1000.0),
                lambda: dsp.NormalizeSamples([1.0]),
                lambda: dsp.SamplesToBytes([1.0]),
                ):
            with self.assertRaises(ValueError):
                operation()

        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value = value):
                with self.assertRaises(ValueError):
                    dsp.ApplySoundClip([0.0, 0.0], value)
                with self.assertRaises(ValueError):
                    dsp.GetPanGains(value)
                with self.assertRaises(ValueError):
                    dsp.ApplySoundChorus([0.0, 0.0], rate = value)
                with self.assertRaises(ValueError):
                    dsp.ApplySoundCut([0.0, 0.0], value)

    def test_DryReverbsDoNotExtendSound(self):
        source = Sound(samples = [0.25, -0.5, 0.75], channels = 1)

        for effectName, processed in (
                ("Schroverb", source.Schroverb(wet = 0.0)),
                ("Freeverb", source.Freeverb(wet = 0.0)),
                ("MTVerb", source.MTVerb(wet = 0.0))
                ):
            with self.subTest(effect = effectName):
                np.testing.assert_array_equal(processed.samples, source.samples)
                self.assertEqual(processed.duration, source.duration)

    def test_SoftClipMixIsContinuousAndPreservesDryHeadroom(self):
        source = Sound(samples = [2.0, -2.0], channels = 1)

        dry = source.SoftClip(mix = 0.0)
        nearlyDry = source.SoftClip(mix = 0.000001)
        fullyWet = source.SoftClip(mix = 1.0)

        np.testing.assert_array_equal(dry.samples, [2.0, -2.0])
        np.testing.assert_allclose(nearlyDry.samples, [1.999999, -1.999999])
        np.testing.assert_array_equal(fullyWet.samples, [1.0, -1.0])

    def test_NonFiniteSamplesAreRejectedAtSoundAndDSPBoundaries(self):
        dsp = ChirpDSP(channels = 1)

        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value = value):
                with self.assertRaises(ValueError):
                    Sound(samples = [value], channels = 1)
                with self.assertRaises(ValueError):
                    dsp.ApplySoundGain([value], 0.5)
                with self.assertRaises(ValueError):
                    dsp.SamplesToBytes([value])
                with self.assertRaises(ValueError):
                    dsp.MixSamples([[value]])
                with self.assertRaises(ValueError):
                    dsp.NormalizeSamples([value])

    def test_PcmMetadataIsValidatedBeforeDurationCalculation(self):
        metadata = ChirpFile.MakePcmMetadata(0.0, 1)
        metadata["sampleRate"] = 0

        with self.assertRaisesRegex(ValueError, "Unsupported sample rate"):
            ChirpFile.PcmFileData(b"\x00\x00", metadata)

    def test_PcmInputsAndFormatCountsUseStrictTypes(self):
        metadata = ChirpFile.MakePcmMetadata(0.0, 1)
        with tempfile.TemporaryDirectory() as directory:
            wavPath = Path(directory) / "invalid.wav"
            for action in (
                    lambda: Sound(pcm = 4, channels = 1),
                    lambda: ChirpFile.PcmFileData(4, metadata),
                    lambda: ChirpFile.WriteWav(wavPath, 4, metadata),
                    ):
                with self.subTest(action = action):
                    with self.assertRaises(TypeError):
                        action()

        for metadataKey, value in (
                ("channels", 1.0),
                ("sampleRate", 44100.0),
                ("bitsPerSample", 16.0),
                ):
            invalidMetadata = ChirpFile.MakePcmMetadata(0.0, 1)
            invalidMetadata[metadataKey] = value
            with self.subTest(metadataKey = metadataKey):
                with self.assertRaises(ValueError):
                    ChirpFile.PcmFileData(b"", invalidMetadata)

        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "declared duration"):
                ChirpFile.WriteWav(
                    Path(directory) / "mismatch.wav", b"",
                    ChirpFile.MakePcmMetadata(1.0 / 44100.0, 1)
                )

    def test_ExternalPcmMinimumDecodesWithinFloatRange(self):
        pcm = struct.pack("<hhh", -32768, -32767, 32767)
        duration = 3.0 / 44100.0
        fileData = ChirpFile.PcmFileData(pcm, ChirpFile.MakePcmMetadata(duration, 1))
        player = ChirpPlayer.__new__(ChirpPlayer)
        player.channels = 1
        player.sampleRate = 44100
        player.bitsPerSample = 16

        expected = [-1.0, -1.0, 1.0]
        np.testing.assert_array_equal(ChirpDSP(channels = 1).BytesToSamples(pcm), expected)
        np.testing.assert_array_equal(ChirpSynth(channels = 1).GetSoundSamples(fileData), expected)
        np.testing.assert_array_equal(player.GetPlaybackSamples(fileData), expected)

    def test_24BitWavPreservesSourcePrecision(self):
        sourceValues = [-8388608, -257, -1, 0, 1, 257, 8388607]
        pcm = b"".join(
            value.to_bytes(3, byteorder = "little", signed = True)
            for value in sourceValues
        )
        expected = np.maximum(np.asarray(sourceValues, dtype = np.float64) / 8388607.0, -1.0)

        with tempfile.TemporaryDirectory() as directory:
            wavPath = Path(directory) / "source.wav"
            with wave.open(str(wavPath), "wb") as wavFile:
                wavFile.setnchannels(1)
                wavFile.setsampwidth(3)
                wavFile.setframerate(44100)
                wavFile.writeframes(pcm)

            fileData = ChirpFile.ReadWav(wavPath)
            loaded = Sound.LoadWav(wavPath)
            copiedPath = ChirpFile.WriteWav(Path(directory) / "copy", fileData.pcm, fileData.metadata)
            ChirpFile.WavToChirp(wavPath)
            converted = Sound.Load(wavPath.with_suffix(".chirp"))

            with wave.open(str(copiedPath), "rb") as wavFile:
                copiedWidth = wavFile.getsampwidth()
                copiedPcm = wavFile.readframes(wavFile.getnframes())

        self.assertEqual(fileData.bitsPerSample, 24)
        self.assertEqual(fileData.sampleFormat, "pcm_s24le")
        self.assertEqual(fileData.pcm, pcm)
        self.assertEqual(copiedWidth, 3)
        self.assertEqual(copiedPcm, pcm)
        self.assertNotEqual(fileData.samples[4], 0.0)
        np.testing.assert_array_equal(fileData.samples, expected)
        np.testing.assert_array_equal(loaded.samples, expected)
        np.testing.assert_array_equal(converted.samples, expected.astype(np.float32).astype(np.float64))

    def test_DocumentedSynthAndFilterKeywordsAreAccepted(self):
        synthesizer = ChirpSynth(channels = 1)
        recipe = [Tone(440.0, 0.001)]
        plan = synthesizer.CompileSequence(recipe = recipe)
        samples = synthesizer.RenderSamples(recipeOrPlan = plan)
        dsp = ChirpDSP(channels = 1)

        lowPassed = dsp.ApplySoundLowPass(soundData = samples, freq = 1000.0)
        swept = dsp.ApplySoundHighShelfSweep(
            soundData = samples,
            startFreq = 500.0,
            endFreq = 2000.0,
            db = 3.0
        )

        self.assertEqual(len(lowPassed), len(samples))
        self.assertEqual(len(swept), len(samples))

    def test_ChirpReadRejectsTruncatedAndOversizedMetadata(self):
        malformedFiles = (
            ChirpFile.MAGIC,
            ChirpFile.MAGIC + b"\x01\x00",
            ChirpFile.MAGIC + struct.pack("<I", ChirpFile.MAX_METADATA_BYTES + 1),
            ChirpFile.MAGIC + struct.pack("<I", 10) + b"{}",
            ChirpFile.MAGIC + struct.pack("<I", 1) + b"{",
            ChirpFile.MAGIC + struct.pack("<I", 17) + b'{"duration": NaN}',
        )

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "malformed.chirp"
            for fileData in malformedFiles:
                with self.subTest(fileData = fileData):
                    path.write_bytes(fileData)
                    with self.assertRaises(ValueError):
                        ChirpFile.Read(path)

    def test_ChirpReadRejectsWholeFramePayloadLengthChanges(self):
        sound = Sound(samples = [0.0, 0.25, 0.5, 0.75], channels = 1)
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            validPath = sound.Save(directory / "valid")
            fileBytes = validPath.read_bytes()
            metadataLength = struct.unpack("<I", fileBytes[6:10])[0]
            payloadStart = 10 + metadataLength
            changedFiles = (
                fileBytes[:payloadStart] + fileBytes[payloadStart:-4],
                fileBytes + np.array([1.0], dtype = "<f4").tobytes(),
            )

            for index, changedFile in enumerate(changedFiles):
                path = directory / ("changed" + str(index) + ".chirp")
                path.write_bytes(changedFile)
                with self.subTest(path = path):
                    with self.assertRaisesRegex(ValueError, "declared duration"):
                        ChirpFile.Read(path)

    def test_ReadWavRejectsFrameAlignedTruncation(self):
        formatChunk = struct.pack("<HHIIHH", 1, 1, 44100, 88200, 2, 16)
        declaredDataSize = 6
        riffSize = 4 + (8 + len(formatChunk)) + (8 + declaredDataSize)
        wavBytes = (
            b"RIFF" + struct.pack("<I", riffSize) + b"WAVE"
            + b"fmt " + struct.pack("<I", len(formatChunk)) + formatChunk
            + b"data" + struct.pack("<I", declaredDataSize) + b"\x00\x00"
        )

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "truncated.wav"
            path.write_bytes(wavBytes)
            with self.assertRaisesRegex(ValueError, "truncated"):
                ChirpFile.ReadWav(path)

    def test_ChirpRoundTripStoresUnclippedFloat32Samples(self):
        sourceSamples = np.array([1.5, -2.25, 1.0 / 3.0], dtype = np.float64)
        expectedSamples = sourceSamples.astype(np.float32).astype(np.float64)
        sound = Sound(samples = sourceSamples, channels = 1)

        with tempfile.TemporaryDirectory() as directory:
            path = sound.Save(Path(directory) / "float-samples")
            fileBytes = path.read_bytes()
            metadataLength = struct.unpack("<I", fileBytes[6:10])[0]
            metadataEnd = 10 + metadataLength
            metadata = json.loads(fileBytes[10:metadataEnd].decode("utf-8"))
            payload = fileBytes[metadataEnd:]
            fileData = ChirpFile.Load(path)
            loaded = Sound.Load(path)

        self.assertEqual(fileBytes[:6], ChirpFile.MAGIC)
        self.assertEqual(metadata["sampleFormat"], "float32-le")
        self.assertNotIn("bitsPerSample", metadata)
        self.assertEqual(len(payload), len(sourceSamples) * 4)
        np.testing.assert_array_equal(np.frombuffer(payload, dtype = "<f4"), sourceSamples.astype(np.float32))
        np.testing.assert_array_equal(fileData.samples, expectedSamples)
        np.testing.assert_array_equal(loaded.samples, expectedSamples)
        self.assertGreater(loaded.samples[0], 1.0)
        self.assertLess(loaded.samples[1], -1.0)

        samples = fileData.samples
        samples[0] = 0.0
        self.assertEqual(fileData.samples[0], 1.5)

    def test_ChirpWriteRejectsSamplesOutsideFloat32Range(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid"
            sample = float(np.finfo(np.float32).max) * 2.0
            sound = Sound(samples = [sample], channels = 1)

            with self.assertRaises(ValueError):
                sound.Save(path)

    def test_ChirpWriteRejectsNonFiniteJsonMetadata(self):
        sound = Sound(
            samples = [0.0], channels = 1,
            metadata = {"invalid": math.nan}
        )

        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "finite JSON"):
                sound.Save(Path(directory) / "invalid")

    def test_FileWritesPreserveExistingDestinationsWhenReplacementFails(self):
        sound = Sound(samples = [0.25], channels = 1)
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            chirpPath = sound.Save(directory / "existing")
            wavPath = sound.SaveWav(directory / "existing")
            originalChirp = chirpPath.read_bytes()
            originalWav = wavPath.read_bytes()

            with mock.patch.object(ChirpFile.os, "replace", side_effect = OSError("replace failed")):
                with self.assertRaises(OSError):
                    sound.Gain(0.5).Save(chirpPath)
                with self.assertRaises(OSError):
                    sound.Gain(0.5).SaveWav(wavPath)

            self.assertEqual(chirpPath.read_bytes(), originalChirp)
            self.assertEqual(wavPath.read_bytes(), originalWav)
            self.assertEqual(list(directory.glob("*.tmp")), [])

    def test_ChirpReadRejectsInvalidFloatPayloads(self):
        metadata = ChirpFile.MakeMetadata(0.0, 1)
        metadataBytes = json.dumps(metadata).encode("utf-8")
        header = ChirpFile.MAGIC + struct.pack("<I", len(metadataBytes)) + metadataBytes
        invalidPayloads = (
            b"\x00",
            np.array([np.nan], dtype = "<f4").tobytes(),
            np.array([np.inf], dtype = "<f4").tobytes(),
        )

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.chirp"
            for payload in invalidPayloads:
                with self.subTest(payload = payload):
                    path.write_bytes(header + payload)
                    with self.assertRaises(ValueError):
                        ChirpFile.Read(path)

    def test_ChirpWavConversionClipsOnlyAtPcmBoundary(self):
        source = Sound(samples = [1.5, -1.5, 0.25], channels = 1)

        with tempfile.TemporaryDirectory() as directory:
            chirpPath = source.Save(Path(directory) / "conversion")
            ChirpFile.ChirpToWav(chirpPath)
            wavPath = chirpPath.with_suffix(".wav")
            wavSound = Sound.LoadWav(wavPath)
            ChirpFile.WavToChirp(wavPath)
            converted = Sound.Load(chirpPath)

        expected = [1.0, -1.0, round(0.25 * 32767) / 32767.0]
        np.testing.assert_allclose(wavSound.samples, expected)
        np.testing.assert_allclose(converted.samples, expected)

    def test_SaveAndSaveWavReturnResolvedPaths(self):
        sound = Sound(samples = [0.0], channels = 1)

        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "beep"
            chirpPath = sound.Save(destination)
            wavPath = sound.SaveWav(destination)

            self.assertEqual(chirpPath, destination.with_suffix(".chirp"))
            self.assertEqual(wavPath, destination.with_suffix(".wav"))
            self.assertIsInstance(chirpPath, Path)
            self.assertIsInstance(wavPath, Path)
            self.assertTrue(chirpPath.is_file())
            self.assertTrue(wavPath.is_file())

    def test_SaveReplacesConflictingFileExtensions(self):
        sound = Sound(samples = [0.0], channels = 1)

        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            chirpPath = sound.Save(directory / "native.wav")
            unchangedChirp = sound.Save(directory / "unchanged.chirp")
            wavPath = sound.SaveWav(directory / "wave.chirp")
            unchangedWav = sound.SaveWav(directory / "unchanged.wav")

        self.assertEqual(chirpPath.name, "native.chirp")
        self.assertEqual(unchangedChirp.name, "unchanged.chirp")
        self.assertEqual(wavPath.name, "wave.wav")
        self.assertEqual(unchangedWav.name, "unchanged.wav")

    def test_SoundPreservesCustomMetadataAcrossLoadsAndCopies(self):
        sourceMetadata = {"author": {"name": "Chirper"}}
        sound = Sound(
            samples = [0.25, -0.5], channels = 1,
            metadata = sourceMetadata
        )
        sourceMetadata["author"]["name"] = "Changed"
        exposedMetadata = sound.metadata
        exposedMetadata["author"]["name"] = "Also changed"
        exposedMetadata["channels"] = 2
        processed = sound.Gain(0.5)

        with tempfile.TemporaryDirectory() as directory:
            path = sound.Save(Path(directory) / "metadata")
            loaded = Sound.Load(path)

        self.assertEqual(sound.metadata["author"]["name"], "Chirper")
        self.assertEqual(processed.metadata["author"]["name"], "Chirper")
        self.assertEqual(loaded.metadata["author"]["name"], "Chirper")
        self.assertEqual(loaded.metadata["channels"], 1)

    def test_SoundRawArgumentsHaveUnambiguousPrecedence(self):
        with self.assertRaisesRegex(ValueError, "not more than one"):
            Sound([Tone(440.0, 0.01)], samples = [0.0], channels = 1)
        with self.assertRaisesRegex(ValueError, "not both"):
            Sound(pcm = b"", samples = [], channels = 1)
        with self.assertRaisesRegex(ValueError, "disagrees"):
            Sound(
                pcm = b"\x00\x00", channels = 1,
                metadata = ChirpFile.MakePcmMetadata(1.0 / 44100.0, 2)
            )

        sound = Sound(
            samples = [0.0], channels = 1, layered = "unused",
            metadata = {"channels": 2}
        )
        self.assertEqual(sound.channels, 1)

    def test_InvalidChannelAndFormatTypesAreRejected(self):
        for constructor in (
                lambda: Sound(channels = True),
                lambda: ChirpDSP(channels = True),
                lambda: ChirpSynth(channels = True),
                lambda: ChirpPlayer(channels = True, enabled = False),
                ):
            with self.assertRaises(ValueError):
                constructor()

        metadata = ChirpFile.MakeMetadata(0.0, True)
        with self.assertRaises(ValueError):
            ChirpFile.ChirpFileData([], metadata)

        for constructor in (
                lambda: Sound(channels = 1.0),
                lambda: ChirpDSP(channels = 1.0),
                lambda: ChirpSynth(channels = 1.0),
                lambda: ChirpPlayer(channels = 1.0, enabled = False),
                ):
            with self.assertRaises(ValueError):
                constructor()

        with self.assertRaises(ValueError):
            ChirpAudioData.SamplesToPcm([], 1, bitsPerSample = 16.0)
        with self.assertRaises(ValueError):
            ChirpAudioData.GetSampleDuration([], 1, sampleRate = 44100.0)
        with self.assertRaises(ValueError):
            ChirpAudioData.GetPcmDuration(b"", 1, sampleRate = 44100.0)

    def test_PitchControlScalesToneFrequencyInputs(self):
        duration = 16.0 / 44100.0
        step = 4.0 / 44100.0
        cases = [
            (
                Tone(100.0, duration).Bend(200.0),
                Tone(200.0, duration).Bend(400.0)
            ),
            (
                Tone(100.0, duration).Arpeggio([1.0, 1.5], step),
                Tone(200.0, duration).Arpeggio([1.0, 1.5], step)
            ),
            (
                Tone(100.0, duration).Arpeggio([150.0, 175.0], step),
                Tone(200.0, duration).Arpeggio([300.0, 350.0], step)
            ),
            (
                Tone(PerformanceFrequency(
                    100.0, bend = 200.0, bendStepped = True,
                    duration = duration
                ), duration),
                Tone(PerformanceFrequency(
                    200.0, bend = 400.0, bendStepped = True,
                    duration = duration
                ), duration)
            ),
            (
                Tone(PerformanceFrequency(
                    100.0, trill = 150.0, trillLength = step,
                    duration = duration
                ), duration),
                Tone(PerformanceFrequency(
                    200.0, trill = 300.0, trillLength = step,
                    duration = duration
                ), duration)
            ),
            (
                Tone(PerformanceFrequency(
                    100.0, portamentoStart = 50.0,
                    portamentoDuration = duration
                ), duration),
                Tone(PerformanceFrequency(
                    200.0, portamentoStart = 100.0,
                    portamentoDuration = duration
                ), duration)
            ),
            (
                Tone(100.0, duration).Mod(50.0),
                Tone(200.0, duration).Mod(100.0)
            ),
        ]

        enabled = ChirpKernels.NUMBA_ENABLED
        try:
            for accelerated in (False, True):
                if accelerated and not ChirpKernels.NUMBA_AVAILABLE:
                    continue
                ChirpKernels.NUMBA_ENABLED = accelerated
                for pitchedTone, explicitTone in cases:
                    pitched = [Seconds(), Pitch(2.0), pitchedTone]
                    explicit = [Seconds(), explicitTone]
                    np.testing.assert_allclose(
                        ChirpSynth(channels = 1).RenderSamples(pitched),
                        ChirpSynth(channels = 1).RenderSamples(explicit),
                        rtol = 0.0,
                        atol = 1e-12
                    )
        finally:
            ChirpKernels.NUMBA_ENABLED = enabled

    def test_SaveAndSaveWavCreateParentDirectories(self):
        sound = Sound(samples = [0.0], channels = 1)

        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "new" / "nested" / "beep"
            chirpPath = sound.Save(destination)
            wavPath = sound.SaveWav(destination)

            self.assertTrue(chirpPath.is_file())
            self.assertTrue(wavPath.is_file())

    def test_MonoAveragesStereoChannels(self):
        sound = Sound(samples = [1.0, -1.0, 0.5, 0.5], channels = 2)

        mono = sound.Mono()

        self.assertEqual(mono.channels, 1)
        self.assertEqual(mono.duration, sound.duration)
        np.testing.assert_array_equal(mono.samples, [0.0, 0.5])
        np.testing.assert_array_equal(sound.samples, [1.0, -1.0, 0.5, 0.5])

    def test_MonoDownmixRemainsFiniteAtFloatLimits(self):
        maximum = np.finfo(np.float64).max
        sound = Sound(
            samples = [maximum, maximum, -maximum, -maximum], channels = 2
        )

        mono = sound.Mono()

        self.assertTrue(np.all(np.isfinite(mono.samples)))
        np.testing.assert_array_equal(mono.samples, [maximum, -maximum])

    def test_StereoCentersMonoWithEqualPower(self):
        sound = Sound(samples = [1.0, -0.5], channels = 1)

        stereo = sound.Stereo()

        centerGain = np.sqrt(0.5)
        self.assertEqual(stereo.channels, 2)
        np.testing.assert_allclose(stereo.samples, [centerGain, centerGain, -0.5 * centerGain, -0.5 * centerGain])

    def test_PanPromotesMonoToStereo(self):
        sound = Sound(samples = [1.0, -0.5], channels = 1)

        right = sound.Pan(1.0)

        self.assertEqual(right.channels, 2)
        np.testing.assert_allclose(right.samples, [0.0, 1.0, 0.0, -0.5], atol = 0.000000000001)

    def test_PingPongPromotesMonoWithoutAttenuatingEchoSource(self):
        sound = Sound(samples = [1.0, 0.0], channels = 1)

        pingPong = sound.PingPong(delay = 1.0 / 44100.0, decay = 0.5, count = 1)
        frames = pingPong.samples.reshape(-1, 2)

        self.assertEqual(pingPong.channels, 2)
        np.testing.assert_allclose(frames[0], [np.sqrt(0.5), np.sqrt(0.5)])
        np.testing.assert_allclose(frames[1], [0.5, 0.0], atol = 0.000000000001)

    def test_InsertConvertsSoundToRecipeChannels(self):
        mono = Sound(samples = [1.0, -0.5], channels = 1)
        stereo = Sound(samples = [0.25, 0.75, -0.25, 0.5], channels = 2)

        insertedStereo = Sound([Insert(mono)], channels = 2)
        insertedMono = Sound([Insert(stereo)], channels = 1)

        centerGain = np.sqrt(0.5)
        np.testing.assert_allclose(
            insertedStereo.samples,
            [centerGain, centerGain, -0.5 * centerGain, -0.5 * centerGain]
        )
        np.testing.assert_allclose(insertedMono.samples, [0.5, 0.125])

    def test_PlayerConvertsSoundToPlaybackChannels(self):
        mono = Sound(samples = [1.0, -0.5], channels = 1)
        stereo = Sound(samples = [0.25, 0.75, -0.25, 0.5], channels = 2)
        stereoPlayer = ChirpPlayer(channels = 2, enabled = False)
        monoPlayer = ChirpPlayer(channels = 1, enabled = False)

        centerGain = np.sqrt(0.5)
        np.testing.assert_allclose(
            stereoPlayer.GetPlaybackSamples(mono),
            [centerGain, centerGain, -0.5 * centerGain, -0.5 * centerGain]
        )
        np.testing.assert_allclose(monoPlayer.GetPlaybackSamples(stereo), [0.5, 0.125])

    def test_DelayAndPingPongShareDefaults(self):
        self.assertEqual(Sound.Delay.__defaults__, (0.25, 0.5, None, True))
        self.assertEqual(Sound.PingPong.__defaults__, (0.25, 0.5, None, 1.0, True))

    def test_MixConvertsInputsToRequestedChannels(self):
        mono = Sound(samples = [1.0, -0.5], channels = 1)
        stereo = Sound(samples = [0.25, 0.75, -0.25, 0.5], channels = 2)

        stereoMix = Sound.Mix([mono, stereo], channels = 2, mixGain = 1.0)
        monoMix = Sound.Mix([mono, stereo], channels = 1, mixGain = 1.0)

        centerGain = np.sqrt(0.5)
        np.testing.assert_allclose(
            stereoMix.samples,
            [centerGain + 0.25, centerGain + 0.75, (-0.5 * centerGain) - 0.25, (-0.5 * centerGain) + 0.5],
            atol = 0.000000000001
        )
        np.testing.assert_allclose(monoMix.samples, [1.5, -0.375], atol = 0.000000000001)

    def test_MixDefaultsToStereoOutput(self):
        mono = Sound(samples = [1.0], channels = 1)

        mixed = Sound.Mix([mono], mixGain = 1.0)

        self.assertEqual(mixed.channels, 2)
        np.testing.assert_allclose(mixed.samples, [np.sqrt(0.5), np.sqrt(0.5)])

    def test_InvertFlipsSamplePolarity(self):
        sound = Sound(samples = [1.5, -0.75, 0.0, 0.25], channels = 2)

        inverted = sound.Invert()

        np.testing.assert_array_equal(inverted.samples, [-1.5, 0.75, 0.0, -0.25])
        np.testing.assert_array_equal(inverted.Invert().samples, sound.samples)
        np.testing.assert_array_equal(sound.samples, [1.5, -0.75, 0.0, 0.25])

    def test_DebiasCentersEachChannelIndependently(self):
        sound = Sound(samples = [2.0, 12.0, 4.0, 16.0, 6.0, 20.0], channels = 2)

        debiased = sound.Debias()

        np.testing.assert_array_equal(debiased.samples, [-2.0, -4.0, 0.0, 0.0, 2.0, 4.0])
        np.testing.assert_array_equal(sound.samples, [2.0, 12.0, 4.0, 16.0, 6.0, 20.0])
        np.testing.assert_allclose(debiased.samples.reshape(-1, 2).mean(axis = 0), [0.0, 0.0])

    def test_DebiasHandlesEmptySounds(self):
        debiased = Sound(channels = 1).Debias()

        self.assertEqual(debiased.channels, 1)
        self.assertEqual(debiased.samples.size, 0)

    def test_CompatibleControlsPreserveToneContinuity(self):
        duration = 0.01
        plainSynth = ChirpSynth(channels = 1)
        controlledSynth = ChirpSynth(channels = 1)
        plain = plainSynth.RenderSamples([
            Tone(440.0, duration).Wave("Sine"),
            Tone(440.0, duration).Wave("Sine"),
        ])
        controlled = controlledSynth.RenderSamples([
            Tone(440.0, duration).Wave("Sine"),
            VibratoRate(7.0),
            Wave("Sine"),
            Tone(440.0, duration).Wave("Sine"),
        ])

        np.testing.assert_array_equal(controlled, plain)

    def test_WaveChangesFadeBothSidesOfBoundary(self):
        synth = ChirpSynth(channels = 1)
        duration = 0.01
        samples = synth.RenderSamples([
            Tone(440.0, duration).Wave("Sine"),
            Tone(440.0, duration).Wave("Pulse50"),
        ])
        boundary = int(synth.SAMPLE_RATE * duration)

        self.assertEqual(samples[boundary - 1], 0.0)
        self.assertEqual(samples[boundary], 0.0)

    def test_ToneWaveOverrideDoesNotChangeSequenceDefault(self):
        synth = ChirpSynth(channels = 1)
        duration = 0.01
        samples = synth.RenderSamples([
            Tone(440.0, duration).Wave("Pulse50"),
            Tone(440.0, duration),
        ])
        expected = ChirpSynth(channels = 1).RenderSamples([
            Tone(440.0, duration).Wave("Pulse50"),
            Tone(440.0, duration).Wave("Sine"),
        ])

        np.testing.assert_array_equal(samples, expected)

    def test_FadesReachTheirEndpoints(self):
        dsp = ChirpDSP(channels = 1)
        pcm = dsp.SamplesToBytes([0.75, 0.75])
        duration = 2.0 / dsp.SAMPLE_RATE

        fadedIn = dsp.BytesToSamples(dsp.ApplySoundFadeIn(pcm, duration))
        fadedOut = dsp.BytesToSamples(dsp.ApplySoundFadeOut(pcm, duration))
        cut = dsp.BytesToSamples(dsp.ApplySoundCut(pcm, duration, duration))

        self.assertEqual(fadedIn[0], 0.0)
        self.assertAlmostEqual(fadedIn[-1], 0.75, places = 4)
        self.assertEqual(fadedOut[-1], 0.0)
        self.assertEqual(cut[-1], 0.0)

    def test_LfoWaveControlsAffectFollowingTones(self):
        sineSynth = ChirpSynth(channels = 1)
        squareSynth = ChirpSynth(channels = 1)
        overrideSynth = ChirpSynth(channels = 1)
        duration = 0.02

        sine = sineSynth.RenderSamples([
            Tone(440.0, duration).Vibrato(rate = 20.0).Tremolo(rate = 20.0),
        ])
        square = squareSynth.RenderSamples([
            VibratoWave("Pulse50"),
            TremoloWave("Pulse50"),
            Tone(440.0, duration).Vibrato(rate = 20.0).Tremolo(rate = 20.0),
        ])
        override = overrideSynth.RenderSamples([
            Tone(440.0, duration).Vibrato(rate = 20.0, wave = "Pulse50").Tremolo(rate = 20.0, wave = "Pulse50"),
        ])

        self.assertEqual(len(square), len(sine))
        np.testing.assert_array_equal(override, square)
        self.assertFalse(np.array_equal(square, sine))

    def test_ModChangesToneAndZeroDepthIsNoOp(self):
        plainSynth = ChirpSynth(channels = 1)
        zeroSynth = ChirpSynth(channels = 1)
        modSynth = ChirpSynth(channels = 1)
        duration = 0.02

        plain = plainSynth.RenderSamples([
            Tone(440.0, duration).Wave("Sine"),
        ])
        zero = zeroSynth.RenderSamples([
            Tone(440.0, duration).Wave("Sine").Mod(660.0, depth = 0.0),
        ])
        modded = modSynth.RenderSamples([
            Tone(440.0, duration).Wave("Sine").Mod(660.0, depth = 1.0),
        ])

        np.testing.assert_array_equal(zero, plain)
        self.assertEqual(len(modded), len(plain))
        self.assertFalse(np.array_equal(modded, plain))

    def test_ZeroModulationPreservesToneContinuity(self):
        duration = 0.01
        plain = ChirpSynth(channels = 1).RenderSamples([
            Tone(440.0, duration).Wave("Sine"),
            Tone(440.0, duration).Wave("Sine"),
        ])
        zeroDepth = ChirpSynth(channels = 1).RenderSamples([
            Tone(440.0, duration).Wave("Sine"),
            Tone(440.0, duration).Wave("Sine").Mod(660.0, depth = 0.0),
        ])
        zeroFrequency = ChirpSynth(channels = 1).RenderSamples([
            Tone(440.0, duration).Wave("Sine"),
            Tone(440.0, duration).Wave("Sine").Mod(0.0, depth = 1.0),
        ])

        np.testing.assert_array_equal(zeroDepth, plain)
        np.testing.assert_array_equal(zeroFrequency, plain)

    def test_ModulationTransitionsFadeBothSides(self):
        duration = 0.01
        boundary = int(ChirpSynth.SAMPLE_RATE * duration)
        modToPlain = ChirpSynth(channels = 1).RenderSamples([
            Tone(440.0, duration).Wave("Sine").Mod(660.0),
            Tone(440.0, duration).Wave("Sine"),
        ])
        plainToMod = ChirpSynth(channels = 1).RenderSamples([
            Tone(440.0, duration).Wave("Sine"),
            Tone(440.0, duration).Wave("Sine").Mod(660.0),
        ])

        np.testing.assert_array_equal(
            modToPlain[boundary - 1:boundary + 1],
            [0.0, 0.0]
        )
        np.testing.assert_array_equal(
            plainToMod[boundary - 1:boundary + 1],
            [0.0, 0.0]
        )

    def test_ModulationPhaseContinuesAcrossCompatibleTones(self):
        duration = 0.013
        oneTone = ChirpSynth(channels = 1).RenderSamples([
            Tone(440.0, duration * 2.0).Wave("Sine").Mod(660.0),
        ])
        twoTones = ChirpSynth(channels = 1).RenderSamples([
            Tone(440.0, duration).Wave("Sine").Mod(660.0),
            Tone(440.0, duration).Wave("Sine").Mod(660.0),
        ])

        self.assertEqual(len(twoTones), len(oneTone))
        difference = max(
            abs(twoSample - oneSample)
            for twoSample, oneSample in zip(twoTones, oneTone)
        )
        self.assertLess(difference, 0.000000000001)

    def test_TremoloPhaseContinuesAcrossCompatibleTones(self):
        duration = 0.013
        oneTone = ChirpSynth(channels = 1).RenderSamples([
            Tone(440.0, duration * 2.0).Wave("Sine").Tremolo(
                depth = 1.0,
                rate = 7.0
            ),
        ])
        twoTones = ChirpSynth(channels = 1).RenderSamples([
            Tone(440.0, duration).Wave("Sine").Tremolo(
                depth = 1.0,
                rate = 7.0
            ),
            Tone(440.0, duration).Wave("Sine").Tremolo(
                depth = 1.0,
                rate = 7.0
            ),
        ])

        self.assertEqual(len(twoTones), len(oneTone))
        difference = max(
            abs(twoSample - oneSample)
            for twoSample, oneSample in zip(twoTones, oneTone)
        )
        self.assertLess(difference, 0.000000000001)

    def test_TremoloWaveChangesFadeBothSides(self):
        duration = 0.013
        boundary = int(ChirpSynth.SAMPLE_RATE * duration)
        samples = ChirpSynth(channels = 1).RenderSamples([
            Tone(440.0, duration).Wave("Sine").Tremolo(
                depth = 1.0,
                rate = 7.0
            ),
            TremoloWave("Pulse50"),
            Tone(440.0, duration).Wave("Sine").Tremolo(
                depth = 1.0,
                rate = 7.0
            ),
        ])

        np.testing.assert_array_equal(
            samples[boundary - 1:boundary + 1],
            [0.0, 0.0]
        )

    def test_ToneRecipeChangesFadeBothSides(self):
        duration = 0.013
        boundary = int(ChirpSynth.SAMPLE_RATE * duration) * 2
        changedTones = (
            Tone(660.0, duration, 0.8).Wave("Sine"),
            Tone(440.0, duration, 0.4).Wave("Sine"),
            Tone(440.0, duration, 0.8).Wave("Sine").Pan(1.0),
            Tone(440.0, duration, 0.8).Wave("Sine").Vibrato(depth = 20.0),
            Tone(440.0, duration, 0.8).Wave("Sine").Bend(660.0, "insine"),
            Tone(440.0, duration, 0.8).Wave("Sine").Fade(0.4, "outsine"),
        )

        for changedTone in changedTones:
            with self.subTest(tone = changedTone):
                samples = ChirpSynth(channels = 2).RenderSamples([
                    Tone(440.0, duration, 0.8).Wave("Sine"),
                    changedTone,
                ])
                np.testing.assert_array_equal(
                    samples[boundary - 2:boundary + 2],
                    [0.0, 0.0, 0.0, 0.0]
                )

    def test_WaveGeneratorsUseRawAmplitude(self):
        synth = ChirpSynth(channels = 1)
        samples, _, _, _ = MakeTone(
            synth,
            440.0,
            0.01,
            wave = synth.oscillator.Pulse50,
            fadeIn = False,
            fadeOut = False
        )

        self.assertEqual(max(samples), 1.0)
        self.assertEqual(min(samples), -1.0)
        self.assertFalse(hasattr(synth, "GetWaveGain"))
        self.assertFalse(hasattr(synth, "MakeTone"))

    def test_ToneAmplitudeAndFadeTargetsUseLinearGain(self):
        synth = ChirpSynth(channels = 1)
        samples, _, _, _ = MakeTone(
            synth,
            440.0,
            0.01,
            wave = synth.oscillator.Pulse50,
            amplitude = 0.5,
            fadeIn = False,
            fadeOut = False
        )
        fadedSamples, _, _, _ = MakeTone(
            synth,
            440.0,
            0.01,
            wave = synth.oscillator.Pulse50,
            amplitude = 0.8,
            amplitudeBend = 0.4,
            fadeIn = False,
            fadeOut = False
        )

        self.assertEqual(max(samples), 0.5)
        self.assertEqual(min(samples), -0.5)
        self.assertAlmostEqual(abs(fadedSamples[0]), 0.8)
        self.assertAlmostEqual(abs(fadedSamples[-1]), 0.4)

    def test_DynamicsProvideEqualDecibelGainSteps(self):
        gains = [
            D.D01,
            D.D03,
            D.D05,
            D.D07,
            D.D09,
            D.D11,
            D.D13,
            D.D15,
        ]

        self.assertIs(D, Dynamics)
        self.assertEqual(D.D00, 0.0)
        self.assertEqual(gains[0], 1.0 / 128.0)
        self.assertEqual(gains[-1], 1.0)
        for lowerGain, higherGain in zip(gains, gains[1:]):
            self.assertEqual(higherGain, lowerGain * 2.0)

        for lowerGain, middleGain, higherGain in (
                (D.D01, D.D02, D.D03),
                (D.D03, D.D04, D.D05),
                (D.D05, D.D06, D.D07),
                (D.D07, D.D08, D.D09),
                (D.D09, D.D10, D.D11),
                (D.D11, D.D12, D.D13),
                (D.D13, D.D14, D.D15)
                ):
            self.assertEqual(middleGain, np.sqrt(lowerGain * higherGain))

    def test_LfoValuesRemainBipolar(self):
        for waveName in (
                "Sine", "Triangle", "Saw", "Pulse50", "Pulse25", "Pulse12",
                "TriangleAA", "SawAA", "Pulse50AA", "Pulse25AA", "Pulse12AA",
                "Noise", "NoiseLP", "NoiseHP", "NoiseBP", "NoiseStep",
                "NoiseQuanta"
                ):
            synth = ChirpSynth(channels = 1)
            wave = synth.oscillator.GetWave(waveName)
            values = [
                synth.oscillator.GetLfoValue(wave, (2.0 * 3.141592653589793 * i) / 1000.0)
                for i in range(1000)
            ]

            self.assertGreaterEqual(min(values), -1.0, waveName)
            self.assertLessEqual(max(values), 1.0, waveName)

    def test_QuantaNoiseUsesBinaryStatesAndFrequencyControlledDensity(self):
        sampleRate = ChirpSynth.SAMPLE_RATE
        sampleCount = sampleRate

        sparseSynth = ChirpSynth(channels = 1)
        sparseWave = sparseSynth.oscillator.GetWave("NoiseQuanta")
        sparse = np.asarray([
            sparseWave(index / sampleRate, 20.0)
            for index in range(sampleCount)
        ])

        denseSynth = ChirpSynth(channels = 1)
        denseWave = denseSynth.oscillator.GetWave("NoiseQuanta")
        dense = np.asarray([
            denseWave(index / sampleRate, 20000.0)
            for index in range(sampleCount)
        ])

        self.assertEqual(set(np.unique(sparse)), {-1.0, 1.0})
        self.assertEqual(set(np.unique(dense)), {-1.0, 1.0})
        sparseTransitions = np.count_nonzero(np.diff(sparse))
        denseTransitions = np.count_nonzero(np.diff(dense))
        self.assertGreater(denseTransitions, sparseTransitions * 100)
        self.assertTrue(denseSynth.oscillator.IsNoiseWave(denseWave))

    def test_ZeroFrequencyQuantaNoiseHoldsItsInitialBinaryState(self):
        synth = ChirpSynth(channels = 1)
        wave = synth.oscillator.GetWave("NoiseQuanta")
        samples = [
            wave(index / synth.SAMPLE_RATE, 0.0)
            for index in range(1000)
        ]

        self.assertIn(samples[0], (-1.0, 1.0))
        self.assertEqual(len(set(samples)), 1)

    def test_WaveNamesIgnoreCaseUnderscoresAndHyphens(self):
        synth = ChirpSynth(channels = 1)

        for alias, canonical in (
                ("sine", "Sine"),
                ("TRIANGLE-aa", "TriangleAA"),
                ("pulse_50_AA", "Pulse50AA"),
                ("noise-lp", "NoiseLP"),
                ("noise_quanta", "NoiseQuanta")
                ):
            resolved = synth.oscillator.GetWave(alias)
            expected = synth.oscillator.GetWave(canonical)
            self.assertEqual(resolved.__func__, expected.__func__)

    def test_SoundWaveTablesCollapseStereoAndInterpolateAcrossTheLoop(self):
        sound = Sound(samples = [1.0, -1.0, 0.0, 1.0], channels = 2)
        wave = WaveTable(sound)

        np.testing.assert_array_equal(wave.samples, [0.0, 0.5])
        self.assertEqual(wave.GetValue(0.0), 0.0)
        self.assertEqual(wave.GetValue(0.25), 0.25)
        self.assertEqual(wave.GetValue(0.5), 0.5)
        self.assertEqual(wave.GetValue(0.75), 0.25)
        self.assertEqual(wave.GetValue(1.0), 0.0)

    def test_PhaseRotatesTheStartingPointOfASoundWaveTable(self):
        customWave = Sound(samples = [0.0, 1.0, 0.0, -1.0], channels = 1)
        synth = ChirpSynth(channels = 1)
        centered = synth.RenderSamples([
            Tone(11025.0, 0.01).Wave(customWave).Phase(0.0),
        ])
        quarterTurn = synth.RenderSamples([
            Tone(11025.0, 0.01).Wave(customWave).Phase(90.0),
        ])

        self.assertEqual(centered[200], 0.0)
        self.assertEqual(quarterTurn[200], 1.0)

    def test_SoundWaveTablesWorkAsCarrierAndModulationWaves(self):
        customWave = Sound(samples = [0.0, 1.0, 0.0, -1.0], channels = 1)
        synth = ChirpSynth(channels = 1)
        recipes = (
            [Tone(440.0, 0.01).Wave(customWave)],
            [Tone(440.0, 0.01).Wave("Sine").Vibrato(depth = 20.0, rate = 5.0, wave = customWave)],
            [Tone(440.0, 0.01).Wave("Sine").Tremolo(depth = 0.5, rate = 5.0, wave = customWave)],
            [Tone(440.0, 0.01).Wave("Sine").Mod(freq = 110.0, depth = 0.5, wave = customWave)],
            [Wave(customWave), VibratoWave(customWave), TremoloWave(customWave), Tone(440.0, 0.01)],
        )

        for recipe in recipes:
            with self.subTest(recipe = recipe):
                samples = synth.RenderSamples(recipe)
                self.assertEqual(len(samples), 441)
                self.assertTrue(np.all(np.isfinite(samples)))

    def test_RingAcceptsBuiltInAndSoundWaveTables(self):
        source = Sound(samples = np.ones(8), channels = 1)
        customWave = Sound(samples = [0.0, 1.0, 0.0, -1.0], channels = 1)

        pulseRing = source.Ring(11025.0, wave = "Pulse50")
        customRing = source.Ring(11025.0, wave = customWave)

        np.testing.assert_array_equal(pulseRing.samples, [1.0, 1.0, -1.0, -1.0, 1.0, 1.0, -1.0, -1.0])
        np.testing.assert_allclose(customRing.samples, [0.0, 1.0, 0.0, -1.0, 0.0, 1.0, 0.0, -1.0], atol = 1e-12)

    def test_FailedOutputStartDoesNotLeaveAStuckVoice(self):
        class FailingOutput:
            def __init__(self, **settings):
                pass

            def Start(self):
                raise RuntimeError("Audio device unavailable")

            def GetStats(self):
                return {}

            def Close(self):
                pass

        player = ChirpPlayer(
            channels = 1,
            enabled = True,
            outputFactory = FailingOutput
        )

        try:
            with self.assertRaises(RuntimeError):
                player.Play(b"\x00\x00" * 32)

            self.assertEqual(player.GetStats()["activeVoices"], 0)
        finally:
            player.Close()

    def test_AutomaticReverbTailsContainDelayedWetOutput(self):
        impulse = np.array([1.0], dtype = np.float64)
        dsp = ChirpDSP(channels = 1)
        reverbs = (
            dsp.ApplySoundSchroverb(impulse, wet = 1.0, decay = 0.0),
            dsp.ApplySoundFreeverb(impulse, wet = 1.0, decay = 0.0),
            dsp.ApplySoundMTVerb(impulse, wet = 1.0, decay = 0.0, mode = "room"),
            dsp.ApplySoundMTVerb(impulse, wet = 1.0, decay = 0.0, mode = "hall"),
            dsp.ApplySoundMTVerb(impulse, wet = 1.0, decay = 0.0, mode = "plate"),
        )

        for reverbed in reverbs:
            self.assertGreater(np.max(np.abs(reverbed)), 0.0)
            self.assertGreater(len(reverbed), 1)

    def test_StatefulNoiseUsesEveryScheduledFrameIndex(self):
        class CountingRandom:
            def __init__(self):
                self.calls = 0

            def random(self):
                self.calls += 1
                return 0.25

        oscillator = ChirpSynth(channels = 1).oscillator
        counter = CountingRandom()
        oscillator.random = counter
        for frame in range(44100):
            oscillator.NoiseStep(frame / 44100.0, 4000.0)

        self.assertEqual(counter.calls // 2, 4010)

    def test_CustomZeroFrequencyWaveRetainsPhase(self):
        def CustomSine(time, frequency):
            return math.sin(2.0 * math.pi * frequency * time)

        oscillator = ChirpSynth(channels = 1).oscillator
        rendered = oscillator.RenderWave(CustomSine, 0.0, 3, phaseDegrees = 90.0)

        np.testing.assert_allclose(rendered, np.ones(3), rtol = 0.0, atol = 1e-12)

    def test_InvalidEmptySweepFailsWithAndWithoutAcceleration(self):
        previous = ChirpKernels.NUMBA_ENABLED
        try:
            for enabled in (False, True):
                ChirpKernels.SetNumbaEnabled(enabled)
                with self.assertRaises(ValueError):
                    ChirpDSP(channels = 1).ApplySoundBiquadSweep(
                        [], "invalid", 100.0, 1000.0
                    )
                with self.assertRaises(ValueError):
                    ChirpDSP(channels = 1).ApplySoundLowPassSweep(
                        [], 100.0, 1000.0, easing = "invalid"
                    )
        finally:
            ChirpKernels.SetNumbaEnabled(previous)

    def test_ExtremeEqualizerGainRaisesControlledErrors(self):
        dsp = ChirpDSP(channels = 1)
        for db in (-20000.0, 20000.0):
            with self.subTest(db = db):
                with self.assertRaises(ValueError):
                    dsp.ApplySoundPeak([1.0], 1000.0, db)
                with self.assertRaises(ValueError):
                    dsp.ApplySoundHighShelfSweep([], 100.0, 1000.0, db)

    def test_StereoPingPongPreservesAntiPhaseInput(self):
        sound = Sound(samples = [1.0, -1.0], channels = 2)
        delayed = sound.PingPong(
            delay = 1.0 / 44100.0, decay = 0.5,
            count = 1, width = 1.0
        )

        frames = delayed.samples.reshape(-1, 2)
        np.testing.assert_array_equal(frames[0], [1.0, -1.0])
        np.testing.assert_array_equal(frames[1], [-0.5, 0.5])

    def test_AutomaticDelayCountUsesTheTailDurationPolicy(self):
        dsp = ChirpDSP(channels = 1)

        self.assertEqual(dsp.GetDelayCount(0.999, None, 0.25), 120)
        self.assertGreater(dsp.GetDelayCount(0.999, None, 0.001), 64)

    def test_TwoFrameToneFadesItsFinalSample(self):
        synthesizer = ChirpSynth(channels = 1)
        samples, _, _, _ = MakeTone(
            synthesizer,
            440.0, 2.0 / synthesizer.SAMPLE_RATE,
            wave = synthesizer.oscillator.Sine
        )

        self.assertEqual(samples[-1], 0.0)

    def test_BiquadFadeOnlyChangesTheSilentEndpointRegion(self):
        previous = ChirpKernels.NUMBA_ENABLED
        try:
            for accelerated in (False, True) if ChirpKernels.NUMBA_AVAILABLE else (False,):
                ChirpKernels.SetNumbaEnabled(accelerated)
                for channels in (1, 2):
                    for frameCount in (0, 1, 2, 64, 300):
                        with self.subTest(
                                accelerated = accelerated, channels = channels,
                                frameCount = frameCount
                                ):
                            dsp = ChirpDSP(channels = channels)
                            source = np.full((frameCount, channels), 0.5)
                            if channels == 2:
                                source[:, 1] = -0.25
                            coefficients = (1.0, 0.5, 0.0, 0.0, 0.0)

                            # This FIR has the independent response y[n] = x[n] + x[n - 1] / 2.
                            expected = source.copy()
                            expected[1:] += source[:-1] * 0.5
                            filtered = dsp.ApplySoundBiquad(source, coefficients)
                            np.testing.assert_array_equal(filtered, expected.reshape(-1))

                            if frameCount == 0:
                                continue
                            source[-1] = 0.0
                            original = source.copy()
                            expected = source.copy()
                            expected[1:] += source[:-1] * 0.5
                            fadeFrames = min(132, frameCount)  # 3 ms at 44.1 kHz.
                            for frame in range(fadeFrames):
                                gain = 0.0 if fadeFrames == 1 else 1.0 - (frame / (fadeFrames - 1))
                                expected[frameCount - fadeFrames + frame] *= gain

                            filtered = dsp.ApplySoundBiquad(source, coefficients)
                            np.testing.assert_allclose(
                                filtered, expected.reshape(-1), rtol = 0.0, atol = 1e-15
                            )
                            np.testing.assert_array_equal(filtered[-channels:], 0.0)
                            np.testing.assert_array_equal(source, original)

                            if channels == 2:
                                # A zero in just one channel does not make the frame silent.
                                source[-1, 1] = -0.25
                                expected = source.copy()
                                expected[1:] += source[:-1] * 0.5
                                filtered = dsp.ApplySoundBiquad(source, coefficients)
                                np.testing.assert_array_equal(filtered, expected.reshape(-1))
        finally:
            ChirpKernels.SetNumbaEnabled(previous)

    def test_AllBiquadFiltersAndSweepsPreserveSilentEndpoints(self):
        previous = ChirpKernels.NUMBA_ENABLED
        try:
            for accelerated in (False, True) if ChirpKernels.NUMBA_AVAILABLE else (False,):
                ChirpKernels.SetNumbaEnabled(accelerated)
                for channels in (1, 2):
                    dsp = ChirpDSP(channels = channels)
                    source = np.full((300, channels), 0.5)
                    source[-1] = 0.0
                    for filterName in (
                            "LowPass", "HighPass", "BandPass", "Notch",
                            "Peak", "LowShelf", "HighShelf"
                            ):
                        gainArgs = (3.0,) if filterName in ("Peak", "LowShelf", "HighShelf") else ()
                        for sweep in (False, True):
                            with self.subTest(
                                    accelerated = accelerated, channels = channels,
                                    filterName = filterName, sweep = sweep
                                    ):
                                methodName = "ApplySound" + filterName + ("Sweep" if sweep else "")
                                frequencies = (300.0, 1800.0) if sweep else (900.0,)
                                filtered = getattr(dsp, methodName)(source, *frequencies, *gainArgs)
                                self.assertEqual(len(filtered), source.size)
                                self.assertTrue(np.all(np.isfinite(filtered)))
                                self.assertGreater(np.max(np.abs(filtered)), 0.0)
                                np.testing.assert_array_equal(filtered[-channels:], 0.0)
        finally:
            ChirpKernels.SetNumbaEnabled(previous)

    def test_DspRejectsFractionalCounts(self):
        with self.assertRaises(TypeError):
            ChirpDSP(channels = 1).GetEasingValues(3.5)

if __name__ == "__main__":
    unittest.main()
