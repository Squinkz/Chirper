import math
import unittest

import numpy as np

from Chirper.composition.ChirpPatch import Patch
from Chirper.composition.ChirpSequence import Note, Sequence, SetPatch
from Chirper.core import ChirpKernels
from Chirper.core.ChirpDSP import ChirpDSP
from Chirper.core.ChirpSound import Sound
from Chirper.core.ChirpSynth import ChirpSynth
from Chirper.core.ChirpTone import Tone


class UnisonTests(unittest.TestCase):
    def test_CoincidentUnisonVoicesPreserveTheOriginalLevel(self):
        synthesizer = ChirpSynth(channels = 1)
        original = synthesizer.RenderSamples([
            Tone(440.0, 0.02, 0.8).Wave("Sine"),
        ])
        unison = synthesizer.RenderSamples([
            Tone(440.0, 0.02, 0.8).Wave("Sine").Unison(5, 0.0, 0.0),
        ])

        np.testing.assert_allclose(unison, original, rtol = 0.0, atol = 1e-15)

    def test_UnisonPreservesPhaseAcrossCompatibleTones(self):
        oneTone = ChirpSynth(channels = 2).RenderSamples([
            Tone(440.0, 0.04, 0.8).Wave("SawAA").Unison(3, 12.0, 0.8),
        ])
        twoTones = ChirpSynth(channels = 2).RenderSamples([
            Tone(440.0, 0.02, 0.8).Wave("SawAA").Unison(3, 12.0, 0.8),
            Tone(440.0, 0.02, 0.8).Wave("SawAA").Unison(3, 12.0, 0.8),
        ])

        np.testing.assert_allclose(twoTones, oneTone, rtol = 0.0, atol = 2e-13)

    def test_UnisonSupportsSoundWaveTables(self):
        customWave = Sound(samples = [0.0, 1.0, 0.0, -1.0], channels = 1)
        samples = ChirpSynth(channels = 2).RenderSamples([
            Tone(440.0, 0.01).Wave(customWave).Unison(4, 8.0, 1.0),
        ])

        self.assertEqual(len(samples), 882)
        self.assertTrue(np.all(np.isfinite(samples)))
        self.assertFalse(np.array_equal(samples[0::2], samples[1::2]))

    def test_UnisonRejectsNoiseWaves(self):
        with self.assertRaises(ValueError):
            ChirpSynth(channels = 1).CompileSequence([
                Tone(1000.0, 0.01).Wave("Noise").Unison(),
            ])


class ModulationEffectTests(unittest.TestCase):
    def setUp(self):
        self.numbaWasEnabled = ChirpKernels.NUMBA_ENABLED

    def tearDown(self):
        ChirpKernels.SetNumbaEnabled(self.numbaWasEnabled)

    def test_ChorusUsesFractionalDelayInterpolation(self):
        dsp = ChirpDSP(channels = 1)
        source = np.array([1.0, 0.0, 0.0, 0.0], dtype = np.float64)
        delay = 1.5 / dsp.SAMPLE_RATE
        chorused = dsp.ApplySoundChorus(
            source, rate = 0.0, depth = 0.0, delay = delay,
            voices = 1, feedback = 0.0, mix = 1.0
        )

        np.testing.assert_allclose(chorused, [0.0, 0.5, 0.5, 0.0], rtol = 0.0, atol = 1e-15)

    def test_PhaserUsesTheExistingAllPassRecurrence(self):
        dsp = ChirpDSP(channels = 1)
        source = np.zeros(32, dtype = np.float64)
        source[0] = 1.0
        frequency = 1000.0
        tangent = math.tan(math.pi * frequency / dsp.SAMPLE_RATE)
        coefficient = (1.0 - tangent) / (1.0 + tangent)

        expected = dsp.AllPassFilterFrames(source, 1, coefficient)
        phased = dsp.ApplySoundPhaser(
            source, rate = 0.0, minFreq = frequency, maxFreq = frequency,
            stages = 1, feedback = 0.0, mix = 1.0
        )

        np.testing.assert_allclose(phased, expected, rtol = 0.0, atol = 1e-15)

    def test_ChorusAndPhaserPreserveChannelsAndDuration(self):
        source = Sound(
            samples = np.sin(np.arange(2048, dtype = np.float64) * 0.1),
            channels = 2
        )

        for processed in (source.Chorus(), source.Phaser()):
            with self.subTest(effect = type(processed)):
                self.assertEqual(processed.channels, source.channels)
                self.assertEqual(processed.duration, source.duration)
                self.assertTrue(np.all(np.isfinite(processed.samples)))

    def test_ModulationEffectsAcceptSoundWaveTables(self):
        customWave = Sound(samples = [-1.0, 0.0, 1.0, 0.0], channels = 1)
        source = Sound(samples = np.linspace(-0.5, 0.5, 512), channels = 1)

        chorus = source.Chorus(wave = customWave)
        phaser = source.Phaser(wave = customWave)

        self.assertEqual(len(chorus.samples), len(source.samples))
        self.assertEqual(len(phaser.samples), len(source.samples))

    def test_ZeroMixReturnsTheOriginalSignal(self):
        source = Sound(samples = [0.2, -0.4, 0.6], channels = 1)

        np.testing.assert_array_equal(source.Chorus(mix = 0.0).samples, source.samples)
        np.testing.assert_array_equal(source.Phaser(mix = 0.0).samples, source.samples)

    def test_ModulationEffectsPreservePcmRepresentation(self):
        dsp = ChirpDSP(channels = 1)
        source = dsp.SamplesToBytes([0.2, -0.4, 0.6, -0.8])

        self.assertIsInstance(dsp.ApplySoundChorus(source), bytes)
        self.assertIsInstance(dsp.ApplySoundPhaser(source), bytes)

    def test_AutoPanUsesOneEqualPowerPanPosition(self):
        dsp = ChirpDSP(channels = 1)
        source = np.ones(4, dtype = np.float64)
        panned = dsp.ApplySoundAutoPan(
            source, rate = dsp.SAMPLE_RATE / 4.0, wave = "Sine"
        ).reshape(-1, 2)
        center = math.sqrt(0.5)

        np.testing.assert_allclose(
            panned,
            [
                [center, center],
                [0.0, 1.0],
                [center, center],
                [1.0, 0.0],
            ],
            rtol = 0.0,
            atol = 1e-12
        )

    def test_AutoPanRotatesStereoAndPreservesPcmRepresentation(self):
        dsp = ChirpDSP(channels = 2)
        source = np.array([0.25, 0.75, -0.5, 0.2], dtype = np.float64)
        right = dsp.ApplySoundAutoPan(source, rate = 0.0, offset = 90.0)
        left = dsp.ApplySoundAutoPan(source, rate = 0.0, offset = -90.0)
        pcm = dsp.SamplesToBytes(source)

        np.testing.assert_allclose(right, [0.0, 1.0, 0.0, -0.3], atol = 1e-15)
        np.testing.assert_allclose(left, [1.0, 0.0, -0.3, 0.0], atol = 1e-15)
        self.assertIsInstance(
            dsp.ApplySoundAutoPan(pcm, rate = 0.0, offset = 90.0), bytes
        )

    def test_SoundAutoPanPromotesMonoAndAcceptsSoundWaves(self):
        source = Sound(samples = [0.25, -0.5, 0.75], channels = 1)
        customWave = Sound(samples = [1.0], channels = 1)
        panned = source.AutoPan(rate = 2.0, wave = customWave)

        self.assertEqual(panned.channels, 2)
        np.testing.assert_allclose(panned.samples[0::2], 0.0, atol = 1e-15)
        np.testing.assert_allclose(panned.samples[1::2], source.samples, atol = 1e-15)

    def test_ToneAutoPanContinuesAcrossCompatibleTones(self):
        duration = 0.013
        oneTone = ChirpSynth(channels = 2).RenderSamples([
            Tone(440.0, duration * 2.0).Wave("Sine").AutoPan(
                depth = 0.8, rate = 7.0, offset = 20.0
            ),
        ])
        twoTones = ChirpSynth(channels = 2).RenderSamples([
            Tone(440.0, duration).Wave("Sine").AutoPan(
                depth = 0.8, rate = 7.0, offset = 20.0
            ),
            Tone(440.0, duration).Wave("Sine").AutoPan(
                depth = 0.8, rate = 7.0, offset = 20.0
            ),
        ])

        np.testing.assert_allclose(twoTones, oneTone, rtol = 0.0, atol = 2e-13)

    def test_NoteAutoPanAppliesAfterThePatch(self):
        def Body(freq, dur, amp):
            return [Tone(freq, dur, amp).Wave("Sine").Phase(90.0)]

        sequence = Sequence([
            SetPatch(Patch(body = Body)),
            Note(0, 0.0, 440.0, 0.01).AutoPan(rate = 0.0, offset = -90.0),
        ])
        panned = Sound(sequence, channels = 2)

        np.testing.assert_allclose(panned.samples[1::2], 0.0, atol = 1e-15)
        self.assertGreater(np.max(np.abs(panned.samples[0::2])), 0.5)

    def test_ToneAutoPanContinuesAcrossMonophonicNotes(self):
        def Body(freq, dur, amp):
            return [Tone(freq, dur, amp).Wave("Sine").AutoPan(
                depth = 0.8, rate = 3.0, offset = 20.0
            )]

        patch = Patch(body = Body, polyphonic = False)
        held = Sound(Sequence([
            SetPatch(patch),
            Note(0, 0.0, 440.0, 0.5),
        ]), channels = 2)
        legato = Sound(Sequence([
            SetPatch(patch),
            Note(0, 0.0, 440.0, 0.25),
            Note(0, 1.0, 440.0, 0.25),
        ]), channels = 2)

        np.testing.assert_allclose(legato.samples, held.samples, rtol = 0.0, atol = 1e-12)

    @unittest.skipUnless(ChirpKernels.NUMBA_AVAILABLE, "Numba acceleration is unavailable")
    def test_CompiledAndPythonModulationEffectsMatch(self):
        dsp = ChirpDSP(channels = 2)
        source = np.sin(np.arange(4096, dtype = np.float64) * 0.071) * 0.6
        effects = (
            lambda: dsp.ApplySoundChorus(
                source, rate = 0.73, depth = 0.0027, delay = 0.014,
                voices = 3, feedback = 0.2, spread = 0.8, mix = 0.6,
                wave = "TriangleAA"
            ),
            lambda: dsp.ApplySoundPhaser(
                source, rate = 0.41, minFreq = 180.0, maxFreq = 2400.0,
                stages = 8, feedback = 0.35, spread = 0.7, mix = 0.55,
                wave = "Sine"
            ),
        )

        for effect in effects:
            ChirpKernels.SetNumbaEnabled(False)
            fallback = effect()
            ChirpKernels.SetNumbaEnabled(True)
            accelerated = effect()

            np.testing.assert_allclose(accelerated, fallback, rtol = 0.0, atol = 1e-12)
            self.assertEqual(dsp.SamplesToBytes(accelerated), dsp.SamplesToBytes(fallback))


if __name__ == "__main__":
    unittest.main()
