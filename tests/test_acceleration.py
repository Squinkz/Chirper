import unittest

import numpy as np

from Chirper import Seconds, Tone
from Chirper.core import ChirpKernels
from Chirper.core.ChirpDSP import ChirpDSP
from Chirper.core.ChirpSynth import ChirpSynth
from tests.render_helpers import MakeTone


class NumbaAccelerationTests(unittest.TestCase):
    def setUp(self):
        self.numbaWasEnabled = ChirpKernels.NUMBA_ENABLED

    def tearDown(self):
        ChirpKernels.SetNumbaEnabled(self.numbaWasEnabled)

    def test_FallbackRenderingWorksWithoutNumba(self):
        ChirpKernels.SetNumbaEnabled(False)
        samples = ChirpSynth(channels = 1).RenderSamples([
            Seconds(),
            Tone(440.0, 0.01, 0.5).Wave("Sine"),
        ])

        self.assertEqual(len(samples), 441)
        self.assertFalse(ChirpKernels.NUMBA_ENABLED)

    def test_CustomWaveFunctionsRetainThePythonFallback(self):
        callCount = 0

        def CustomWave(time, frequency):
            nonlocal callCount
            callCount += 1
            return np.sin(2.0 * np.pi * frequency * time)

        ChirpKernels.SetNumbaEnabled(True)
        samples = ChirpSynth(channels = 1).RenderSamples([
            Seconds(),
            Tone(440.0, 0.01, 0.5).Wave(CustomWave),
        ])

        self.assertEqual(len(samples), 441)
        self.assertEqual(callCount, 441)

    @unittest.skipUnless(
        ChirpKernels.NUMBA_AVAILABLE,
        "Numba acceleration is unavailable"
    )
    def test_CustomEasingUsesLocalSynthesisFallback(self):
        callCount = 0

        def CustomEasing(t):
            nonlocal callCount
            callCount += 1
            return t * t

        ChirpKernels.SetNumbaEnabled(True)
        samples = ChirpSynth(channels = 1).RenderSamples([
            Seconds(),
            (
                Tone(440.0, 0.01, 0.5).Wave("Sine")
                .Bend(660.0, CustomEasing)
                .Fade(0.25, CustomEasing)
            ),
        ])

        self.assertEqual(len(samples), 441)
        self.assertEqual(callCount, 882)
        self.assertTrue(ChirpKernels.NUMBA_ENABLED)

    @unittest.skipUnless(
        ChirpKernels.NUMBA_AVAILABLE,
        "Numba acceleration is unavailable"
    )
    def test_CustomEasingUsesLocalPerformanceBendFallback(self):
        callCount = 0

        def CustomEasing(t):
            nonlocal callCount
            callCount += 1
            return t * t

        synthesizer = ChirpSynth(channels = 1)
        ChirpKernels.SetNumbaEnabled(True)
        samples = MakeTone(
            synthesizer,
            440.0,
            0.01,
            performanceBend = 660.0,
            performanceBendEasing = CustomEasing
        )[0]

        self.assertEqual(len(samples), 441)
        self.assertEqual(callCount, 441)
        self.assertTrue(ChirpKernels.NUMBA_ENABLED)

    @unittest.skipUnless(
        ChirpKernels.NUMBA_AVAILABLE,
        "Numba acceleration is unavailable"
    )
    def test_CustomEasingUsesLocalBiquadSweepFallback(self):
        callCount = 0

        def CustomEasing(t):
            nonlocal callCount
            callCount += 1
            return t * t

        dsp = ChirpDSP(channels = 1)
        source = np.sin(np.arange(441, dtype = np.float64) * 0.1)
        ChirpKernels.SetNumbaEnabled(True)
        custom = dsp.ApplySoundLowPassSweep(
            source, 300.0, 3000.0, easing = CustomEasing
        )
        builtIn = dsp.ApplySoundLowPassSweep(
            source, 300.0, 3000.0, easing = "inQuad"
        )

        self.assertEqual(callCount, 441)
        self.assertTrue(ChirpKernels.NUMBA_ENABLED)
        np.testing.assert_allclose(custom, builtIn, rtol = 0.0, atol = 5e-15)

    @unittest.skipUnless(
        ChirpKernels.NUMBA_AVAILABLE,
        "Numba acceleration is unavailable"
    )
    def test_AcceleratedAndFallbackSynthesisMatch(self):
        waveSettings = (
            ("Saw", "Saw", "Triangle", "Sine"),
            (
                "SawAA",
                "Pulse25AA",
                "SawAA",
                "Pulse12AA"
            ),
            (
                "TriangleAA",
                "TriangleAA",
                "TriangleAA",
                "Pulse50AA"
            ),
        )

        for (
                carrierWave, modWave,
                vibratoWave, tremoloWave
                ) in waveSettings:
            with self.subTest(wave = carrierWave):
                synthesizer = ChirpSynth(channels = 1)
                plan = synthesizer.CompileSequence([
                    Seconds(),
                    (
                        Tone(220.0, 0.04, 0.7)
                        .Wave(carrierWave)
                        .Vibrato(
                            rate = 5.5,
                            wave = vibratoWave
                        )
                        .Tremolo(
                            0.3,
                            7.0,
                            tremoloWave
                        )
                        .Mod(83.0, 1.1, modWave)
                        .Bend(330.0, "inoutback")
                        .Fade(0.35, "outelastic")
                    ),
                ])

                ChirpKernels.SetNumbaEnabled(False)
                fallback = synthesizer.RenderSamples(plan)
                ChirpKernels.SetNumbaEnabled(True)
                accelerated = synthesizer.RenderSamples(plan)

                np.testing.assert_allclose(
                    accelerated,
                    fallback,
                    rtol = 0.0,
                    atol = 1e-13
                )
                self.assertEqual(
                    ChirpDSP(
                        channels = 1
                    ).SamplesToBytes(accelerated),
                    ChirpDSP(
                        channels = 1
                    ).SamplesToBytes(fallback)
                )

    @unittest.skipUnless(
        ChirpKernels.NUMBA_AVAILABLE,
        "Numba acceleration is unavailable"
    )
    def test_AcceleratedAndFallbackStepBendsMatch(self):
        synthesizer = ChirpSynth(channels = 1)
        arguments = {
            "freq": 220.0,
            "duration": 0.04,
            "wave": synthesizer.oscillator.Sine,
            "performanceBend": 440.0,
            "performanceBendEasing": "inoutquad",
            "performanceBendStepped": True,
        }

        ChirpKernels.SetNumbaEnabled(False)
        fallback = MakeTone(synthesizer, **arguments)[0]
        ChirpKernels.SetNumbaEnabled(True)
        accelerated = MakeTone(synthesizer, **arguments)[0]

        np.testing.assert_allclose(
            accelerated, fallback, rtol = 0.0, atol = 1e-13
        )

    @unittest.skipUnless(
        ChirpKernels.NUMBA_AVAILABLE,
        "Numba acceleration is unavailable"
    )
    def test_AcceleratedAndFallbackDSPMatch(self):
        dsp = ChirpDSP(channels = 2)
        timeValues = np.arange(2205, dtype = np.float64) / dsp.SAMPLE_RATE
        mono = np.sin(2.0 * np.pi * 220.0 * timeValues) * 0.5
        samples = np.repeat(mono, 2)
        effects = {
            "biquad": lambda: dsp.ApplySoundLowPass(
                samples,
                1800.0
            ),
            "biquadSweep": lambda: dsp.ApplySoundLowPassSweep(
                samples,
                300.0,
                3000.0,
                easing = "inoutlog"
            ),
            "schroverb": lambda: dsp.ApplySoundSchroverb(
                samples,
                tail = 0.02
            ),
            "freeverb": lambda: dsp.ApplySoundFreeverb(
                samples,
                tail = 0.02
            ),
            "mtverb": lambda: dsp.ApplySoundMTVerb(
                samples,
                tail = 0.02
            ),
        }

        for effectName, applyEffect in effects.items():
            with self.subTest(effect = effectName):
                ChirpKernels.SetNumbaEnabled(False)
                fallback = applyEffect()
                ChirpKernels.SetNumbaEnabled(True)
                accelerated = applyEffect()

                np.testing.assert_allclose(
                    accelerated,
                    fallback,
                    rtol = 0.0,
                    atol = 5e-15
                )
                self.assertEqual(
                    dsp.SamplesToBytes(accelerated),
                    dsp.SamplesToBytes(fallback)
                )


if __name__ == "__main__":
    unittest.main()
