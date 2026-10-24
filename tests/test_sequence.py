import copy
from fractions import Fraction
import math
import unittest
import warnings

import numpy as np

from Chirper.composition.ChirpPatch import Envelope, Patch
from Chirper.composition.ChirpPatches import Patches
from Chirper.composition.ChirpSequence import Meter, Note, Sequence, SetPatch
from Chirper.core import ChirpKernels
from Chirper.core.ChirpConstants import (
    D, ER, ES, JR, JS, L, N, Q, T, V,
    Dynamics, EqualNote, EqualRatio, EqualScale, JustRatio, JustScale,
    NoteFrequency, NoteLength, QFactor, Tremolo, Vibrato
)
from Chirper.core.ChirpDSP import ChirpDSP
from Chirper.core.ChirpSound import Sound
from Chirper.core.ChirpSynth import ChirpRenderPlan, ChirpSynth
from Chirper.core.ChirpTone import Insert, PerformanceFrequency, Pitch, Seconds, Tone, Tempo, Wave
from tests.render_helpers import MakeTone


class PatchTests(unittest.TestCase):
    def test_ConstantNamespacesCannotBeModified(self):
        constantNamespaces = (
            JustRatio, EqualRatio, JustScale, EqualScale, NoteFrequency,
            EqualNote, NoteLength, Vibrato, Tremolo, Dynamics, QFactor,
            JR, ER, JS, ES, N, L, V, T, D, Q
        )

        for constantNamespace in constantNamespaces:
            namespaceName = getattr(
                constantNamespace, "__name__", type(constantNamespace).__name__
            )
            with self.subTest(constantNamespace = namespaceName):
                with self.assertRaises(AttributeError):
                    setattr(constantNamespace, "TEST_VALUE", 1.0)

        with self.assertRaises(AttributeError):
            N.C4 = 500.0
        with self.assertRaises(AttributeError):
            ES.MAJOR = (1.0,)
        with self.assertRaises(AttributeError):
            del ES.MAJOR
        with self.assertRaises(TypeError):
            ES.MAJOR[0] = 2.0

        self.assertIs(ES.IONIAN, ES.MAJOR)
        self.assertIs(JS.PENTA, JS.PENTA_MIN)

    def test_BuiltInPatchesCannotBeModified(self):
        builtInPatches = (
            Patches.Sine, Patches.Triangle, Patches.Square, Patches.Saw,
            Patches.SuperSine, Patches.SuperTriangle, Patches.SuperSquare,
            Patches.SuperSaw, Patches.CowBell
        )

        for patch in builtInPatches:
            with self.subTest(patch = patch):
                with self.assertRaises(AttributeError):
                    patch.bodyGain = 2.0
                with self.assertRaises(AttributeError):
                    patch.extraSetting = True

        with self.assertRaises(AttributeError):
            Patches.Sine = Patch()
        with self.assertRaises(AttributeError):
            del Patches.Sine

        customPatch = Patch(bodyGain = 0.5)
        customPatch.bodyGain = 0.75
        self.assertEqual(customPatch.bodyGain, 0.75)

    def test_EnvelopeValidatesAndClampsItsValues(self):
        envelope = Envelope(-1.0, -2.0, -3.0, -4.0, retrigger = False)
        noBody = Envelope(0.0, 0.0, None, 0.0)
        boosted = Envelope(0.0, 0.0, 2.5, 0.0)

        self.assertEqual(envelope.attack, 0.0)
        self.assertEqual(envelope.decay, 0.0)
        self.assertEqual(envelope.sustain, 0.0)
        self.assertEqual(envelope.release, 0.0)
        self.assertFalse(envelope.retrigger)
        self.assertEqual(noBody.sustain, 0.0)
        self.assertEqual(boosted.sustain, 2.5)
        self.assertEqual(envelope.attackCurve, -5.0)
        self.assertEqual(envelope.decayCurve, 5.0)
        self.assertEqual(envelope.releaseCurve, 5.0)

        with self.assertRaises(AttributeError):
            envelope.attack = 1.0
        with self.assertRaises(AttributeError):
            del envelope.release

        with self.assertRaises(TypeError):
            Envelope(True, 0.0, 1.0, 0.0)
        with self.assertRaises(ValueError):
            Envelope(float("inf"), 0.0, 1.0, 0.0)
        with self.assertRaises(TypeError):
            Envelope(0.0, 0.0, 1.0, 0.0, retrigger = 1)
        with self.assertRaises(TypeError):
            Envelope(0.0, 0.0, 1.0, 0.0, attackCurve = "invalid")
        with self.assertRaises(ValueError):
            Envelope(0.0, 0.0, 1.0, 0.0, releaseCurve = float("inf"))
        with self.assertRaises(TypeError):
            Patch(envelope = object())

    def test_PatchAcceptsEnvelopeBeforePolyphonyPositionally(self):
        envelope = Envelope(0.01, 0.02, 0.5, 0.03)
        patch = Patch(None, None, 1.0, 1.0, envelope, False, True)

        self.assertIs(patch.envelope, envelope)
        self.assertFalse(patch.polyphonic)
        self.assertTrue(patch.portamento)

    def test_EnvelopeCurveIsNormalizedAndSupportsLinearValues(self):
        linear = Envelope.GetCurveValues(5, 0.0)
        transient = Envelope.GetCurveValues(5, -5.0)
        release = Envelope.GetCurveValues(5, 5.0)

        np.testing.assert_allclose(linear, [0.0, 0.25, 0.5, 0.75, 1.0])
        self.assertEqual(transient[0], 0.0)
        self.assertEqual(transient[-1], 1.0)
        self.assertEqual(release[0], 0.0)
        self.assertEqual(release[-1], 1.0)
        np.testing.assert_allclose(transient, 1.0 - release[::-1], atol = 1e-12)

    def test_EnvelopeShapesOnlyBodyAndExtendsActiveTones(self):
        sampleRate = Patch.SAMPLE_RATE
        envelope = Envelope(
            2.0 / sampleRate,
            2.0 / sampleRate,
            0.5,
            3.0 / sampleRate,
            attackCurve = 0.0,
            decayCurve = 0.0,
            releaseCurve = 0.0
        )
        transient = Sound(samples = np.full(9, 0.25), channels = 1)

        def Transient(freq, dur, amp):
            return [Insert(transient)]

        def Body(freq, dur, amp):
            return [Tone(freq, dur, amp).Wave("Sine").Phase(90.0)]

        patch = Patch(Transient, Body, envelope = envelope)
        samples = patch.RenderSamples(
            440.0, 6.0 / sampleRate, 1.0, channels = 1
        )
        synthesizer = ChirpSynth(channels = 1)
        plan = synthesizer.CompileSequence([
            Seconds(),
            Tone(440.0, 6.0 / sampleRate, 1.0).Wave("Sine").Phase(90.0),
        ])
        event = copy.copy(plan.events[0])
        event.duration = 9.0 / sampleRate
        event.sampleCount = 9
        event.fadeOut = False
        raw = synthesizer.RenderPlan(ChirpRenderPlan(
            synthesizer, [event], event.sampleCount
        ))
        gains = np.array([
            0.0, 1.0,
            1.0, 0.5,
            0.5, 0.5,
            0.5, 0.25, 0.0,
        ])

        self.assertEqual(len(samples), 9)
        np.testing.assert_allclose(samples, 0.25 + (raw * gains), atol = 1e-12)

    def test_EnvelopeDoesNotExtendShortTonesOrInsertedSounds(self):
        sampleRate = Patch.SAMPLE_RATE
        envelope = Envelope(0.0, 0.0, 1.0, 5.0 / sampleRate)
        inserted = Sound(samples = [1.0, 1.0, 1.0], channels = 1)

        def ShortTone(freq, dur, amp):
            return [Tone(freq, 3.0 / sampleRate, amp).Wave("Sine")]

        def Inserted(freq, dur, amp):
            return [Insert(inserted)]

        shortTone = Patch(body = ShortTone, envelope = envelope).RenderSamples(
            440.0, 6.0 / sampleRate, channels = 1
        )
        insertedSamples = Patch(body = Inserted, envelope = envelope).RenderSamples(
            440.0, 6.0 / sampleRate, channels = 1
        )

        self.assertEqual(len(shortTone), 3)
        self.assertEqual(len(insertedSamples), 3)

    def test_EnvelopeWithoutBodyReleasesWhenNoteEndsDuringDecay(self):
        sampleRate = Patch.SAMPLE_RATE
        source = Sound(samples = np.ones(20), channels = 1)
        envelope = Envelope(
            2.0 / sampleRate,
            10.0 / sampleRate,
            0.0,
            3.0 / sampleRate,
            attackCurve = 0.0,
            decayCurve = 0.0,
            releaseCurve = 0.0
        )

        def Body(freq, dur, amp):
            return [Insert(source)]

        patch = Patch(body = Body, envelope = envelope)
        samples = patch.RenderSamples(
            440.0, 6.0 / sampleRate, 1.0, channels = 1
        )

        self.assertEqual(len(samples), 9)
        np.testing.assert_allclose(
            samples,
            np.array([
                0.0,
                1.0,
                1.0,
                8.0 / 9.0,
                7.0 / 9.0,
                6.0 / 9.0,
                6.0 / 9.0,
                3.0 / 9.0,
                0.0,
            ]),
            atol = 1e-12
        )

    def test_EnvelopeReleasesFromAnInterruptedTransientLevel(self):
        sampleRate = Patch.SAMPLE_RATE
        source = Sound(samples = np.ones(20), channels = 1)

        def Body(freq, dur, amp):
            return [Insert(source)]

        patch = Patch(
            body = Body,
            envelope = Envelope(
                10.0 / sampleRate,
                0.0,
                1.0,
                3.0 / sampleRate,
                attackCurve = 0.0,
                releaseCurve = 0.0
            )
        )
        samples = patch.RenderSamples(
            440.0, 4.0 / sampleRate, channels = 1
        )

        np.testing.assert_allclose(samples, [
            0.0, 1.0 / 9.0, 2.0 / 9.0, 3.0 / 9.0,
            3.0 / 9.0, 1.5 / 9.0, 0.0,
        ], atol = 1e-12)

    def test_EnvelopeExtensionDoesNotStretchToneBendOrFade(self):
        sampleRate = Patch.SAMPLE_RATE
        frequencies = []

        def CaptureFrequency(time, frequency):
            frequencies.append(frequency)
            return 1.0

        def Body(freq, dur, amp):
            return [
                Tone(freq, dur, amp).Wave(CaptureFrequency).Bend(880.0).Fade(0.5)
            ]

        patch = Patch(
            body = Body,
            envelope = Envelope(
                0.0, 0.0, 1.0, 5.0 / sampleRate,
                releaseCurve = 0.0
            )
        )
        samples = patch.RenderSamples(
            440.0, 10.0 / sampleRate, channels = 1
        )

        self.assertEqual(len(samples), 15)
        self.assertEqual(len(frequencies), 15)
        self.assertAlmostEqual(frequencies[9], 880.0)
        np.testing.assert_allclose(frequencies[10:], 880.0, atol = 1e-12)
        self.assertAlmostEqual(samples[10], 0.5)
        self.assertAlmostEqual(samples[11], 0.375)

    def test_EnvelopeExtensionUsesExactStereoFrameCount(self):
        sampleRate = Patch.SAMPLE_RATE

        def Body(freq, dur, amp):
            return [Tone(freq, dur, amp).Wave("Sine")]

        patch = Patch(
            body = Body,
            envelope = Envelope(0.05, 0.3, 0.5, 0.5)
        )
        gateFrames = 4134
        releaseFrames = int(0.5 * sampleRate)
        samples = patch.RenderSamples(
            440.0, gateFrames / sampleRate, channels = 2
        )

        self.assertEqual(len(samples), (gateFrames + releaseFrames) * 2)

    def test_MonophonicEnvelopeRetriggerControlsContiguousNotes(self):
        sampleRate = Patch.SAMPLE_RATE
        inserted = Sound(samples = np.ones(4), channels = 1)

        def Body(freq, dur, amp):
            return [Insert(inserted)]

        def Render(retrigger):
            patch = Patch(
                body = Body,
                polyphonic = False,
                envelope = Envelope(
                    4.0 / sampleRate, 0.0, 1.0, 0.0,
                    retrigger = retrigger,
                    attackCurve = 0.0
                )
            )
            noteDuration = 4.0 / sampleRate / 4.0
            return Sequence([
                Tempo(60),
                Meter(4, 4),
                SetPatch(patch),
                Note(0, 0.0, 440.0, noteDuration),
                Note(0, 4.0 / sampleRate, 660.0, noteDuration),
            ]).RenderSamples(channels = 1)

        retriggered = Render(True)
        legato = Render(False)

        self.assertEqual(retriggered[4], 0.0)
        self.assertEqual(legato[4], 1.0)

    def test_NoteScopedControlsDoNotRetriggerLegatoEnvelope(self):
        sampleRate = Patch.SAMPLE_RATE

        def Constant(time, frequency):
            return 1.0

        def Body(freq, dur, amp):
            return [Tone(freq, dur, amp).Wave(Constant)]

        patch = Patch(
            body = Body,
            polyphonic = False,
            envelope = Envelope(
                8.0 / sampleRate, 0.0, 1.0, 0.0,
                retrigger = False,
                attackCurve = 0.0
            )
        )
        duration = Fraction(4, 4 * sampleRate)
        nextBeat = Fraction(4, sampleRate)

        def Render(firstNote):
            return Sequence([
                Tempo(60),
                SetPatch(patch),
                firstNote,
                Note(0, nextBeat, 100.0, duration),
            ]).RenderSamples(channels = 1)

        baseline = Render(Note(0, 0, 100.0, duration))
        controlledNotes = (
            Note(0, 0, 100.0, duration).FadeIn(duration * 0.5),
            Note(0, 0, 100.0, duration).FadeOut(duration * 0.5),
            Note(0, 0, 100.0, duration).BendIn(0.5, duration * 0.5),
            Note(0, 0, 100.0, duration).BendOut(2.0, duration * 0.5),
        )
        for firstNote in controlledNotes:
            with self.subTest(control = firstNote):
                samples = Render(firstNote)
                self.assertGreater(samples[4], 0.0)
                self.assertEqual(samples[4], baseline[4])

    def test_IncompatibleMonophonicLayerRetriggersLegatoEnvelope(self):
        sampleRate = Patch.SAMPLE_RATE
        inserted = Sound(samples = np.ones(4), channels = 1)

        def Body(freq, dur, amp):
            return [
                Insert(inserted),
                Tone(freq, dur, amp).Wave("Sine"),
            ]

        patch = Patch(
            body = Body,
            polyphonic = False,
            envelope = Envelope(
                4.0 / sampleRate, 0.0, 1.0, 0.0,
                retrigger = False,
                attackCurve = 0.0
            )
        )
        noteDuration = 4.0 / sampleRate / 4.0
        samples = Sequence([
            Tempo(60),
            Meter(4, 4),
            SetPatch(patch),
            Note(0, 0.0, 440.0, noteDuration, 1.0),
            Note(0, 4.0 / sampleRate, 660.0, noteDuration, 0.5),
        ]).RenderSamples(channels = 1)

        self.assertEqual(samples[4], 0.0)

    def test_MonophonicEnvelopeReleaseOverlapsFollowingNote(self):
        sampleRate = Patch.SAMPLE_RATE

        def Body(freq, dur, amp):
            return [Tone(freq, dur, amp).Wave("Sine")]

        patch = Patch(
            body = Body,
            polyphonic = False,
            envelope = Envelope(
                0.0, 0.0, 1.0, 3.0 / sampleRate,
                releaseCurve = 0.0
            )
        )
        noteDuration = 4.0 / sampleRate / 4.0
        samples = Sequence([
            Tempo(60),
            Meter(4, 4),
            SetPatch(patch),
            Note(0, 0.0, 440.0, noteDuration),
            Note(0, 4.0 / sampleRate, 660.0, noteDuration),
        ]).RenderSamples(channels = 1)

        self.assertEqual(len(samples), 11)
        self.assertNotEqual(samples[4], 0.0)

    def test_PatchRoutesNoteValues(self):
        received = []

        def Body(freq, dur, amp):
            received.append((freq, dur, amp))
            return [Tone(freq, dur, amp).Wave("Sine")]

        patch = Patch(body = Body)
        samples = patch.RenderSamples(440.0, 0.01, 0.4, channels = 1)
        expected = ChirpSynth(channels = 1).RenderSamples([
            Seconds(),
            Tone(440.0, 0.01, 0.4).Wave("Sine"),
        ])

        self.assertEqual(received, [(440.0, 0.01, 0.4)])
        np.testing.assert_array_equal(samples, expected)

    def test_TransientAndBodyLayersRenderSimultaneously(self):
        def Transient(freq, dur, amp):
            return [Tone(freq, dur, amp).Wave("Sine")]

        def Body(freq, dur, amp):
            return [Tone(freq, dur, amp).Wave("Sine")]

        patchSamples = Patch(Transient, Body).RenderSamples(220.0, 0.01, 0.3, channels = 1)
        toneSamples = ChirpSynth(channels = 1).RenderSamples([
            Seconds(),
            Tone(220.0, 0.01, 0.3).Wave("Sine"),
        ])

        self.assertEqual(len(patchSamples), len(toneSamples))
        np.testing.assert_array_equal(patchSamples, toneSamples * 2.0)

    def test_PatchConstructorBalancesTransientAndBody(self):
        transient = Sound(samples = [1.0], channels = 1)
        body = Sound(samples = [2.0], channels = 1)

        def Transient(freq, dur, amp):
            return [Insert(transient)]

        def Body(freq, dur, amp):
            return [Insert(body)]

        patch = Patch(Transient, Body, transientGain = 0.5, bodyGain = 2.0)
        samples = patch.RenderSamples(440.0, 0.01, channels = 1)
        overridden = patch.RenderSamples(
            440.0, 0.01, channels = 1,
            transientGain = 2.0, bodyGain = 0.25
        )

        np.testing.assert_array_equal(samples, [4.5])
        np.testing.assert_array_equal(overridden, [2.5])

    def test_PatchGainsMustBeFiniteNumbers(self):
        with self.assertRaises(TypeError):
            Patch(transientGain = True)
        with self.assertRaises(ValueError):
            Patch(bodyGain = float("inf"))

    def test_PatchDefaultsAndModesRequireBooleans(self):
        self.assertTrue(Patch().polyphonic)
        self.assertFalse(Patch().portamento)
        self.assertFalse(Patch(polyphonic = False).polyphonic)
        self.assertTrue(Patch(portamento = True).portamento)
        with self.assertRaises(TypeError):
            Patch(polyphonic = 1)
        with self.assertRaises(TypeError):
            Patch(portamento = 1)

    def test_ExplicitToneValuesIgnoreIncomingNoteValues(self):
        def Body(freq, dur, amp):
            return [Tone(880.0, 0.005, 0.25).Wave("TriangleAA")]

        samples = Patch(body = Body).RenderSamples(220.0, 1.0, 0.0, channels = 1)
        expected = ChirpSynth(channels = 1).RenderSamples([
            Seconds(),
            Tone(880.0, 0.005, 0.25).Wave("TriangleAA"),
        ])

        np.testing.assert_array_equal(samples, expected)

    def test_InsertsAreAllowedInBothSectionsAndRemainUnscaled(self):
        inserted = Sound(samples = [0.25, -0.5, 0.75], channels = 1)

        def Transient(freq, dur, amp):
            return [Insert(inserted)]

        def Body(freq, dur, amp):
            return [Insert(inserted.Gain(2.0))]

        samples = Patch(Transient, Body).RenderSamples(440.0, 0.5, 0.0, channels = 1)

        np.testing.assert_array_equal(samples, inserted.samples * 3.0)

    def test_ToneAndNotePanApplyHierarchically(self):
        def Body(freq, dur, amp):
            return [Tone(freq, dur, amp).Wave("Sine").Pan(-0.25).Phase(30.0)]

        patch = Patch(body = Body)
        sequence = Sequence([
            Tempo(120),
            Meter(4, 4),
            SetPatch(patch),
            Note(0, 0, 440.0, L.L64, 0.5).Pan(0.25),
        ])
        samples = sequence.RenderSamples(channels = 2)
        duration = 4.0 * (60.0 / 120.0) * L.L64
        expected = ChirpSynth(channels = 2).RenderSamples([
            Seconds(),
            Tone(440.0, duration, 0.5).Wave("Sine").Pan(-0.25).Phase(30.0),
        ])
        dsp = ChirpDSP(channels = 2)
        expected = dsp.ApplySoundPan(expected, 0.25)

        np.testing.assert_array_equal(samples, expected)

    def test_NotePanAppliesToInsertedSounds(self):
        inserted = Sound(samples = [0.25, 0.75, -0.5, 0.5], channels = 2)

        def Body(freq, dur, amp):
            return [Insert(inserted)]

        sequence = Sequence([
            SetPatch(Patch(body = Body)),
            Note(0, 0, N.C4, L.L4).Pan(-0.75),
        ])
        samples = sequence.RenderSamples(channels = 2)
        dsp = ChirpDSP(channels = 2)
        expected = dsp.ApplySoundPan(inserted.samples, -0.75)

        np.testing.assert_array_equal(samples, expected)

    def test_NoteFadeMultipliesAnExistingToneFade(self):
        def Body(freq, dur, amp):
            return [Tone(freq, dur, amp).Wave("Sine").Fade(amp * 0.5, "inSine")]

        patch = Patch(body = Body)
        sequence = Sequence([
            Tempo(120),
            SetPatch(patch),
            Note(0, 0, 440.0, L.L64, 0.8).Fade(0.2, "outSine"),
        ])
        samples = sequence.RenderSamples(channels = 1)
        duration = 4.0 * (60.0 / 120.0) * L.L64
        toneSamples = ChirpSynth(channels = 1).RenderSamples([
            Seconds(),
            Tone(440.0, duration, 0.8).Wave("Sine").Fade(0.4, "inSine"),
        ])
        dsp = ChirpDSP(channels = 1)
        progress = dsp.GetEasingValues(len(toneSamples), "outSine")
        expected = toneSamples * (1.0 + (((0.2 / 0.8) - 1.0) * progress))

        np.testing.assert_array_equal(samples, expected)

    def test_ToneScopedFadesMultiplyAndClampToItsDuration(self):
        def Constant(time, frequency):
            return 1.0

        synthesizer = ChirpSynth(channels = 1)
        tone = (
            Tone(100.0, 7.0 / synthesizer.SAMPLE_RATE)
            .Wave(Constant)
            .FadeIn(5.0 / synthesizer.SAMPLE_RATE)
            .FadeOut(5.0 / synthesizer.SAMPLE_RATE)
        )
        plan = synthesizer.CompileSequence([Seconds(), tone])
        plan.events[0].fadeFrames = 0
        samples = synthesizer.RenderPlan(plan)

        fadeIn = np.array([0.0, 0.25, 0.5, 0.75, 1.0, 1.0, 1.0])
        fadeOut = np.array([1.0, 1.0, 1.0, 0.75, 0.5, 0.25, 0.0])
        np.testing.assert_allclose(samples, fadeIn * fadeOut, atol = 1e-12)

        clamped = Tone(100.0).FadeIn(-1.0).FadeOut(-2.0)
        self.assertEqual(clamped.fadeInDuration, 0.0)
        self.assertEqual(clamped.fadeOutDuration, 0.0)

        timedPlan = synthesizer.CompileSequence([
            Tempo(60),
            Tone(100.0, Fraction(8, 4 * synthesizer.SAMPLE_RATE))
            .FadeIn(Fraction(4, 4 * synthesizer.SAMPLE_RATE))
            .BendOut(200.0, Fraction(2, 4 * synthesizer.SAMPLE_RATE)),
        ])
        timedEvent = timedPlan.events[0]
        self.assertAlmostEqual(timedEvent.duration, 8.0 / synthesizer.SAMPLE_RATE)
        self.assertAlmostEqual(
            timedEvent.fadeInDuration, 4.0 / synthesizer.SAMPLE_RATE
        )
        self.assertAlmostEqual(
            timedEvent.bendOutDuration, 2.0 / synthesizer.SAMPLE_RATE
        )

    def test_NoteScopedFadesShapeCompletePatchOutputAndReleaseTail(self):
        inserted = Sound(samples = np.ones(9), channels = 1)

        def Body(freq, dur, amp):
            return [Insert(inserted)]

        sampleRate = Sequence.SAMPLE_RATE
        duration = Fraction(7, 4 * sampleRate)
        fade = Fraction(3, 4 * sampleRate)
        samples = Sequence([
            Tempo(60),
            SetPatch(Patch(body = Body)),
            Note(0, 0, 100.0, duration).FadeIn(fade).FadeOut(fade),
        ]).RenderSamples(channels = 1)

        np.testing.assert_allclose(
            samples, [0.0, 0.5, 1.0, 1.0, 1.0, 0.5, 0.0, 0.0, 0.0],
            atol = 1e-12
        )

    def test_NoteFadeCanRiseFromSilence(self):
        def Body(freq, dur, amp):
            return [Tone(freq, dur, amp).Wave("Sine")]

        duration = 4.0 * (60.0 / 120.0) * L.L64
        sequence = Sequence([
            Tempo(120),
            SetPatch(Patch(body = Body)),
            Note(0, 0, 440.0, L.L64, 0.0).Fade(1.0),
        ])
        samples = sequence.RenderSamples(channels = 1)
        target = ChirpSynth(channels = 1).RenderSamples([
            Seconds(),
            Tone(440.0, duration, 1.0).Wave("Sine"),
        ])
        progress = ChirpDSP(channels = 1).GetEasingValues(len(target))

        np.testing.assert_array_equal(samples, target * progress)
        self.assertEqual(samples[0], 0.0)

    def test_NoteAndToneVibratoCompoundInCents(self):
        def Body(freq, dur, amp):
            return [Tone(freq, dur, amp).Wave("Sine").Vibrato(30.0, 5.0, "Sine")]

        duration = 4.0 * (60.0 / 120.0) * L.L64
        samples = Sequence([
            Tempo(120),
            SetPatch(Patch(body = Body)),
            Note(0, 0, 440.0, L.L64).Vibrato(20.0, 5.0, "Sine"),
        ]).RenderSamples(channels = 1)
        expected = ChirpSynth(channels = 1).RenderSamples([
            Seconds(),
            Tone(440.0, duration).Wave("Sine").Vibrato(50.0, 5.0, "Sine"),
        ])

        np.testing.assert_allclose(samples, expected, rtol = 0.0, atol = 1e-12)

    def test_DynamicInsertedSoundsInheritNotePitchPerformance(self):
        def Direct(freq, dur, amp):
            return [Tone(freq, dur, amp).Wave("Sine")]

        def Inserted(freq, dur, amp):
            sound = Sound([
                Seconds(),
                Tone(freq, dur, amp).Wave("Sine"),
            ], channels = 1)
            return [Insert(sound)]

        note = Note(0, 0, 440.0, L.L64).Bend(660.0).Vibrato(20.0, 5.0)
        direct = Sequence([
            SetPatch(Patch(body = Direct)),
            note,
        ]).RenderSamples(channels = 1)
        inserted = Sequence([
            SetPatch(Patch(body = Inserted)),
            Note(0, 0, 440.0, L.L64).Bend(660.0).Vibrato(20.0, 5.0),
        ]).RenderSamples(channels = 1)

        np.testing.assert_array_equal(inserted, direct)

    def test_NoteTremoloAppliesToCompletePatchOutput(self):
        inserted = Sound(samples = [1.0, 1.0, 1.0], channels = 1)

        def Body(freq, dur, amp):
            return [Insert(inserted)]

        samples = Sequence([
            SetPatch(Patch(body = Body)),
            Note(0, 0, N.C4, L.L4).Tremolo(1.0, 0.0, "Sine"),
        ]).RenderSamples(channels = 1)

        np.testing.assert_array_equal(samples, [1.0, 1.0, 1.0])

    def test_NoteAndToneTremoloMultiply(self):
        def Body(freq, dur, amp):
            return [Tone(freq, dur, amp).Wave("Sine").Tremolo(0.25, 0.0, "Sine")]

        duration = 4.0 * (60.0 / 120.0) * L.L64
        samples = Sequence([
            Tempo(120),
            SetPatch(Patch(body = Body)),
            Note(0, 0, 440.0, L.L64).Tremolo(0.5, 0.0, "Sine"),
        ]).RenderSamples(channels = 1)
        expected = ChirpSynth(channels = 1).RenderSamples([
            Seconds(),
            Tone(440.0, duration).Wave("Sine").Tremolo(0.25, 0.0, "Sine"),
        ])

        np.testing.assert_array_equal(samples, expected)

    def test_NoteFadeAppliesToAllPatchLayers(self):
        inserted = Sound(samples = [0.5, 0.25, -0.5], channels = 1)

        def Body(freq, dur, amp):
            return [
                Tone(freq, dur, 0.25).Wave("Sine"),
                Insert(inserted),
            ]

        duration = 3.0 / (4.0 * 44100.0)
        patch = Patch(body = Body)
        faded = Sequence([
            Tempo(60),
            SetPatch(patch),
            Note(0, 0, 440.0, duration, 0.0).Fade(1.0),
        ]).RenderSamples(channels = 1)
        unchanged = patch.RenderSamples(440.0, 3.0 / 44100.0, 1.0, channels = 1)

        np.testing.assert_array_equal(faded, unchanged * [0.0, 0.5, 1.0])

    def test_NoteFadeControlsAnInsertWhoseGainUsesAmplitude(self):
        inserted = Sound(samples = [1.0, 1.0, 1.0], channels = 1)

        def Body(freq, dur, amp):
            return [Insert(inserted.Gain(amp))]

        duration = 3.0 / (4.0 * 44100.0)
        samples = Sequence([
            Tempo(60),
            SetPatch(Patch(body = Body)),
            Note(0, 0, 440.0, duration, 0.0).Fade(1.0),
        ]).RenderSamples(channels = 1)

        np.testing.assert_array_equal(samples, [0.0, 0.5, 1.0])

    def test_NoteFadeAppliesToUnchangedInsertedSounds(self):
        inserted = Sound(samples = [0.25, 0.5, 0.75], channels = 1)

        def Body(freq, dur, amp):
            return [Insert(inserted)]

        duration = 3.0 / (4.0 * 44100.0)
        samples = Sequence([
            Tempo(60),
            SetPatch(Patch(body = Body)),
            Note(0, 0, N.C4, duration, 0.0).Fade(1.0),
        ]).RenderSamples(channels = 1)

        np.testing.assert_array_equal(samples, inserted.samples * [0.0, 0.5, 1.0])

    def test_PatchRenderingDoesNotMutateReturnedToneObjects(self):
        template = Tone(440.0, 0.01, 0.5).Wave("Sine").Pan(-0.25).Phase(30.0)

        def Body(freq, dur, amp):
            return [template]

        patch = Patch(body = Body)
        patch.RenderSamples(440.0, 0.01, channels = 2)

        self.assertEqual(template.pan, -0.25)
        self.assertEqual(template.phaseDegrees, 30.0)
        self.assertFalse(hasattr(patch, "Pan"))
        self.assertFalse(hasattr(patch, "Phase"))

    def test_EmptyPatchProducesAnEmptySound(self):
        sound = Patch().Render(440.0, 1.0, channels = 1)

        self.assertEqual(sound.duration, 0.0)
        self.assertEqual(len(sound.samples), 0)

    def test_PatchRecipesMustBeCallableAndReturnIterables(self):
        with self.assertRaises(TypeError):
            Patch(transient = [])

        def InvalidRecipe(freq, dur, amp):
            return None

        with self.assertRaises(ValueError):
            Patch(body = InvalidRecipe).RenderSamples(440.0, 1.0)

    def test_PatchSubclassUsesTransientAndBodyMethods(self):
        class LayeredPatch(Patch):
            def Transient(self, freq, dur, amp):
                return [Tone(freq, dur, amp).Wave("Sine")]

            def Body(self, freq, dur, amp):
                return [Tone(freq, dur, amp).Wave("Sine")]

        samples = LayeredPatch().RenderSamples(440.0, 0.01, 0.25, channels = 1)
        expected = ChirpSynth(channels = 1).RenderSamples([
            Seconds(),
            Tone(440.0, 0.01, 0.25).Wave("Sine"),
        ])

        np.testing.assert_array_equal(samples, expected * 2.0)

    def test_PatchRecipesRejectWaveControl(self):
        def Body(freq, dur, amp):
            return [Wave("Sine"), Tone(freq, dur, amp)]

        with self.assertRaises(ValueError):
            Patch(body = Body).RenderSamples(440.0, 0.01)

    def test_PatchToneWithoutWaveUsesSine(self):
        def Body(freq, dur, amp):
            return [Tone(freq, dur, amp)]

        samples = Patch(body = Body).RenderSamples(440.0, 0.01, 0.5, channels = 1)
        expected = ChirpSynth(channels = 1).RenderSamples([
            Seconds(),
            Tone(440.0, 0.01, 0.5).Wave("Sine"),
        ])

        np.testing.assert_array_equal(samples, expected)

    def test_PatchRecipesRetainNonWaveSoundControls(self):
        def Body(freq, dur, amp):
            return [Pitch(2.0), Tone(freq, dur, amp).Wave("Sine")]

        samples = Patch(body = Body).RenderSamples(220.0, 0.01, 0.5, channels = 1)
        expected = ChirpSynth(channels = 1).RenderSamples([
            Seconds(),
            Tone(440.0, 0.01, 0.5).Wave("Sine"),
        ])

        np.testing.assert_array_equal(samples, expected)


class SequenceTests(unittest.TestCase):
    def MakeInsertPatch(self, value = 1.0):
        click = Sound(samples = [value], channels = 1)

        def Body(freq, dur, amp):
            return [Insert(click)]

        return Patch(body = Body)

    def test_SequenceDefaultsToSuperSine(self):
        implicit = Sequence([
            Note(0, 0, N.C4, L.L64, 0.25),
        ]).RenderSamples(channels = 1)
        explicit = Sequence([
            SetPatch(Patches.SuperSine),
            Note(0, 0, N.C4, L.L64, 0.25),
        ]).RenderSamples(channels = 1)

        np.testing.assert_array_equal(implicit, explicit)

    def test_BeatOverflowIsIgnoredInsteadOfAdvancingBars(self):
        patch = self.MakeInsertPatch()
        sequence = Sequence([
            Tempo(60),
            Meter(4, 4),
            SetPatch(patch),
            Note(0, 7, N.C4, L.L4),
            Note(1, 3, N.C4, L.L4),
        ])

        with warnings.catch_warnings(record = True) as caught:
            warnings.simplefilter("always")
            samples = sequence.RenderSamples(channels = 1)

        self.assertEqual(len(samples), (7 * 44100) + 1)
        self.assertEqual(samples[7 * 44100], 1.0)
        self.assertEqual(np.count_nonzero(samples), 1)
        self.assertEqual(len(caught), 1)
        self.assertIs(caught[0].category, UserWarning)

    def test_DecimalPositionsResolveAndNegativePositionsAreIgnored(self):
        patch = self.MakeInsertPatch()
        sequence = Sequence([
            Tempo(60),
            Meter(4, 4),
            SetPatch(patch),
            Note(-2, -1.5, N.C4, L.L4),
            Note(0, 0.5, N.C4, L.L4),
        ])

        with warnings.catch_warnings(record = True):
            warnings.simplefilter("always")
            samples = sequence.RenderSamples(channels = 1)

        self.assertEqual(samples[0], 0.0)
        self.assertEqual(samples[22050], 1.0)
        self.assertEqual(np.count_nonzero(samples), 1)

    def test_MeterDenominatorDefinesTheBeatUnit(self):
        patch = self.MakeInsertPatch()
        sequence = Sequence([
            Tempo(60),
            Meter(6, 8),
            SetPatch(patch),
            Note(0, 1, N.C4, L.L4),
        ])

        samples = sequence.RenderSamples(channels = 1)

        self.assertEqual(len(samples), 22051)
        self.assertEqual(samples[22050], 1.0)

    def test_DurationIsResolvedToSecondsBeforePatchRendering(self):
        receivedDurations = []

        def Body(freq, dur, amp):
            receivedDurations.append(dur)
            return []

        sequence = Sequence([
            Tempo(120),
            Meter(4, 4),
            SetPatch(Patch(body = Body)),
            Note(0, 0, N.C4, L.L4),
        ])
        sequence.RenderSamples(channels = 1)

        self.assertEqual(receivedDurations, [0.5])

    def test_SetPatchInheritsAndOverridesPortamento(self):
        patch = Patch(polyphonic = False, portamento = True)

        self.assertTrue(SetPatch(patch).portamento)
        self.assertFalse(SetPatch(patch, portamento = False).portamento)
        with self.assertRaises(TypeError):
            SetPatch(patch, portamento = 1)

    def test_MonophonicPortamentoUsesNoteOverlapAndLogarithmicPitch(self):
        sampleRate = Sequence.SAMPLE_RATE
        frequencies = []

        def CaptureFrequency(time, frequency):
            frequencies.append(frequency)
            return 0.0

        def Body(freq, dur, amp):
            return [Tone(freq, dur, amp).Wave(CaptureFrequency)]

        sequence = Sequence([
            Tempo(60),
            Meter(4, 4),
            SetPatch(Patch(
                body = Body, polyphonic = False, portamento = True
            )),
            Note(0, 0, 100.0, Fraction(5, 4 * sampleRate)),
            Note(
                0, Fraction(2, sampleRate), 200.0,
                Fraction(4, 4 * sampleRate)
            ),
        ])

        scheduled = sequence.ScheduleNotes()
        self.assertEqual(
            [round(item.duration * sampleRate) for item in scheduled],
            [2, 4]
        )
        self.assertEqual(scheduled[1].portamentoStart, 100.0)
        self.assertEqual(
            round(scheduled[1].portamentoDuration * sampleRate), 3
        )

        sequence.RenderSamples(channels = 1)
        np.testing.assert_allclose(
            frequencies,
            [100.0, 100.0, 100.0, math.sqrt(20000.0), 200.0, 200.0],
            rtol = 0.0,
            atol = 1e-10
        )

    def test_PortamentoStartsAtTheFinalQuantizedStepBendFrequency(self):
        sampleRate = Sequence.SAMPLE_RATE
        sequence = Sequence([
            Tempo(60),
            SetPatch(Patch(polyphonic = False, portamento = True)),
            Note(0, 0, 100.0, Fraction(4, 4 * sampleRate)).StepBend(
                175.0, [1.0, 1.5]
            ),
            Note(
                0, Fraction(2, sampleRate), 200.0,
                Fraction(4, 4 * sampleRate)
            ),
        ])

        scheduled = sequence.ScheduleNotes()

        self.assertEqual(scheduled[1].portamentoStart, 150.0)

    def test_PortamentoStartsAtTheOutgoingScopedBendFrequency(self):
        sampleRate = Sequence.SAMPLE_RATE
        sequence = Sequence([
            Tempo(60),
            SetPatch(Patch(polyphonic = False, portamento = True)),
            Note(0, 0, 100.0, Fraction(5, 4 * sampleRate)).BendOut(
                200.0, Fraction(5, 4 * sampleRate)
            ),
            Note(
                0, Fraction(2, sampleRate), 300.0,
                Fraction(4, 4 * sampleRate)
            ),
        ])

        scheduled = sequence.ScheduleNotes()

        self.assertEqual(scheduled[1].portamentoStart, 150.0)
        self.assertEqual(
            round(scheduled[1].portamentoDuration * sampleRate), 3
        )

    def test_PortamentoRequiresOverlapAndMonophony(self):
        sampleRate = Sequence.SAMPLE_RATE
        patch = Patch(polyphonic = False, portamento = True)

        touching = Sequence([
            Tempo(60),
            SetPatch(patch),
            Note(0, 0, 100.0, Fraction(2, 4 * sampleRate)),
            Note(0, Fraction(2, sampleRate), 200.0, L.L4),
        ]).ScheduleNotes()
        disabled = Sequence([
            Tempo(60),
            SetPatch(patch, portamento = False),
            Note(0, 0, 100.0, Fraction(3, 4 * sampleRate)),
            Note(0, Fraction(2, sampleRate), 200.0, L.L4),
        ]).ScheduleNotes()
        polyphonic = Sequence([
            Tempo(60),
            SetPatch(patch, polyphonic = True),
            Note(0, 0, 100.0, Fraction(3, 4 * sampleRate)),
            Note(0, Fraction(2, sampleRate), 200.0, L.L4),
        ]).ScheduleNotes()

        self.assertIsNone(touching[1].portamentoStart)
        self.assertIsNone(disabled[1].portamentoStart)
        self.assertTrue(all(item.portamentoStart is None for item in polyphonic))

    def test_AcceleratedPortamentoMatchesPythonRendering(self):
        if not ChirpKernels.NUMBA_AVAILABLE:
            self.skipTest("Numba is unavailable")

        sampleRate = Sequence.SAMPLE_RATE

        def Body(freq, dur, amp):
            return [Tone(freq, dur, amp).Wave("Sine")]

        sequence = Sequence([
            Tempo(60),
            SetPatch(Patch(
                body = Body, polyphonic = False, portamento = True
            )),
            Note(0, 0, 100.0, Fraction(20, 4 * sampleRate)),
            Note(
                0, Fraction(10, sampleRate), 200.0,
                Fraction(20, 4 * sampleRate)
            ),
        ])

        enabled = ChirpKernels.NUMBA_ENABLED
        try:
            ChirpKernels.NUMBA_ENABLED = True
            accelerated = sequence.RenderSamples(channels = 1)
            ChirpKernels.NUMBA_ENABLED = False
            python = sequence.RenderSamples(channels = 1)
        finally:
            ChirpKernels.NUMBA_ENABLED = enabled

        np.testing.assert_allclose(accelerated, python, rtol = 0.0, atol = 1e-12)

    def test_MonophonicPatchShortensOnlyTheIncomingDuration(self):
        monophonicDurations = []
        polyphonicDurations = []

        def MonophonicBody(freq, dur, amp):
            monophonicDurations.append(dur)
            return []

        def PolyphonicBody(freq, dur, amp):
            polyphonicDurations.append(dur)
            return []

        Sequence([
            Tempo(60),
            SetPatch(Patch(body = MonophonicBody, polyphonic = False)),
            Note(0, 0, N.C4, L.L2),
            Note(0, 1, N.E4, L.L4),
        ]).RenderSamples(channels = 1)
        Sequence([
            Tempo(60),
            SetPatch(Patch(body = PolyphonicBody)),
            Note(0, 0, N.C4, L.L2),
            Note(0, 1, N.E4, L.L4),
        ]).RenderSamples(channels = 1)

        self.assertEqual(monophonicDurations, [1.0, 1.0])
        self.assertEqual(polyphonicDurations, [2.0, 1.0])

    def test_MonophonicPatchUsesTheLowestSimultaneousFrequency(self):
        receivedFrequencies = []

        def Body(freq, dur, amp):
            receivedFrequencies.append(float(freq))
            return []

        Sequence([
            SetPatch(Patch(body = Body, polyphonic = False)),
            Note(0, 0, N.G4, L.L4),
            Note(0, 0, N.C4, L.L4),
            Note(0, 0, N.E4, L.L4),
        ]).RenderSamples(channels = 1)

        self.assertEqual(receivedFrequencies, [N.C4])

    def test_MonophonicPatchKeepsTheFirstEqualFrequency(self):
        receivedAmplitudes = []

        def Body(freq, dur, amp):
            receivedAmplitudes.append(amp)
            return []

        Sequence([
            SetPatch(Patch(body = Body, polyphonic = False)),
            Note(0, 0, N.C4, L.L4, 0.25),
            Note(0, 0, N.C4, L.L4, 0.75),
        ]).RenderSamples(channels = 1)

        self.assertEqual(receivedAmplitudes, [0.25])

    def test_MonophonicPatchDoesNotCutExplicitLayers(self):
        inserted = Sound(samples = [1.0, 1.0, 1.0, 1.0], channels = 1)

        def Body(freq, dur, amp):
            return [
                Tone(1.0, 4.0 / 44100.0, 1.0).Wave("Pulse50"),
                Insert(inserted),
            ]

        samples = Sequence([
            Tempo(60),
            SetPatch(Patch(body = Body, polyphonic = False)),
            Note(0, 0, N.C4, L.L4),
            Note(0, 2.0 / 44100.0, N.E4, L.L4),
        ]).RenderSamples(channels = 1)

        self.assertEqual(len(samples), 6)
        self.assertGreater(samples[2], 1.0)
        self.assertGreater(samples[3], 1.0)

    def test_MonophonicBendHandoffPreservesOscillatorPhase(self):
        def Body(freq, dur, amp):
            return [Tone(freq, dur, amp).Wave("Sine")]

        samples = Sequence([
            Tempo(60),
            Meter(4, 4),
            SetPatch(Patch(body = Body, polyphonic = False)),
            Note(0, 0, N.G4, L.L4, 0.25).Bend(N.G5, "outSine"),
            Note(0, 1, N.G5, L.L4, 0.25),
        ]).RenderSamples(channels = 1)
        boundary = 44100

        self.assertGreater(abs(samples[boundary - 1]), 0.01)
        self.assertGreater(abs(samples[boundary]), 0.01)
        self.assertLess(abs(samples[boundary] - samples[boundary - 1]), 0.05)

    def test_MonophonicStepBendHandoffPreservesOscillatorPhase(self):
        def Body(freq, dur, amp):
            return [Tone(freq, dur, amp).Wave("Sine")]

        samples = Sequence([
            Tempo(60),
            Meter(4, 4),
            SetPatch(Patch(body = Body, polyphonic = False)),
            Note(0, 0, N.G4, L.L4, 0.25).StepBend(N.G5),
            Note(0, 1, N.G5, L.L4, 0.25),
        ]).RenderSamples(channels = 1)
        boundary = 44100

        self.assertGreater(abs(samples[boundary - 1]), 0.01)
        self.assertGreater(abs(samples[boundary]), 0.01)
        self.assertLess(abs(samples[boundary] - samples[boundary - 1]), 0.05)

    def test_MonophonicFadeIntoMatchingAmplitudePreservesState(self):
        def Body(freq, dur, amp):
            return [Tone(freq, dur, amp).Wave("Sine")]

        samples = Sequence([
            Tempo(60),
            Meter(4, 4),
            SetPatch(Patch(body = Body, polyphonic = False)),
            Note(0, 0, N.G4, L.L4, D.D00).Bend(N.G5, "outSine").Vibrato().Fade(D.D11),
            Note(0, 1, N.G5, L.L4, D.D11).Vibrato(),
        ]).RenderSamples(channels = 1)
        boundary = 44100

        self.assertNotEqual(samples[boundary - 1], 0.0)
        self.assertNotEqual(samples[boundary], 0.0)
        self.assertLess(abs(samples[boundary] - samples[boundary - 1]), 0.05)

    def test_MonophonicFadeIntoDifferentAmplitudeRetainsBoundaryFades(self):
        def Body(freq, dur, amp):
            return [Tone(freq, dur, amp).Wave("Sine")]

        samples = Sequence([
            Tempo(60),
            SetPatch(Patch(body = Body, polyphonic = False)),
            Note(0, 0, N.G4, L.L4, 0.0).Fade(0.2),
            Note(0, 1, N.G4, L.L4, 0.4),
        ]).RenderSamples(channels = 1)
        boundary = 44100

        self.assertEqual(samples[boundary - 1], 0.0)
        self.assertEqual(samples[boundary], 0.0)

    def test_PerformancePhaseContinuationDoesNotAdvanceANewBend(self):
        synthesizer = ChirpSynth(channels = 1)
        arguments = {
            "freq": N.G4,
            "duration": 0.01,
            "wave": synthesizer.oscillator.Sine,
            "performanceBend": N.G5,
            "performanceBendDuration": 0.01,
        }

        initial, _, _, _ = MakeTone(synthesizer, **arguments)
        continued, _, _, _ = MakeTone(
            synthesizer,
            **arguments,
            performanceOffset = 1.0
        )

        np.testing.assert_allclose(initial, continued, rtol = 0.0, atol = 1e-12)

    def test_MonophonicNoteModulationContinuesAcrossCompatibleNotes(self):
        def Body(freq, dur, amp):
            return [Tone(freq, dur, amp).Wave("Sine")]

        patch = Patch(body = Body, polyphonic = False)
        split = Sequence([
            Tempo(60),
            SetPatch(patch),
            Note(0, 0, N.G4, L.L4).Vibrato(20.0, 5.25).Tremolo(0.5, 3.25, "sine"),
            Note(0, 1, N.G4, L.L4).Vibrato(20.0, 5.25).Tremolo(0.5, 3.25, "SINE"),
        ]).RenderSamples(channels = 1)
        continuous = Sequence([
            Tempo(60),
            SetPatch(patch),
            Note(0, 0, N.G4, L.L2).Vibrato(20.0, 5.25).Tremolo(0.5, 3.25, "Sine"),
        ]).RenderSamples(channels = 1)

        np.testing.assert_allclose(split, continuous, rtol = 0.0, atol = 1e-11)

    def test_MonophonicToneModulationContinuesAcrossCompatibleNotes(self):
        def Body(freq, dur, amp):
            return [
                Tone(freq, dur, amp).Wave("Sine")
                .Vibrato(20.0, 5.25)
                .Tremolo(0.5, 3.25)
            ]

        patch = Patch(body = Body, polyphonic = False)
        split = Sequence([
            Tempo(60),
            SetPatch(patch),
            Note(0, 0, N.G4, L.L4),
            Note(0, 1, N.G4, L.L4),
        ]).RenderSamples(channels = 1)
        continuous = Sequence([
            Tempo(60),
            SetPatch(patch),
            Note(0, 0, N.G4, L.L2),
        ]).RenderSamples(channels = 1)

        np.testing.assert_allclose(split, continuous, rtol = 0.0, atol = 1e-11)

    def test_NoteBendModulatesDerivedPatchFrequencies(self):
        def Body(freq, dur, amp):
            return [Tone(freq * 2.0, dur, amp).Wave("Sine")]

        duration = 4.0 * (60.0 / 120.0) * L.L64
        sequence = Sequence([
            Tempo(120),
            SetPatch(Patch(body = Body)),
            Note(0, 0, N.C4, L.L64).Bend(N.G4, "inSine"),
        ])
        samples = sequence.RenderSamples(channels = 1)
        expected = ChirpSynth(channels = 1).RenderSamples([
            Seconds(),
            Tone(N.C4 * 2.0, duration).Wave("Sine").Bend(N.G4 * 2.0, "inSine"),
        ])

        np.testing.assert_allclose(samples, expected, rtol = 0.0, atol = 1e-12)

    def test_ToneBendInAndBendOutUseIndependentWindows(self):
        frequencies = []

        def CaptureFrequency(time, frequency):
            frequencies.append(frequency)
            return 0.0

        sampleRate = ChirpSynth.SAMPLE_RATE
        ChirpSynth(channels = 1).RenderSamples([
            Seconds(),
            Tone(100.0, 7.0 / sampleRate).Wave(CaptureFrequency)
            .BendIn(50.0, 3.0 / sampleRate)
            .BendOut(200.0, 3.0 / sampleRate),
        ])

        np.testing.assert_allclose(
            frequencies, [50.0, 75.0, 100.0, 100.0, 100.0, 150.0, 200.0],
            rtol = 0.0, atol = 1e-12
        )

        frequencies.clear()
        ChirpSynth(channels = 1).RenderSamples([
            Seconds(),
            Tone(100.0, 6.0 / sampleRate).Wave(CaptureFrequency)
            .BendIn(50.0, 4.0 / sampleRate)
            .BendOut(200.0, 4.0 / sampleRate),
        ])
        np.testing.assert_allclose(
            frequencies, [50.0, 75.0, 100.0, 100.0, 150.0, 200.0],
            rtol = 0.0, atol = 1e-12
        )

    def test_OneFrameBendOutReachesItsTarget(self):
        frequencies = []

        def CaptureFrequency(time, frequency):
            frequencies.append(frequency)
            return 0.0

        sampleRate = ChirpSynth.SAMPLE_RATE
        ChirpSynth(channels = 1).RenderSamples([
            Seconds(),
            Tone(440.0, 2.0 / sampleRate).Wave(CaptureFrequency)
            .BendOut(880.0, 1.0 / sampleRate),
        ])

        np.testing.assert_allclose(frequencies, [440.0, 880.0])

    def test_UnisonDetunesToneAndNoteScopedBendTargets(self):
        sampleRate = ChirpSynth.SAMPLE_RATE
        expected = [
            110.0, 220.0, 440.0,
            220.0, 440.0, 880.0,
            440.0, 880.0, 1760.0,
        ]

        toneFrequencies = []

        def CaptureToneFrequency(time, frequency):
            toneFrequencies.append(frequency)
            return 0.0

        ChirpSynth(channels = 1).RenderSamples([
            Seconds(),
            Tone(440.0, 3.0 / sampleRate).Wave(CaptureToneFrequency)
            .BendIn(0.5, 2.0 / sampleRate)
            .BendOut(2.0, 1.0 / sampleRate)
            .Unison(3, 1200.0, 0.0),
        ])
        np.testing.assert_allclose(toneFrequencies, expected, atol = 1e-10)

        noteFrequencies = []

        def CaptureNoteFrequency(time, frequency):
            noteFrequencies.append(frequency)
            return 0.0

        def Body(freq, dur, amp):
            return [
                Tone(freq, dur, amp).Wave(CaptureNoteFrequency)
                .Unison(3, 1200.0, 0.0)
            ]

        Sequence([
            Tempo(60),
            SetPatch(Patch(body = Body)),
            Note(0, 0, 440.0, Fraction(3, 4 * sampleRate))
            .BendIn(0.5, Fraction(2, 4 * sampleRate))
            .BendOut(2.0, Fraction(1, 4 * sampleRate)),
        ]).RenderSamples(channels = 1)
        np.testing.assert_allclose(noteFrequencies, expected, atol = 1e-10)

    def test_NoteScopedBendsFollowTheOriginalArpeggioTimeline(self):
        frequencies = []

        def CaptureFrequency(time, frequency):
            frequencies.append(frequency)
            return 0.0

        def Body(freq, dur, amp):
            return [Tone(freq * 2.0, dur, amp).Wave(CaptureFrequency)]

        sampleRate = Sequence.SAMPLE_RATE
        duration = Fraction(8, 4 * sampleRate)
        window = Fraction(4, 4 * sampleRate)
        step = Fraction(4, 4 * sampleRate)
        Sequence([
            Tempo(60),
            SetPatch(Patch(body = Body)),
            Note(0, 0, 100.0, duration)
            .BendIn(0.5, window)
            .BendOut(2.0, window)
            .Arpeggio([1.5], step),
        ]).RenderSamples(channels = 1)

        np.testing.assert_allclose(
            frequencies,
            [100.0, 100.0 + (100.0 / 3.0), 100.0 + (200.0 / 3.0), 200.0,
             300.0, 400.0, 500.0, 600.0],
            rtol = 0.0, atol = 1e-10
        )

    def test_FullAndScopedBendMethodsReplaceEachOther(self):
        tone = Tone(100.0).BendIn(0.5, 0.1).BendOut(2.0, 0.1)
        self.assertIsNone(tone.bend)
        self.assertEqual(tone.bendInTarget, 0.5)
        self.assertEqual(tone.bendOutTarget, 2.0)

        tone.Bend(200.0)
        self.assertIsNone(tone.bendInTarget)
        self.assertIsNone(tone.bendOutTarget)

        note = Note(0, 0, 100.0, L.L4).Bend(200.0).BendIn(0.5, L.L16)
        self.assertIsNone(note.bend)
        note.BendOut(2.0, L.L16)
        self.assertEqual(note.bendInTarget, 0.5)
        self.assertEqual(note.bendOutTarget, 2.0)

        note.StepBend(200.0)
        self.assertIsNone(note.bendInTarget)
        self.assertIsNone(note.bendOutTarget)

        with self.assertRaises(TypeError):
            Tone(100.0).BendIn(50.0, True)
        with self.assertRaises(ValueError):
            Note(0, 0, 100.0, L.L4).BendOut(200.0, float("inf"))

    def test_ClearedScopedBendDurationsDoNotShortenLaterBends(self):
        tone = Tone(440.0).BendIn(0.5, 0.008).BendOut(2.0, 0.008)
        tone.Bend(2.0)
        self.assertEqual(tone.bendInDuration, 0.0)
        self.assertEqual(tone.bendOutDuration, 0.0)

        note = Note(0, 0, 440.0, L.L4).BendIn(0.5, L.L16).BendOut(
            2.0, L.L16
        )
        note.StepBend(2.0)
        self.assertEqual(note.bendInDuration, 0.0)
        self.assertEqual(note.bendOutDuration, 0.0)

        frequencies = []

        def CaptureFrequency(time, frequency):
            frequencies.append(frequency)
            return 0.0

        sampleRate = ChirpSynth.SAMPLE_RATE
        ChirpSynth(channels = 1).RenderSamples([
            Seconds(),
            Tone(440.0, 10.0 / sampleRate).Wave(CaptureFrequency)
            .BendIn(0.5, 8.0 / sampleRate)
            .Bend(2.0)
            .BendOut(2.0, 8.0 / sampleRate),
        ])
        self.assertEqual(frequencies[2], 440.0)
        self.assertGreater(frequencies[3], 440.0)

    def test_NoteTrillAlternatesAbsoluteAndRatioTargets(self):
        for target, targetFrequency in ((150.0, 150.0), (2.0, 200.0), (20.0, 20.0)):
            with self.subTest(target = target):
                frequencies = []

                def CaptureFrequency(time, frequency):
                    frequencies.append(frequency)
                    return 0.0

                def Body(freq, dur, amp):
                    return [Tone(freq, dur, amp).Wave(CaptureFrequency)]

                Sequence([
                    Tempo(60),
                    SetPatch(Patch(body = Body)),
                    Note(0, 0, 100.0, Fraction(8, 4 * 44100)).Trill(
                        target, Fraction(2, 4 * 44100)
                    ),
                ]).RenderSamples(channels = 1)

                np.testing.assert_allclose(
                    frequencies,
                    [100.0, 100.0, targetFrequency, targetFrequency] * 2,
                    rtol = 0.0,
                    atol = 1e-12
                )

    def test_NoteTrillFreezesFinalPitchDuringRelease(self):
        frequencies = []

        def CaptureFrequency(time, frequency):
            frequencies.append(frequency)
            return 0.0

        def Body(freq, dur, amp):
            return [Tone(freq, dur, amp).Wave(CaptureFrequency)]

        patch = Patch(
            body = Body,
            envelope = Envelope(0.0, 0.0, 1.0, 4.0 / 44100.0)
        )
        Sequence([
            Tempo(60),
            SetPatch(patch),
            Note(0, 0, 100.0, Fraction(4, 4 * 44100)).Trill(
                2.0, Fraction(3, 4 * 44100)
            ),
        ]).RenderSamples(channels = 1)

        np.testing.assert_allclose(
            frequencies,
            [100.0, 100.0, 100.0, 200.0, 200.0, 200.0, 200.0, 200.0],
            rtol = 0.0,
            atol = 1e-12
        )

    def test_TrillAndBendTargetsResolveForPitchedAndNoiseWaves(self):
        performed = PerformanceFrequency(
            100.0,
            bend = 2.0,
            bendStepped = True,
            trill = 2.0,
            trillLength = 0.01
        )
        synthesizer = ChirpSynth(channels = 1)

        pitched = synthesizer.CompileSequence([
            Seconds(), Tone(performed, 0.01).Wave("Sine")
        ]).events[0]
        noise = synthesizer.CompileSequence([
            Seconds(), Tone(performed, 0.01).Wave("NoiseStep")
        ]).events[0]
        pitchedToneBend = synthesizer.CompileSequence([
            Seconds(), Tone(100.0, 0.01).Wave("Sine").Bend(2.0)
        ]).events[0]
        noiseToneBend = synthesizer.CompileSequence([
            Seconds(), Tone(100.0, 0.01).Wave("NoiseStep").Bend(2.0)
        ]).events[0]

        self.assertEqual(pitched.performanceBend, 200.0)
        self.assertEqual(pitched.performanceTrill, 200.0)
        self.assertEqual(pitchedToneBend.bend, 200.0)
        self.assertEqual(noise.performanceBend, 2.0)
        self.assertIsNone(noise.performanceTrill)
        self.assertEqual(noiseToneBend.bend, 2.0)

    def test_NoteStepBendAcceptsARatioTarget(self):
        frequencies = []

        def CaptureFrequency(time, frequency):
            frequencies.append(frequency)
            return 0.0

        def Body(freq, dur, amp):
            return [Tone(freq, dur, amp).Wave(CaptureFrequency)]

        Sequence([
            Tempo(60),
            SetPatch(Patch(body = Body)),
            Note(0, 0, 100.0, Fraction(13, 4 * 44100)).StepBend(2.0),
        ]).RenderSamples(channels = 1)

        expected = [100.0 * (2.0 ** (semitone / 12.0)) for semitone in range(13)]
        np.testing.assert_allclose(frequencies, expected, rtol = 0.0, atol = 1e-10)

    def test_ChordValidatesCopiesAndReplacesArpeggio(self):
        pattern = [1.5, 1.25, 1.25]
        dynamics = [1.0, 0.5]
        note = Note(0, 0, 100.0, L.L4).Chord(
            pattern, dynamics = dynamics
        )
        pattern.append(2.0)
        dynamics.append(0.25)

        self.assertEqual(note.chord.values, (1.5, 1.25, 1.25))
        self.assertEqual(note.chord.roll, 0.0)
        self.assertEqual(note.chord.dynamics.values, (1.0, 0.5))
        self.assertIsNone(note.arpeggio)

        note.Arpeggio([1.5])
        self.assertIsNone(note.chord)
        self.assertIsNotNone(note.arpeggio)

        note.Chord([1.25])
        self.assertIsNotNone(note.chord)
        self.assertIsNone(note.arpeggio)

        tuplePattern = Note(0, 0, 100.0, L.L4).Chord((1.0, 1.5))
        self.assertEqual(tuplePattern.chord.values, (1.0, 1.5))
        with self.assertRaises(ValueError):
            Note(0, 0, 100.0, L.L4).Chord([1.5, 440.0])
        with self.assertRaises(TypeError):
            Note(0, 0, 100.0, L.L4).Chord([1.5], roll = True)
        with self.assertRaises(TypeError):
            Note(0, 0, 100.0, L.L4).Chord([1.5], roll = "slow")
        with self.assertRaises(ValueError):
            Note(0, 0, 100.0, L.L4).Chord([1.5], roll = float("inf"))
        with self.assertRaises(TypeError):
            Note(0, 0, 100.0, L.L4).Chord([1.5], dynamics = (1.0, 0.5))
        with self.assertRaises(ValueError):
            Note(0, 0, 100.0, L.L4).Chord([1.5], dynamics = [])
        with self.assertRaises(TypeError):
            Note(0, 0, 100.0, L.L4).Chord([1.5], dynamics = [True])
        with self.assertRaises(ValueError):
            Note(0, 0, 100.0, L.L4).Chord([1.5], dynamics = [-0.1])
        with self.assertRaises(ValueError):
            Note(0, 0, 100.0, L.L4).Chord(
                [1.5], dynamics = [float("inf")]
            )

        self.assertEqual(
            Note(0, 0, 100.0, L.L4).Chord([1.5], inversion = None).chord.inversion,
            0
        )
        with self.assertRaises(TypeError):
            Note(0, 0, 100.0, L.L4).Chord([1.5], inversion = True)
        with self.assertRaises(TypeError):
            Note(0, 0, 100.0, L.L4).Chord([1.5], inversion = 1.5)

    def test_ChordInversionRotatesInBothDirectionsAndRetainsOctaveCycles(self):
        expected = {
            -4: [37.5, 50.0, 62.5],
            -3: [50.0, 62.5, 75.0],
            -2: [62.5, 75.0, 100.0],
            -1: [75.0, 100.0, 125.0],
            0: [100.0, 150.0, 125.0],
            1: [125.0, 150.0, 200.0],
            2: [150.0, 200.0, 250.0],
            3: [200.0, 250.0, 300.0],
            4: [250.0, 300.0, 400.0],
        }

        for inversion, frequencies in expected.items():
            with self.subTest(inversion = inversion):
                chord = Note(0, 0, 100.0, L.L4).Chord(
                    [1.5, 1.25], inversion = inversion
                ).chord
                np.testing.assert_allclose(
                    chord.GetFrequencies(100.0), frequencies,
                    rtol = 0.0, atol = 1e-12
                )

        powerChord = Note(0, 0, 100.0, L.L4).Chord(
            ES.POWER, inversion = 1
        ).chord
        np.testing.assert_allclose(
            powerChord.GetFrequencies(100.0),
            [100.0 * ER.FIFTH, 200.0],
            rtol = 0.0, atol = 1e-12
        )

    def test_NoteChordSchedulesSimultaneousRatiosAndFrequencies(self):
        ratioNote = Note(0, 0, 100.0, L.L4, 0.75).Chord([
            1.5, 1.0, 1.25, 1.5
        ]).Pan(-0.5).Fade(0.25)
        frequencyNote = Note(0, 0, 100.0, L.L4).Chord([
            150.0, 100.0, 125.0, 150.0
        ])

        polyphonicPatch = Patch(polyphonic = True)
        ratioNotes = Sequence([
            Tempo(60), SetPatch(polyphonicPatch), ratioNote
        ]).ScheduleNotes()
        frequencyNotes = Sequence([
            Tempo(60), SetPatch(polyphonicPatch), frequencyNote
        ]).ScheduleNotes()
        expectedFrequencies = [100.0, 150.0, 125.0]

        self.assertEqual(
            [item.note.freq for item in ratioNotes], expectedFrequencies
        )
        self.assertEqual(
            [item.note.freq for item in frequencyNotes], expectedFrequencies
        )
        self.assertTrue(all(item.startFrame == 0 for item in ratioNotes))
        self.assertTrue(all(item.duration == 1.0 for item in ratioNotes))
        self.assertTrue(all(item.note.amplitude == 0.75 for item in ratioNotes))
        self.assertTrue(all(item.note.pan == -0.5 for item in ratioNotes))
        self.assertTrue(all(item.note.fadeTarget == 0.25 for item in ratioNotes))
        self.assertTrue(all(item.note.chord is None for item in ratioNotes))

    def test_NoteChordDynamicsFollowPitchAndInterpolatePerceptually(self):
        scheduled = Sequence([
            Tempo(60),
            Note(0, 0, 100.0, L.L4, 0.8).Fade(0.4).Chord(
                [1.5, 0.5, 1.25], roll = -L.L64,
                dynamics = [1.0, 0.25]
            ),
        ]).ScheduleNotes()

        gainStep = 0.25 ** (1.0 / 3.0)
        expectedGains = {
            50.0: 1.0,
            100.0: gainStep,
            125.0: gainStep ** 2.0,
            150.0: 0.25,
        }
        self.assertEqual(
            [item.note.freq for item in scheduled],
            [150.0, 125.0, 100.0, 50.0]
        )
        np.testing.assert_allclose(
            [item.note.amplitude for item in scheduled],
            [0.8 * expectedGains[item.note.freq] for item in scheduled]
        )
        np.testing.assert_allclose(
            [item.note.fadeTarget for item in scheduled],
            [0.4 * expectedGains[item.note.freq] for item in scheduled]
        )

    def test_DynamicsCurvePreservesZeroControlPoints(self):
        note = Note(0, 0, 100.0, L.L4).Chord(
            [1.5], dynamics = [0.0, 1.0]
        )
        bothZero = Note(0, 0, 100.0, L.L4).Chord(
            [1.5], dynamics = [0.0, 0.0]
        )

        np.testing.assert_allclose(
            note.chord.dynamics.GetGains(3),
            [0.0, math.sqrt(D.D01), 1.0]
        )
        self.assertEqual(bothZero.chord.dynamics.GetGains(3), (0.0, 0.0, 0.0))

    def test_NoteChordRespectsMonophonicPatchSelection(self):
        scheduled = Sequence([
            Tempo(60),
            SetPatch(Patch(polyphonic = False)),
            Note(0, 0, 100.0, L.L4).Chord([1.5, 0.5]),
        ]).ScheduleNotes()

        self.assertEqual(len(scheduled), 1)
        self.assertEqual(scheduled[0].note.freq, 50.0)

    def test_NoteChordRollsInBothDirectionsAndKeepsACommonEndpoint(self):
        duration = Fraction(10, 4 * 44100)
        roll = Fraction(2, 4 * 44100)

        ascending = Sequence([
            Tempo(60),
            Note(0, 0, 100.0, duration).Chord(
                [1.5, 0.5, 1.25], roll = roll
            ),
        ]).ScheduleNotes()
        descending = Sequence([
            Tempo(60),
            Note(0, 0, 100.0, duration).Chord(
                [1.5, 0.5, 1.25], roll = -roll
            ),
        ]).ScheduleNotes()

        self.assertEqual(
            [item.note.freq for item in ascending],
            [50.0, 100.0, 125.0, 150.0]
        )
        self.assertEqual(
            [item.note.freq for item in descending],
            [150.0, 125.0, 100.0, 50.0]
        )
        self.assertEqual(
            [item.startFrame for item in ascending], [0, 2, 4, 6]
        )
        self.assertEqual(
            [item.startFrame for item in descending], [0, 2, 4, 6]
        )
        self.assertEqual(
            [round(item.duration * 44100) for item in ascending],
            [10, 8, 6, 4]
        )
        self.assertEqual(
            [item.performanceOffsetFrames for item in ascending],
            [0, 2, 4, 6]
        )
        self.assertTrue(all(
            item.startFrame + round(item.duration * 44100) == 10
            for item in ascending + descending
        ))

        shortened = Sequence([
            Tempo(60),
            Note(0, 0, 100.0, Fraction(3, 4 * 44100)).Chord(
                [1.5, 0.5, 1.25], roll = roll
            ),
        ]).ScheduleNotes()
        self.assertEqual(
            [item.note.freq for item in shortened], [50.0, 100.0]
        )
        self.assertEqual(
            [round(item.duration * 44100) for item in shortened], [3, 1]
        )

    def test_ArpeggioValidatesAndCopiesItsPattern(self):
        pattern = [1.0, 1.5, 1.25, 1.25]
        dynamics = [1.0, 0.5]
        note = Note(0, 0, 100.0, L.L4).Arpeggio(
            pattern, dynamics = dynamics
        )
        tone = Tone(100.0).Arpeggio(pattern, dynamics = dynamics)
        pattern.append(2.0)
        dynamics.append(0.25)

        self.assertEqual(note.arpeggio.values, (1.0, 1.5, 1.25, 1.25))
        self.assertEqual(tone.arpeggio.values, (1.0, 1.5, 1.25, 1.25))
        self.assertEqual(note.arpeggio.dynamics.values, (1.0, 0.5))
        self.assertEqual(tone.arpeggio.dynamics.values, (1.0, 0.5))

        tuplePattern = Note(0, 0, 100.0, L.L4).Arpeggio((1.0, 1.5))
        self.assertEqual(tuplePattern.arpeggio.values, (1.0, 1.5))
        with self.assertRaises(ValueError):
            Tone(100.0).Arpeggio([1.5, 440.0])
        with self.assertRaises(ValueError):
            Note(0, 0, 100.0, L.L4).Arpeggio([1.0], 0.0)
        with self.assertRaises(TypeError):
            Tone(100.0).Arpeggio([1.5], dynamics = (1.0, 0.5))

        self.assertEqual(
            Tone(100.0).Arpeggio([1.5], rotation = None).arpeggio.rotation,
            0
        )
        with self.assertRaises(TypeError):
            Tone(100.0).Arpeggio([1.5], rotation = False)
        with self.assertRaises(TypeError):
            Note(0, 0, 100.0, L.L4).Arpeggio([1.5], rotation = 2.0)

    def test_ArpeggioRotationPreservesFrequenciesAndPatternOrder(self):
        positive = Tone(100.0).Arpeggio(
            [1.5, 1.25], rotation = 1
        ).arpeggio
        negative = Tone(100.0).Arpeggio(
            [150.0, 125.0], rotation = -1
        ).arpeggio
        fullCycle = Note(0, 0, 100.0, L.L4).Arpeggio(
            [1.5, 1.25], rotation = -3
        ).arpeggio

        np.testing.assert_allclose(
            positive.GetFrequencies(100.0), [150.0, 125.0, 100.0],
            rtol = 0.0, atol = 1e-12
        )
        np.testing.assert_allclose(
            negative.GetFrequencies(100.0), [125.0, 100.0, 150.0],
            rtol = 0.0, atol = 1e-12
        )
        np.testing.assert_allclose(
            fullCycle.GetFrequencies(100.0), [100.0, 150.0, 125.0],
            rtol = 0.0, atol = 1e-12
        )

    def test_NoteArpeggioSchedulesRatiosFrequenciesAndRemainders(self):
        duration = Fraction(7, 4 * 44100)
        step = Fraction(2, 4 * 44100)

        ratioNotes = Sequence([
            Tempo(60),
            Note(0, 0, 100.0, duration).Arpeggio([1.5, 1.25], step),
        ]).ScheduleNotes()
        frequencyNotes = Sequence([
            Tempo(60),
            Note(0, 0, 100.0, duration).Arpeggio([150.0, 125.0], step),
        ]).ScheduleNotes()

        expectedFrequencies = [100.0, 150.0, 125.0, 100.0]
        self.assertEqual([item.note.freq for item in ratioNotes], expectedFrequencies)
        self.assertEqual([item.note.freq for item in frequencyNotes], expectedFrequencies)
        self.assertEqual([item.startFrame for item in ratioNotes], [0, 2, 4, 6])
        self.assertEqual(
            [round(item.duration * 44100) for item in ratioNotes],
            [2, 2, 2, 1]
        )

    def test_PolyphonicArpeggioPreservesNoteModulationPhases(self):
        duration = Fraction(8, 4 * 44100)
        step = Fraction(2, 4 * 44100)
        rate = 44100.0 / 16.0
        sequence = Sequence([
            Tempo(60),
            SetPatch(Patch(polyphonic = True)),
            Note(0, 0, 100.0, duration)
                .Arpeggio([1.5], step)
                .Tremolo(0.5, rate, "Sine")
                .AutoPan(1.0, rate, "Sine", 90.0),
        ])
        scheduledNotes = sequence.ScheduleNotes()

        for scheduled in scheduledNotes:
            scheduled.noteTremolo = (0.5, rate, "sine")
            scheduled.noteAutoPan = (1.0, rate, "sine", 90.0)

        sequence.ResolveModulationPhases(scheduledNotes)

        self.assertTrue(all(scheduled.polyphonic for scheduled in scheduledNotes))
        np.testing.assert_allclose(
            [scheduled.tremoloPhaseDegrees for scheduled in scheduledNotes],
            [270.0, 315.0, 0.0, 45.0],
            rtol = 0.0,
            atol = 1e-12
        )
        np.testing.assert_allclose(
            [scheduled.autoPanOffset for scheduled in scheduledNotes],
            [90.0, 135.0, 180.0, 225.0],
            rtol = 0.0,
            atol = 1e-12
        )

    def test_NoteArpeggioDynamicsRepeatWithDuplicatePatternPitches(self):
        duration = Fraction(8, 4 * 44100)
        step = Fraction(2, 4 * 44100)
        scheduled = Sequence([
            Tempo(60),
            Note(0, 0, 100.0, duration, 0.8).Fade(0.4).Arpeggio(
                [1.5, 1.5], step, dynamics = [1.0, 0.25]
            ),
        ]).ScheduleNotes()

        self.assertEqual(
            [item.note.freq for item in scheduled],
            [100.0, 150.0, 150.0, 100.0]
        )
        np.testing.assert_allclose(
            [item.note.amplitude for item in scheduled],
            [0.8, 0.4, 0.2, 0.8]
        )
        np.testing.assert_allclose(
            [item.note.fadeTarget for item in scheduled],
            [0.4, 0.2, 0.1, 0.4]
        )

    def test_NoteArpeggioRetriggersEnvelopeButPreservesItsGlobalFade(self):
        attackFrequencies = []

        def Transient(freq, dur, amp):
            attackFrequencies.append(float(freq))
            return []

        def Constant(time, frequency):
            return 1.0

        def Body(freq, dur, amp):
            return [Tone(freq, dur, amp).Wave(Constant)]

        duration = Fraction(8, 4 * 44100)
        step = Fraction(4, 4 * 44100)
        envelope = Envelope(
            2.0 / 44100.0, 0.0, 1.0, 0.0, retrigger = False
        )
        patch = Patch(
            transient = Transient,
            body = Body,
            polyphonic = False,
            envelope = envelope
        )
        envelopeSamples = Sequence([
            Tempo(60),
            SetPatch(patch),
            Note(0, 0, 100.0, duration).Arpeggio([1.5], step),
        ]).RenderSamples(channels = 1)

        self.assertEqual(attackFrequencies, [100.0, 150.0])
        self.assertEqual(envelopeSamples[0], 0.0)
        self.assertEqual(envelopeSamples[4], 0.0)

        fadePatch = Patch(body = Body, polyphonic = False)
        fadeSamples = Sequence([
            Tempo(60),
            SetPatch(fadePatch),
            Note(0, 0, 100.0, duration, 0.0).Fade(1.0).Arpeggio([1.5], step),
        ]).RenderSamples(channels = 1)
        expectedFade = ChirpDSP(channels = 1).GetEasingValues(8, "linear")
        expectedFade[-1] = 0.0
        np.testing.assert_allclose(fadeSamples, expectedFade, rtol = 0.0, atol = 1e-12)

    def test_ToneArpeggioRendersThroughMonophonicPatchLayers(self):
        frequencies = []

        def CaptureFrequency(time, frequency):
            frequencies.append(frequency)
            return 0.0

        def Body(freq, dur, amp):
            return [
                Tone(freq, dur, amp).Wave(CaptureFrequency).Arpeggio(
                    [1.5], 1.0 / 44100.0
                )
            ]

        Sequence([
            Tempo(60),
            SetPatch(Patch(body = Body, polyphonic = False)),
            Note(0, 0, 100.0, Fraction(5, 4 * 44100)),
        ]).RenderSamples(channels = 1)

        np.testing.assert_allclose(frequencies, [100.0, 150.0, 100.0, 150.0, 100.0])

    def test_ToneArpeggioRepeatsJustIntonationPatternExactly(self):
        tone = Tone(100.0, 9.0 / 44100.0).Arpeggio(
            JS.MAJ9, 1.0 / 44100.0
        )
        plan = ChirpSynth(channels = 1).CompileSequence([tone])
        expectedRatios = [
            1.0, 5.0 / 4.0, 3.0 / 2.0, 15.0 / 8.0, 9.0 / 4.0,
            1.0, 5.0 / 4.0, 3.0 / 2.0, 15.0 / 8.0
        ]
        np.testing.assert_allclose(
            [event.freq for event in plan.events],
            np.asarray(expectedRatios) * 100.0
        )
        self.assertTrue(all(not event.fadeOut for event in plan.events[:-1]))
        self.assertTrue(all(not event.fadeIn for event in plan.events[1:]))

    def test_ToneArpeggioDynamicsScaleAmplitudeAndFadeTarget(self):
        tone = Tone(100.0, 4.0 / 44100.0, 0.8).Fade(0.4).Arpeggio(
            [1.5], 1.0 / 44100.0, dynamics = [1.0, 0.25]
        )
        plan = ChirpSynth(channels = 1).CompileSequence([tone])

        self.assertEqual(
            [event.freq for event in plan.events],
            [100.0, 150.0, 100.0, 150.0]
        )
        np.testing.assert_allclose(
            [event.amplitude for event in plan.events],
            [0.8, 0.2, 0.8, 0.2]
        )
        np.testing.assert_allclose(
            [event.amplitudeBend for event in plan.events],
            [0.4, 0.1, 0.4, 0.1]
        )

    def test_AcceleratedTrillMatchesPythonRendering(self):
        if not ChirpKernels.NUMBA_AVAILABLE:
            self.skipTest("Numba is unavailable")

        def Body(freq, dur, amp):
            return [Tone(freq, dur, amp).Wave("Sine")]

        sequence = Sequence([
            Tempo(60),
            SetPatch(Patch(body = Body)),
            Note(0, 0, 100.0, Fraction(16, 4 * 44100)).Trill(
                1.5, Fraction(2, 4 * 44100)
            ),
        ])
        enabled = ChirpKernels.NUMBA_ENABLED
        try:
            ChirpKernels.NUMBA_ENABLED = True
            accelerated = sequence.RenderSamples(channels = 1)
            ChirpKernels.NUMBA_ENABLED = False
            python = sequence.RenderSamples(channels = 1)
        finally:
            ChirpKernels.NUMBA_ENABLED = enabled

        np.testing.assert_allclose(accelerated, python, rtol = 0.0, atol = 1e-12)

    def test_AcceleratedScopedBendsAndFadesMatchPythonRendering(self):
        if not ChirpKernels.NUMBA_AVAILABLE:
            self.skipTest("Numba is unavailable")

        synthesizer = ChirpSynth(channels = 1)
        sampleRate = synthesizer.SAMPLE_RATE
        arguments = {
            "freq": 100.0,
            "duration": 16.0 / sampleRate,
            "wave": synthesizer.oscillator.Sine,
            "bendIn": 50.0,
            "bendInDuration": 5.0 / sampleRate,
            "bendInEasing": "inSine",
            "bendOut": 200.0,
            "bendOutDuration": 5.0 / sampleRate,
            "bendOutEasing": "outSine",
            "performanceBendIn": 75.0,
            "performanceBendInDuration": 4.0 / sampleRate,
            "performanceBendInEasing": "inQuad",
            "performanceBendOut": 150.0,
            "performanceBendOutDuration": 4.0 / sampleRate,
            "performanceBendOutEasing": "outQuad",
            "fadeInDuration": 6.0 / sampleRate,
            "fadeInEasing": "smoothStep3",
            "fadeOutDuration": 6.0 / sampleRate,
            "fadeOutEasing": "outSine",
            "fadeFrames": 0,
        }
        enabled = ChirpKernels.NUMBA_ENABLED
        try:
            ChirpKernels.NUMBA_ENABLED = True
            accelerated = MakeTone(synthesizer, **arguments)[0]
            ChirpKernels.NUMBA_ENABLED = False
            python = MakeTone(synthesizer, **arguments)[0]
        finally:
            ChirpKernels.NUMBA_ENABLED = enabled

        np.testing.assert_allclose(accelerated, python, rtol = 0.0, atol = 1e-12)

    def test_AcceleratedOneFrameBendOutMatchesPythonRendering(self):
        if not ChirpKernels.NUMBA_AVAILABLE:
            self.skipTest("Numba is unavailable")

        synthesizer = ChirpSynth(channels = 1)
        sampleRate = synthesizer.SAMPLE_RATE
        oneFrameArguments = {
            "freq": 440.0,
            "duration": 2.0 / sampleRate,
            "wave": synthesizer.oscillator.Sine,
            "bendOut": 880.0,
            "bendOutDuration": 1.0 / sampleRate,
            "performanceBendOut": 660.0,
            "performanceBendOutDuration": 1.0 / sampleRate,
            "fadeFrames": 0,
        }
        enabled = ChirpKernels.NUMBA_ENABLED
        try:
            ChirpKernels.NUMBA_ENABLED = True
            accelerated = MakeTone(synthesizer, **oneFrameArguments)[0]
            ChirpKernels.NUMBA_ENABLED = False
            python = MakeTone(synthesizer, **oneFrameArguments)[0]
        finally:
            ChirpKernels.NUMBA_ENABLED = enabled

        np.testing.assert_allclose(accelerated, python, rtol = 0.0, atol = 1e-12)

    def test_NoteTrillValidatesTarget(self):
        with self.assertRaises(TypeError):
            Note(0, 0, N.C4, L.L4).Trill("major second")
        with self.assertRaises(ValueError):
            Note(0, 0, N.C4, L.L4).Trill(0.0)
        with self.assertRaises(ValueError):
            Note(0, 0, N.C4, L.L4).Trill(float("inf"))

    def test_NoteStepBendQuantizesDerivedFrequenciesToSemitones(self):
        frequencies = []

        def CaptureFrequency(time, frequency):
            frequencies.append(frequency)
            return 0.0

        def Body(freq, dur, amp):
            return [Tone(freq * 2.0, dur, amp).Wave(CaptureFrequency)]

        duration = Fraction(13, 4 * 44100)
        Sequence([
            Tempo(60),
            SetPatch(Patch(body = Body)),
            Note(0, 0, N.C4, duration).StepBend(N.C5),
        ]).RenderSamples(channels = 1)
        expected = np.array([
            (N.C4 * 2.0) * (2.0 ** (semitone / 12.0))
            for semitone in range(13)
        ])

        np.testing.assert_allclose(frequencies, expected, rtol = 0.0, atol = 1e-10)

    def test_NoteStepBendRoundsArbitraryTargetsAndSupportsDescendingBends(self):
        frequencies = []

        def CaptureFrequency(time, frequency):
            frequencies.append(frequency)
            return 0.0

        def Body(freq, dur, amp):
            return [Tone(freq, dur, amp).Wave(CaptureFrequency)]

        duration = Fraction(13, 4 * 44100)
        target = N.C5 * (2.0 ** (0.4 / 12.0))
        Sequence([
            Tempo(60),
            SetPatch(Patch(body = Body)),
            Note(0, 0, N.C5, duration).StepBend(N.C4),
        ]).RenderSamples(channels = 1)

        expected = np.array([
            N.C5 * (2.0 ** (-semitone / 12.0))
            for semitone in range(13)
        ])
        np.testing.assert_allclose(frequencies, expected, rtol = 0.0, atol = 1e-10)

        frequencies.clear()
        Sequence([
            Tempo(60),
            SetPatch(Patch(body = Body)),
            Note(0, 0, N.C5, duration).StepBend(target),
        ]).RenderSamples(channels = 1)
        self.assertAlmostEqual(frequencies[-1], N.C5)

    def test_NoteStepBendUsesSortedCustomRatiosWithoutCrossingTarget(self):
        frequencies = []

        def CaptureFrequency(time, frequency):
            frequencies.append(frequency)
            return 0.0

        def Body(freq, dur, amp):
            return [Tone(freq, dur, amp).Wave(CaptureFrequency)]

        ratios = [3.0, 1.75, 1.0, 1.5, 1.5, 0.5]
        note = Note(0, 0, 100.0, Fraction(4, 4 * 44100)).StepBend(
            200.0, ratios
        )
        ratios.append(2.0)
        Sequence([
            Tempo(60),
            SetPatch(Patch(body = Body)),
            note,
        ]).RenderSamples(channels = 1)

        self.assertEqual(note.bendRatios, (1.0, 1.5, 1.75, 3.0))
        np.testing.assert_allclose(frequencies, [100.0, 150.0, 175.0, 200.0])

    def test_NoteStepBendRepeatsRatiosAtOctavesWithoutDescending(self):
        frequencies = []

        def CaptureFrequency(time, frequency):
            frequencies.append(frequency)
            return 0.0

        def Body(freq, dur, amp):
            return [Tone(freq, dur, amp).Wave(CaptureFrequency)]

        duration = Fraction(8, 4 * 44100)
        ratios = [1.0, 1.5, 1.75, 3.0]
        Sequence([
            Tempo(60),
            SetPatch(Patch(body = Body)),
            Note(0, 0, 100.0, duration).StepBend(900.0, ratios),
        ]).RenderSamples(channels = 1)

        expanded = np.array([1.0, 1.5, 1.75, 3.0, 3.5, 6.0, 7.0, 8.0])
        expected = 100.0 * expanded
        np.testing.assert_allclose(frequencies, expected)

        frequencies.clear()
        Sequence([
            Tempo(60),
            SetPatch(Patch(body = Body)),
            Note(0, 0, 900.0, duration).StepBend(100.0, ratios),
        ]).RenderSamples(channels = 1)
        np.testing.assert_allclose(frequencies, 900.0 / expanded)

    def test_NoteStepBendRepeatsScalesAndExtendedChordsByOctave(self):
        major = PerformanceFrequency.GetStepBendRatios(
            100.0, 400.0, ES.MAJOR
        )
        expectedMajor = np.array([
            ratio * octave
            for octave in (1.0, 2.0)
            for ratio in ES.MAJOR
        ] + [4.0])
        np.testing.assert_allclose(major, expectedMajor)

        majorNinth = PerformanceFrequency.GetStepBendRatios(
            100.0, 450.0, JS.MAJ9
        )
        expectedMajorNinth = np.array([
            1.0, 5.0 / 4.0, 3.0 / 2.0, 15.0 / 8.0, 9.0 / 4.0,
            5.0 / 2.0, 3.0, 15.0 / 4.0, 9.0 / 2.0
        ])
        np.testing.assert_allclose(majorNinth, expectedMajorNinth)

    def test_NoteStepBendGivesFirstAndLastStepsEqualTime(self):
        frequencies = []

        def CaptureFrequency(time, frequency):
            frequencies.append(frequency)
            return 0.0

        def Body(freq, dur, amp):
            return [Tone(freq, dur, amp).Wave(CaptureFrequency)]

        ratios = [1.0, 1.25, 1.5, 1.75, 2.0]
        Sequence([
            Tempo(60),
            SetPatch(Patch(body = Body)),
            Note(0, 0, 100.0, Fraction(10, 4 * 44100)).StepBend(
                200.0, ratios
            ),
        ]).RenderSamples(channels = 1)

        expected = np.repeat(np.asarray(ratios) * 100.0, 2)
        np.testing.assert_allclose(frequencies, expected)

    def test_NoteStepBendValidatesRatios(self):
        with self.assertRaises(TypeError):
            Note(0, 0, N.C4, L.L4).StepBend(N.C5, "chromatic")
        with self.assertRaises(TypeError):
            Note(0, 0, N.C4, L.L4).StepBend(N.C5, [1.0, True])
        with self.assertRaises(ValueError):
            Note(0, 0, N.C4, L.L4).StepBend(N.C5, [1.0, 0.0])
        with self.assertRaises(ValueError):
            Note(0, 0, N.C4, L.L4).StepBend(N.C5, [1.0, float("inf")])

    def test_NoteStepBendLeavesExplicitPatchFrequenciesUnchanged(self):
        frequencies = []

        def CaptureFrequency(time, frequency):
            frequencies.append(frequency)
            return 0.0

        def Body(freq, dur, amp):
            return [Tone(440.0, dur, amp).Wave(CaptureFrequency)]

        Sequence([
            SetPatch(Patch(body = Body)),
            Note(0, 0, N.C4, L.L64).StepBend(N.C5),
        ]).RenderSamples(channels = 1)

        np.testing.assert_allclose(frequencies, 440.0, rtol = 0.0, atol = 0.0)

    def test_NoteBendAndStepBendUseLastCall(self):
        note = Note(0, 0, N.C4, L.L4).StepBend(N.C5).Bend(N.G4)
        self.assertFalse(note.bendStepped)
        self.assertEqual(note.bend, N.G4)

        note.Bend(N.G4).StepBend(N.C5)
        self.assertTrue(note.bendStepped)
        self.assertEqual(note.bend, N.C5)

    def test_NoteAndPatchToneBendsResolveBeforeRendering(self):
        def Transient(freq, dur, amp):
            return [Tone(freq * 0.5, dur, amp).Wave("SawAA").Bend(freq)]

        samples = Sequence([
            Tempo(120),
            SetPatch(Patch(transient = Transient, polyphonic = False)),
            Note(0, 0, N.G4, L.L64, 0.25).Bend(N.G5, "outSine"),
        ]).RenderSamples(channels = 1)

        self.assertGreater(len(samples), 0)
        self.assertTrue(np.all(np.isfinite(samples)))

    def test_ExplicitPatchFrequenciesIgnoreNoteBendAndVibrato(self):
        def Body(freq, dur, amp):
            return [Tone(440.0, dur, amp).Wave("Sine")]

        plain = Sequence([
            SetPatch(Patch(body = Body)),
            Note(0, 0, N.C4, L.L64),
        ]).RenderSamples(channels = 1)
        performed = Sequence([
            SetPatch(Patch(body = Body)),
            Note(0, 0, N.C4, L.L64).Bend(N.G4).Vibrato(100.0, 8.0),
        ]).RenderSamples(channels = 1)

        np.testing.assert_array_equal(performed, plain)

    def test_PerformedFrequenciesSupportOrdinaryArithmetic(self):
        received = []

        def Body(freq, dur, amp):
            received.extend([
                float(freq * 2.0),
                float(freq / 2.0),
                float(freq + 10.0),
                float(freq - 10.0),
                float(1000.0 - freq),
                float(1000.0 / freq),
            ])
            return []

        Sequence([
            SetPatch(Patch(body = Body)),
            Note(0, 0, 400.0, L.L4).Vibrato(),
        ]).RenderSamples(channels = 1)

        np.testing.assert_allclose(
            received,
            [800.0, 200.0, 410.0, 390.0, 600.0, 2.5],
            rtol = 0.0,
            atol = 0.0
        )

    def test_SetPatchChangesFollowingNotesOnly(self):
        firstPatch = self.MakeInsertPatch(1.0)
        secondPatch = self.MakeInsertPatch(2.0)
        sequence = Sequence([
            SetPatch(firstPatch),
            Note(0, 0, N.C4, L.L4),
            SetPatch(secondPatch),
            Note(0, 0, N.C4, L.L4),
        ])

        samples = sequence.RenderSamples(channels = 1)

        np.testing.assert_array_equal(samples, [3.0])

    def test_SetPatchBalanceUsesDefaultsWithoutMutatingPatch(self):
        transient = Sound(samples = [1.0], channels = 1)
        body = Sound(samples = [2.0], channels = 1)

        def Transient(freq, dur, amp):
            return [Insert(transient)]

        def Body(freq, dur, amp):
            return [Insert(body)]

        patch = Patch(Transient, Body, transientGain = 0.5, bodyGain = 2.0)
        sequence = Sequence([
            Tempo(60),
            SetPatch(patch, balance = -0.5),
            Note(0, 0, N.C4, L.L4),
            SetPatch(patch),
            Note(0, 1, N.C4, L.L4),
        ])
        samples = sequence.RenderSamples(channels = 1)

        self.assertEqual(samples[0], 2.5)
        self.assertEqual(samples[44100], 4.5)
        self.assertEqual(patch.transientGain, 0.5)
        self.assertEqual(patch.bodyGain, 2.0)

        self.assertEqual(SetPatch(patch, balance = -2.0).balance, -1.0)
        self.assertEqual(SetPatch(patch, balance = 2.0).balance, 1.0)
        with self.assertRaises(TypeError):
            SetPatch(patch, balance = True)
        with self.assertRaises(ValueError):
            SetPatch(patch, balance = float("inf"))

    def test_SetPatchBalanceAppliesToMonophonicPatches(self):
        transient = Sound(samples = [1.0], channels = 1)
        body = Sound(samples = [2.0], channels = 1)

        def Transient(freq, dur, amp):
            return [Insert(transient)]

        def Body(freq, dur, amp):
            return [Insert(body)]

        patch = Patch(
            Transient, Body,
            transientGain = 0.5, bodyGain = 2.0,
            polyphonic = False
        )
        samples = Sequence([
            Tempo(60),
            SetPatch(patch, balance = -1.0),
            Note(0, 0, N.C4, L.L4),
            SetPatch(patch, balance = 1.0),
            Note(0, 1, N.C4, L.L4),
        ]).RenderSamples(channels = 1)

        self.assertEqual(samples[0], 0.5)
        self.assertEqual(samples[44100], 4.0)

    def test_SetPatchOverridesPolyphonyWithoutMutatingPatch(self):
        defaultDurations = []
        overriddenDurations = []

        def DefaultBody(freq, dur, amp):
            defaultDurations.append(dur)
            return []

        def OverriddenBody(freq, dur, amp):
            overriddenDurations.append(dur)
            return []

        defaultPatch = Patch(body = DefaultBody, polyphonic = False)
        overriddenPatch = Patch(body = OverriddenBody, polyphonic = False)
        Sequence([
            Tempo(60),
            SetPatch(defaultPatch),
            Note(0, 0, N.C4, L.L2),
            Note(0, 1, N.E4, L.L4),
        ]).RenderSamples(channels = 1)
        Sequence([
            Tempo(60),
            SetPatch(overriddenPatch, polyphonic = True),
            Note(0, 0, N.C4, L.L2),
            Note(0, 1, N.E4, L.L4),
        ]).RenderSamples(channels = 1)

        self.assertEqual(defaultDurations, [1.0, 1.0])
        self.assertEqual(overriddenDurations, [2.0, 1.0])
        self.assertFalse(overriddenPatch.polyphonic)

        with self.assertRaises(TypeError):
            SetPatch(overriddenPatch, polyphonic = 1)

    def test_SequenceExtendsThroughTheLongestLayer(self):
        def Transient(freq, dur, amp):
            return [Tone(freq, 0.25, amp).Wave("Sine")]

        def Body(freq, dur, amp):
            return [Tone(freq, 0.5, amp).Wave("Sine")]

        sequence = Sequence([
            Tempo(120),
            SetPatch(Patch(Transient, Body)),
            Note(0, 1, N.C4, L.L64),
        ])
        sound = Sound(sequence, channels = 1)

        self.assertEqual(sound.duration, 1.0)

    def test_SoundAcceptsASequenceAsAnAlternateInput(self):
        sequence = Sequence([
            SetPatch(self.MakeInsertPatch(0.75)),
            Note(0, 0, N.C4, L.L4),
        ])

        sound = Sound(sequence, channels = 1)
        sequentialFlag = Sound(sequence, channels = 1, layered = False)
        rendered = sequence.Render(channels = 1)

        np.testing.assert_array_equal(sound.samples, [0.75])
        np.testing.assert_array_equal(sequentialFlag.samples, sound.samples)
        np.testing.assert_array_equal(sound.samples, rendered.samples)

    def test_SequenceTimingControlsApplyRegardlessOfDeclarationPosition(self):
        patch = self.MakeInsertPatch()
        early = Sequence([
            Tempo(60),
            Meter(6, 8),
            SetPatch(patch),
            Note(0, 1, N.C4, L.L4),
        ]).RenderSamples(channels = 1)
        late = Sequence([
            SetPatch(patch),
            Note(0, 1, N.C4, L.L4),
            Tempo(60),
            Meter(6, 8),
        ]).RenderSamples(channels = 1)

        np.testing.assert_array_equal(late, early)

    def test_SequenceRejectsDuplicateTimingControls(self):
        with self.assertRaises(ValueError):
            Sequence([Tempo(60), Tempo(90)]).RenderSamples()
        with self.assertRaises(ValueError):
            Sequence([Meter(4, 4), Meter(3, 4)]).RenderSamples()

    def test_SequenceStartAndEndSelectAndRebaseNotes(self):
        def Body(freq, dur, amp):
            return [Insert(Sound(samples = [amp], channels = 1))]

        source = Sequence([
            Tempo(60),
            Meter(4, 4),
            SetPatch(Patch(body = Body)),
            Note(0, 0, N.C4, L.L4, 1.0),
            Note(1, 0, N.C4, L.L4, 2.0),
            Note(2, 0, N.C4, L.L4, 3.0),
        ])
        sequence = source.Start(1, 0).End(2, 0)

        np.testing.assert_array_equal(sequence.RenderSamples(channels = 1), [2.0])
        self.assertEqual(source.RenderSamples(channels = 1)[0], 1.0)

        rearranged = (
            source.End(1, 0)
            + source.Start(2, 0).End(3, 0)
            + source.Start(1, 0).End(2, 0)
        ).RenderSamples(channels = 1)
        nonzero = np.flatnonzero(rearranged)
        np.testing.assert_array_equal(nonzero, [0, 176400, 352800])
        np.testing.assert_array_equal(rearranged[nonzero], [1.0, 3.0, 2.0])

    def test_SequenceBarHelpersUseValidNoteStartsOnly(self):
        sequence = Sequence([
            Tempo(60),
            Meter(4, 4),
            Note(5, 0, N.C4, L.L8),
            Note(2, 0, N.C4, L.L8X),
            Note(8, 4, N.C4, L.L4),
        ]).End(10, 0)

        self.assertEqual(sequence.FirstBar(), 2)
        self.assertEqual(sequence.LastBar(), 5)
        self.assertIsNone(Sequence().FirstBar())
        self.assertIsNone(Sequence().LastBar())

    def test_SequenceTrimSelectsOccupiedBarsWithoutMutatingSource(self):
        def Body(freq, dur, amp):
            return [Insert(Sound(samples = [amp], channels = 1))]

        source = Sequence([
            Tempo(60),
            Meter(4, 4),
            SetPatch(Patch(body = Body)),
            Note(2, 0, N.C4, L.L4, 1.0),
            Note(5, 0, N.C4, L.L4, 2.0),
        ]).End(8, 0)
        trimmed = source.Trim()
        nonzero = np.flatnonzero(trimmed.RenderSamples(channels = 1))

        self.assertEqual(source.FirstBar(), 2)
        self.assertEqual(source.LastBar(), 5)
        self.assertEqual(trimmed.FirstBar(), 0)
        self.assertEqual(trimmed.LastBar(), 3)
        np.testing.assert_array_equal(nonzero, [0, 529200])

        empty = Sequence([Tempo(60), Meter(4, 4)]).Trim()
        self.assertEqual(len(empty.RenderSamples(channels = 1)), 0)

    def test_SequenceBarHelpersRespectSelectionsMetersAndRepetition(self):
        first = Sequence([
            Meter(4, 4),
            Note(2, 0, N.C4, L.L2X),
        ]).End(4, 0)
        second = Sequence([
            Meter(3, 4),
            Note(1, 0, N.C4, L.L1D),
        ]).End(3, 0)
        song = first + (second * 2)

        self.assertEqual(song.FirstBar(), 2)
        self.assertEqual(song.LastBar(), 8)

        selected = Sequence([
            Meter(4, 4),
            Note(2, 0, N.C4, L.L4),
            Note(4, 0, N.C4, L.L4),
            Note(6, 0, N.C4, L.L4),
        ]).End(8, 0).Start(1, 0).End(7, 0)
        trimmed = selected.Trim()

        self.assertEqual(selected.FirstBar(), 1)
        self.assertEqual(selected.LastBar(), 5)
        self.assertEqual(trimmed.FirstBar(), 0)
        self.assertEqual(trimmed.LastBar(), 4)

    def test_SequenceGainReturnsAScaledStructuralCopy(self):
        sourceNote = Note(0, 0, N.C4, L.L4, 0.8).Fade(0.4)
        source = Sequence([sourceNote])
        gained = (source + source).Gain(0.5)

        gainedNotes = [
            event
            for segment in gained.GetSegments()
            for event in segment.section.events
            if isinstance(event, Note)
        ]

        self.assertEqual([note.amplitude for note in gainedNotes], [0.4, 0.4])
        self.assertEqual([note.fadeTarget for note in gainedNotes], [0.2, 0.2])
        self.assertEqual(sourceNote.amplitude, 0.8)
        self.assertEqual(sourceNote.fadeTarget, 0.4)

        restored = gained.Gain(2.0)
        restoredNotes = [
            event
            for segment in restored.GetSegments()
            for event in segment.section.events
            if isinstance(event, Note)
        ]
        self.assertEqual([note.amplitude for note in restoredNotes], [0.8, 0.8])
        self.assertEqual([note.fadeTarget for note in restoredNotes], [0.4, 0.4])

    def test_SequenceGainRequiresAFiniteNonNegativeNumber(self):
        sequence = Sequence()

        with self.assertRaises(TypeError):
            sequence.Gain(True)
        with self.assertRaises(TypeError):
            sequence.Gain("0.5")
        with self.assertRaises(ValueError):
            sequence.Gain(float("inf"))
        with self.assertRaises(ValueError):
            sequence.Gain(-1.0)

    def test_SequenceRangeClampsNegativePositionsAndRejectsBeatOverflow(self):
        patch = self.MakeInsertPatch()
        source = Sequence([
            SetPatch(patch),
            Note(0, 0, N.C4, L.L4),
        ])
        clamped = source.Start(-2, -1).End(0, 1).RenderSamples(channels = 1)

        np.testing.assert_array_equal(clamped, [1.0])
        with self.assertRaises(ValueError):
            source.Start(0, 4).RenderSamples(channels = 1)

    def test_SequenceWarnsAndSkipsNotesOutsideTheirBars(self):
        def Body(freq, dur, amp):
            return [Insert(Sound(samples = [amp], channels = 1))]

        sequence = Sequence([
            Tempo(60),
            Meter(4, 4),
            SetPatch(Patch(body = Body)),
            Note(0, 0, N.C4, L.L4, 1.0),
            Note(0, 4, N.C4, L.L4, 8.0),
            Note(1, -0.5, N.C4, L.L4, 9.0),
            Note(1, 0, N.C4, L.L4, 2.0),
        ])

        with warnings.catch_warnings(record = True) as caught:
            warnings.simplefilter("always")
            samples = sequence.RenderSamples(channels = 1)

        nonzero = np.flatnonzero(samples)
        np.testing.assert_array_equal(nonzero, [0, 176400])
        np.testing.assert_array_equal(samples[nonzero], [1.0, 2.0])
        self.assertEqual(len(caught), 1)
        self.assertIs(caught[0].category, UserWarning)
        self.assertIn("Ignored 2 Notes", str(caught[0].message))

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            selected = sequence.Start(1, 0).RenderSamples(channels = 1)
            repeated = (sequence * 2).RenderSamples(channels = 1)

        np.testing.assert_array_equal(np.flatnonzero(selected), [0])
        np.testing.assert_array_equal(selected[0], 2.0)
        repeatedNonzero = np.flatnonzero(repeated)
        np.testing.assert_array_equal(
            repeatedNonzero, [0, 176400, 352800, 529200]
        )
        np.testing.assert_array_equal(
            repeated[repeatedNonzero], [1.0, 2.0, 1.0, 2.0]
        )

    def test_SequenceRejectsReverseRangeAndAllowsEmptyRange(self):
        with self.assertRaises(ValueError):
            Sequence([]).Start(2, 0).End(1, 0).RenderSamples()

        empty = Sequence([
            Note(1, 0, N.C4, L.L4),
        ]).Start(1, 0).End(1, 0).RenderSamples()
        self.assertEqual(len(empty), 0)

    def test_SequenceCompositionAndRepetitionUseLocalTiming(self):
        first = Sequence([
            Tempo(60),
            Meter(1, 4),
            SetPatch(self.MakeInsertPatch(1.0)),
            Note(0, 0, N.C4, L.L4),
        ]).End(1, 0)
        second = Sequence([
            Tempo(120),
            Meter(1, 8),
            SetPatch(self.MakeInsertPatch(2.0)),
            Note(0, 0, N.C4, L.L4),
        ]).End(1, 0)
        song = first + (second * 3)
        first.events[-1].beat = 10

        samples = song.RenderSamples(channels = 1)
        nonzero = np.flatnonzero(samples)

        np.testing.assert_array_equal(nonzero, [0, 44100, 55125, 66150])
        np.testing.assert_array_equal(samples[nonzero], [1.0, 2.0, 2.0, 2.0])

    def test_ComposedSequenceRangeUsesEachSectionsMeterAndTempo(self):
        def Body(freq, dur, amp):
            return [Insert(Sound(samples = [amp], channels = 1))]

        patch = Patch(body = Body)
        first = Sequence([
            Tempo(240),
            Meter(2, 4),
            SetPatch(patch),
            Note(0, 0, N.C4, L.L4, 1.0),
            Note(1, 0, N.C4, L.L4, 2.0),
        ])
        second = Sequence([
            Tempo(120),
            Meter(3, 8),
            SetPatch(patch),
            Note(0, 0, N.C4, L.L4, 3.0),
            Note(1, 0, N.C4, L.L4, 4.0),
        ])

        song = first + second
        selected = song.Start(1, 0).End(3, 0)
        samples = selected.RenderSamples(channels = 1)
        nonzero = np.flatnonzero(samples)

        np.testing.assert_array_equal(nonzero, [0, 22050])
        np.testing.assert_array_equal(samples[nonzero], [2.0, 3.0])
        self.assertEqual(song.RenderSamples(channels = 1)[0], 1.0)

    def test_SequenceRepetitionCountMatchesPythonSequences(self):
        sequence = Sequence([
            SetPatch(self.MakeInsertPatch()),
            Note(0, 0, N.C4, L.L4),
        ]).End(0, 1)

        np.testing.assert_array_equal((3 * sequence).RenderSamples(1), (sequence * 3).RenderSamples(1))
        self.assertEqual(len((sequence * 0).RenderSamples(1)), 0)
        self.assertEqual(len((sequence * -2).RenderSamples(1)), 0)
        with self.assertRaises(TypeError):
            sequence * 1.5

    def test_SequenceInferredSpanRoundsUpToTheNextBar(self):
        first = Sequence([
            Tempo(60),
            Meter(4, 4),
            SetPatch(self.MakeInsertPatch(1.0)),
            Note(0, 0, N.C4, L.L8),
        ])
        second = Sequence([
            Tempo(60),
            Meter(4, 4),
            SetPatch(self.MakeInsertPatch(2.0)),
            Note(0, 0, N.C4, L.L4),
        ])

        samples = (first + second).RenderSamples(channels = 1)

        self.assertEqual(samples[0], 1.0)
        self.assertEqual(samples[4 * 44100], 2.0)

    def test_SequenceTailPlaysBeyondEndAndOverlapsTheNextSection(self):
        tail = Sound(samples = [1.0, 1.0], channels = 1)

        def Tail(freq, dur, amp):
            return [Insert(tail)]

        first = Sequence([
            Tempo(60),
            Meter(4, 4),
            SetPatch(Patch(body = Tail)),
            Note(0, 0, N.C4, L.L4),
        ]).End(0, Fraction(1, 44100))
        second = Sequence([
            SetPatch(self.MakeInsertPatch(2.0)),
            Note(0, 0, N.C4, L.L4),
        ])

        np.testing.assert_array_equal(first.RenderSamples(1), [1.0, 1.0])
        np.testing.assert_array_equal((first + second).RenderSamples(1)[:2], [1.0, 3.0])

    def test_MonophonicResolutionCrossesSequenceBoundaries(self):
        receivedDurations = []

        def Body(freq, dur, amp):
            receivedDurations.append(dur)
            return []

        patch = Patch(body = Body, polyphonic = False)
        first = Sequence([
            Tempo(60),
            Meter(1, 4),
            SetPatch(patch),
            Note(0, 0, N.C4, L.L2),
        ]).End(1, 0)
        second = Sequence([
            Tempo(120),
            Meter(1, 4),
            SetPatch(patch),
            Note(0, 0, N.E4, L.L4),
        ]).End(1, 0)

        (first + second).RenderSamples(channels = 1)

        self.assertEqual(receivedDurations, [1.0, 0.5])

    def test_NoteDoesNotExposeToneOnlyControls(self):
        note = Note(0, 0, N.C4, L.L4)

        for methodName in ("Wave", "Phase", "Mod", "Unison"):
            self.assertFalse(hasattr(note, methodName))

        self.assertTrue(hasattr(note, "Vibrato"))
        self.assertTrue(hasattr(note, "Tremolo"))

    def test_TransformedRatioTargetsApplyArithmeticToBothEndpoints(self):
        frequency = PerformanceFrequency(
            100.0, bend = 2.0, trill = 2.0
        ) + 10.0
        reversedFrequency = 1000.0 - PerformanceFrequency(
            100.0, bend = 2.0, trill = 2.0
        )

        self.assertEqual(frequency.value, 110.0)
        self.assertEqual(frequency.ResolveBend(), 210.0)
        self.assertEqual(frequency.ResolveTrill(), 210.0)
        self.assertEqual(reversedFrequency.value, 900.0)
        self.assertEqual(reversedFrequency.ResolveBend(), 800.0)
        self.assertEqual(reversedFrequency.ResolveTrill(), 800.0)

    def test_PerformanceFrequencyBehavesLikeARealNumber(self):
        frequency = PerformanceFrequency(220.0, bend = 440.0)

        self.assertEqual(min(300.0, frequency), frequency)
        self.assertEqual(max(100.0, frequency), frequency)
        self.assertEqual(Tone(440.0).Mod(frequency * 3.0).modFreq, 660.0)

        stepCount = max(4.0, min(32.0, 16.0 * (440.0 / frequency)))
        cutoff = frequency * stepCount
        self.assertEqual(float(cutoff), 7040.0)
        self.assertEqual(cutoff.ResolveBend(), 14080.0)

    def test_ToneArpeggioContinuesPerformanceBendProgress(self):
        frequencies = []

        def CaptureFrequency(time, frequency):
            frequencies.append(frequency)
            return 0.0

        duration = 8.0 / ChirpSynth.SAMPLE_RATE
        performed = PerformanceFrequency(
            100.0,
            bendIn = 50.0,
            bendInDuration = 3.0 / ChirpSynth.SAMPLE_RATE,
            bendOut = 200.0,
            bendOutDuration = 3.0 / ChirpSynth.SAMPLE_RATE,
            duration = duration
        )
        synthesizer = ChirpSynth(channels = 1)
        plan = synthesizer.CompileSequence([
            Seconds(),
            Tone(performed, duration).Wave(CaptureFrequency).Arpeggio(
                [1.0, 1.5], 3.0 / ChirpSynth.SAMPLE_RATE
            ),
        ])
        synthesizer.RenderPlan(plan)

        self.assertEqual(len(frequencies), 8)
        self.assertGreater(frequencies[6], 100.0)

    def test_OneFrameEnvelopeReleaseEndsAtZero(self):
        patch = Patch(envelope = Envelope(
            0.0, 0.0, 1.0, 1.0 / Patch.SAMPLE_RATE
        ))

        np.testing.assert_array_equal(
            patch.GetEnvelopeGains(1.0 / Patch.SAMPLE_RATE),
            [1.0, 0.0]
        )

    def test_LongLeftAssociativeSequenceCompositionIsLinearAndRecursionSafe(self):
        phrase = Sequence([Note(0, 0, N.C4, L.L64)])
        song = phrase
        for _ in range(999):
            song = song + phrase

        self.assertEqual(len(song.GetSegments()), 1000)

    def test_MonophonicEnvelopeTailsDoNotRerenderPrefixes(self):
        callbackCount = 0

        def CustomWave(time, frequency):
            nonlocal callbackCount
            callbackCount += 1
            return 0.0

        def Body(freq, dur, amp):
            return [Tone(freq, dur, amp).Wave(CustomWave)]

        patch = Patch(
            body = Body,
            envelope = Envelope(0.0, 0.0, 1.0, 4.0 / Patch.SAMPLE_RATE),
            polyphonic = False
        )
        Sequence([
            Tempo(60), Meter(32, 4), SetPatch(patch),
            *[
                Note(
                    0, Fraction(beat, Patch.SAMPLE_RATE), N.C4,
                    Fraction(1, 4 * Patch.SAMPLE_RATE)
                )
                for beat in range(20)
            ],
        ]).RenderSamples(channels = 1)

        self.assertEqual(callbackCount, 100)


if __name__ == "__main__":
    unittest.main()
