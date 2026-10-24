import math
import numbers


def Linear(t):
    return t


def InSine(t):
    return 1.0 - math.cos((t * math.pi) / 2.0)


def OutSine(t):
    return math.sin((t * math.pi) / 2.0)


def InOutSine(t):
    return -(math.cos(math.pi * t) - 1.0) / 2.0


def InQuad(t):
    return t * t


def OutQuad(t):
    return 1.0 - ((1.0 - t) * (1.0 - t))


def InOutQuad(t):
    if t < 0.5:
        return 2.0 * t * t

    return 1.0 - (math.pow((-2.0 * t) + 2.0, 2.0) / 2.0)


def InCubic(t):
    return t * t * t


def OutCubic(t):
    return 1.0 - math.pow(1.0 - t, 3.0)


def InOutCubic(t):
    if t < 0.5:
        return 4.0 * t * t * t

    return 1.0 - (math.pow((-2.0 * t) + 2.0, 3.0) / 2.0)


def InQuart(t):
    return t ** 4


def OutQuart(t):
    return 1.0 - math.pow(1.0 - t, 4.0)


def InOutQuart(t):
    if t < 0.5:
        return 8.0 * t ** 4

    return 1.0 - (math.pow((-2.0 * t) + 2.0, 4.0) / 2.0)


def InQuint(t):
    return t ** 5


def OutQuint(t):
    return 1.0 - math.pow(1.0 - t, 5.0)


def InOutQuint(t):
    if t < 0.5:
        return 16.0 * t ** 5

    return 1.0 - (math.pow((-2.0 * t) + 2.0, 5.0) / 2.0)


def InCircle(t):
    return 1.0 - math.sqrt(1.0 - (t * t))


def OutCircle(t):
    return math.sqrt(1.0 - ((t - 1.0) ** 2))


def InOutCircle(t):
    if t < 0.5:
        return (1.0 - math.sqrt(1.0 - ((2.0 * t) ** 2))) / 2.0

    return (math.sqrt(1.0 - (((-2.0 * t) + 2.0) ** 2)) + 1.0) / 2.0


def InExpo(t):
    return 0.0 if t == 0.0 else math.pow(2.0, (10.0 * t) - 10.0)


def OutExpo(t):
    return 1.0 if t == 1.0 else 1.0 - math.pow(2.0, -10.0 * t)


def InOutExpo(t):
    if t == 0.0:
        return 0.0
    if t == 1.0:
        return 1.0
    if t < 0.5:
        return math.pow(2.0, (20.0 * t) - 10.0) / 2.0

    return (2.0 - math.pow(2.0, (-20.0 * t) + 10.0)) / 2.0


def InElastic(t):
    if t == 0.0 or t == 1.0:
        return t

    period = (2.0 * math.pi) / 3.0
    return -math.pow(2.0, (10.0 * t) - 10.0) * math.sin(((10.0 * t) - 10.75) * period)


def OutElastic(t):
    if t == 0.0 or t == 1.0:
        return t

    period = (2.0 * math.pi) / 3.0
    return (math.pow(2.0, -10.0 * t) * math.sin(((10.0 * t) - 0.75) * period)) + 1.0


def InOutElastic(t):
    if t == 0.0 or t == 1.0:
        return t

    period = (2.0 * math.pi) / 4.5
    if t < 0.5:
        return -(math.pow(2.0, (20.0 * t) - 10.0) * math.sin(((20.0 * t) - 11.125) * period)) / 2.0

    return (math.pow(2.0, (-20.0 * t) + 10.0) * math.sin(((20.0 * t) - 11.125) * period) / 2.0) + 1.0


def InBack(t):
    overshoot = 1.70158
    return ((overshoot + 1.0) * t ** 3) - (overshoot * t ** 2)


def OutBack(t):
    overshoot = 1.70158
    return 1.0 + ((overshoot + 1.0) * (t - 1.0) ** 3) + (overshoot * (t - 1.0) ** 2)


def InOutBack(t):
    overshoot = 1.70158 * 1.525
    if t < 0.5:
        return (((2.0 * t) ** 2) * (((overshoot + 1.0) * 2.0 * t) - overshoot)) / 2.0

    return ((((2.0 * t) - 2.0) ** 2) * (((overshoot + 1.0) * ((2.0 * t) - 2.0)) + overshoot) + 2.0) / 2.0


def InBounce(t):
    return 1.0 - OutBounce(1.0 - t)


def OutBounce(t):
    scale = 7.5625
    divisor = 2.75
    if t < 1.0 / divisor:
        return scale * t * t
    if t < 2.0 / divisor:
        t -= 1.5 / divisor
        return (scale * t * t) + 0.75
    if t < 2.5 / divisor:
        t -= 2.25 / divisor
        return (scale * t * t) + 0.9375

    t -= 2.625 / divisor
    return (scale * t * t) + 0.984375


def InOutBounce(t):
    if t < 0.5:
        return (1.0 - OutBounce(1.0 - (2.0 * t))) / 2.0

    return (1.0 + OutBounce((2.0 * t) - 1.0)) / 2.0


def InLog(t):
    return 1.0 - math.log10(10.0 - (9.0 * t))


def OutLog(t):
    return math.log10(1.0 + (9.0 * t))


def InOutLog(t):
    if t < 0.5:
        return InLog(2.0 * t) / 2.0

    return (OutLog((2.0 * t) - 1.0) + 1.0) / 2.0


def SmoothStep3(t):
    return -(2.0 * (t ** 3.0)) + (3.0 * (t ** 2.0))


def SmoothStep5(t):
    return (6.0 * (t ** 5.0)) - (15.0 * (t ** 4.0)) + (10.0 * (t ** 3.0))


def SmoothStep7(t):
    return -(20.0 * (t ** 7.0)) + (70.0 * (t ** 6.0)) - (84.0 * (t ** 5.0)) + (35.0 * (t ** 4.0))


EqualPower = OutSine
Cosine = InOutSine

FUNCTIONS = {
    "linear": Linear,
    "lin": Linear,
    "insine": InSine,
    "outsine": OutSine,
    "inoutsine": InOutSine,
    "inquad": InQuad,
    "outquad": OutQuad,
    "inoutquad": InOutQuad,
    "incubic": InCubic,
    "outcubic": OutCubic,
    "inoutcubic": InOutCubic,
    "inquart": InQuart,
    "outquart": OutQuart,
    "inoutquart": InOutQuart,
    "inquint": InQuint,
    "outquint": OutQuint,
    "inoutquint": InOutQuint,
    "incircle": InCircle,
    "outcircle": OutCircle,
    "inoutcircle": InOutCircle,
    "inexpo": InExpo,
    "outexpo": OutExpo,
    "inoutexpo": InOutExpo,
    "inelastic": InElastic,
    "outelastic": OutElastic,
    "inoutelastic": InOutElastic,
    "inback": InBack,
    "outback": OutBack,
    "inoutback": InOutBack,
    "inbounce": InBounce,
    "outbounce": OutBounce,
    "inoutbounce": InOutBounce,
    "log": OutLog,
    "logarithmic": OutLog,
    "inlog": InLog,
    "outlog": OutLog,
    "inoutlog": InOutLog,
    "smoothstep3": SmoothStep3,
    "smoothstep5": SmoothStep5,
    "smoothstep7": SmoothStep7,
    "equalpower": EqualPower,
    "cos": Cosine,
    "cosine": Cosine,
}


def Resolve(easing = "linear"):
    if easing is None:
        return Linear
    if callable(easing):
        return easing

    key = str(easing).replace("_", "").replace("-", "").lower()
    if key not in FUNCTIONS:
        raise ValueError("Unknown easing: " + str(easing))

    return FUNCTIONS[key]


def IsBuiltIn(easing = "linear"):
    if callable(easing):
        return False

    Resolve(easing)
    return True


def ApplyResolved(t, easingFunction):
    if isinstance(t, bool) or not isinstance(t, numbers.Real):
        raise TypeError("Easing input must be numeric")
    t = float(t)
    if not math.isfinite(t):
        raise ValueError("Easing input must be finite")
    t = max(0.0, min(1.0, t))
    result = easingFunction(t)
    if isinstance(result, bool) or not isinstance(result, numbers.Real):
        raise TypeError("Easing functions must return a number")

    result = float(result)
    if not math.isfinite(result):
        raise ValueError("Easing functions must return a finite number")

    return result


def Apply(t, easing = "linear"):
    return ApplyResolved(t, Resolve(easing))
