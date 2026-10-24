import math
import unittest

import numpy as np

from Chirper.core import ChirpKernels, Easing
from Chirper.core.ChirpDSP import ChirpDSP


class EasingTests(unittest.TestCase):
    EASING_NAMES = (
        "linear",
        "inSine", "outSine", "inOutSine",
        "inQuad", "outQuad", "inOutQuad",
        "inCubic", "outCubic", "inOutCubic",
        "inQuart", "outQuart", "inOutQuart",
        "inQuint", "outQuint", "inOutQuint",
        "inCircle", "outCircle", "inOutCircle",
        "inExpo", "outExpo", "inOutExpo",
        "inElastic", "outElastic", "inOutElastic",
        "inBack", "outBack", "inOutBack",
        "inBounce", "outBounce", "inOutBounce",
        "inLog", "outLog", "inOutLog",
        "smoothStep3", "smoothStep5", "smoothStep7",
        "equalPower", "cosine",
    )

    def test_AllEasingCurvesHaveExactEndpoints(self):
        for easingName in self.EASING_NAMES:
            with self.subTest(easing = easingName):
                self.assertAlmostEqual(Easing.Apply(0.0, easingName), 0.0)
                self.assertAlmostEqual(Easing.Apply(1.0, easingName), 1.0)

    def test_PythonAndKernelEasingMatch(self):
        for easingName in self.EASING_NAMES:
            easingId = ChirpKernels.GetEasingId(easingName)
            for value in (0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0):
                with self.subTest(easing = easingName, value = value):
                    self.assertAlmostEqual(
                        ChirpKernels.ApplyEasing(value, easingId),
                        Easing.Apply(value, easingName),
                        places = 14
                    )

    def test_EasingNamesIgnoreCaseUnderscoresAndHyphens(self):
        aliases = (
            ("IN_QUART", "inQuart"),
            ("out-circle", "outCircle"),
            ("In_Out_Elastic", "inOutElastic"),
            ("EQUAL-POWER", "equalPower"),
            ("LOGARITHMIC", "outLog"),
            ("COS", "cosine"),
            ("SMOOTH_STEP-5", "smoothStep5"),
        )

        for alias, canonical in aliases:
            with self.subTest(alias = alias):
                self.assertEqual(Easing.Apply(0.37, alias), Easing.Apply(0.37, canonical))
                self.assertEqual(ChirpKernels.GetEasingId(alias), ChirpKernels.GetEasingId(canonical))

    def test_DuplicateAudioCurvesAreAliases(self):
        aliases = (
            (Easing.EqualPower, Easing.OutSine, "equalPower", "outSine"),
            (Easing.Cosine, Easing.InOutSine, "cosine", "inOutSine"),
        )

        for alias, canonical, aliasName, canonicalName in aliases:
            with self.subTest(alias = aliasName):
                self.assertIs(alias, canonical)
                self.assertIs(Easing.Resolve(aliasName), canonical)
                self.assertEqual(ChirpKernels.GetEasingId(aliasName), ChirpKernels.GetEasingId(canonicalName))

    def test_BackAndElasticCurvesPreserveOvershoot(self):
        self.assertLess(Easing.Apply(0.25, "inBack"), 0.0)
        self.assertGreater(Easing.Apply(0.75, "outBack"), 1.0)
        self.assertLess(min(Easing.Apply(i / 100.0, "inElastic") for i in range(101)), 0.0)
        self.assertGreater(max(Easing.Apply(i / 100.0, "outElastic") for i in range(101)), 1.0)

    def test_AudioCurvesUseTheirDocumentedShapes(self):
        self.assertAlmostEqual(Easing.Apply(0.5, "log"), math.log10(5.5))
        self.assertAlmostEqual(Easing.Apply(0.5, "equalPower"), math.sqrt(0.5))
        self.assertAlmostEqual(Easing.Apply(0.5, "cosine"), 0.5)

    def test_RemovedEasingAliasesAreRejected(self):
        for easingName in (
                "inEqualPower", "outEqualPower",
                "inCirc", "outCirc", "inOutCirc"
            ):
            with self.subTest(easing = easingName):
                with self.assertRaises(ValueError):
                    Easing.Resolve(easingName)
                with self.assertRaises(ValueError):
                    ChirpKernels.GetEasingId(easingName)

    def test_SmoothStepCurvesAreSymmetricAndBecomeFlatterAtTheEnds(self):
        for easingName in ("smoothStep3", "smoothStep5", "smoothStep7"):
            with self.subTest(easing = easingName):
                self.assertAlmostEqual(Easing.Apply(0.5, easingName), 0.5)
                self.assertAlmostEqual(
                    Easing.Apply(0.25, easingName),
                    1.0 - Easing.Apply(0.75, easingName)
                )

        self.assertGreater(Easing.Apply(0.01, "smoothStep3"), Easing.Apply(0.01, "smoothStep5"))
        self.assertGreater(Easing.Apply(0.01, "smoothStep5"), Easing.Apply(0.01, "smoothStep7"))

    def test_InputProgressIsClampedBeforeEasing(self):
        self.assertEqual(Easing.Apply(-1.0, "inBack"), 0.0)
        self.assertEqual(Easing.Apply(2.0, "outElastic"), 1.0)

        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value = value):
                with self.assertRaises(ValueError):
                    Easing.Apply(value, "linear")

    def test_CustomEasingReceivesClampedProgressAndMayOvershoot(self):
        received = []

        def CustomEasing(t):
            received.append(t)
            return (t * 2.0) - 0.25

        self.assertEqual(Easing.Apply(-1.0, CustomEasing), -0.25)
        self.assertEqual(Easing.Apply(2.0, CustomEasing), 1.75)
        self.assertEqual(received, [0.0, 1.0])
        self.assertFalse(Easing.IsBuiltIn(CustomEasing))
        self.assertTrue(Easing.IsBuiltIn("inQuad"))

    def test_CustomEasingMustReturnAFiniteNumber(self):
        def TextEasing(t):
            return "invalid"

        def BooleanEasing(t):
            return True

        def InfiniteEasing(t):
            return math.inf

        with self.assertRaises(TypeError):
            Easing.Apply(0.5, TextEasing)
        with self.assertRaises(TypeError):
            Easing.Apply(0.5, BooleanEasing)
        with self.assertRaises(ValueError):
            Easing.Apply(0.5, InfiniteEasing)

    def test_DspEasingValuesAcceptCustomCallables(self):
        def CustomEasing(t):
            return t * t

        values = ChirpDSP(channels = 1).GetEasingValues(5, CustomEasing)
        np.testing.assert_allclose(values, [0.0, 0.0625, 0.25, 0.5625, 1.0])


if __name__ == "__main__":
    unittest.main()
