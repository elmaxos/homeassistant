"""Erzeugt rosa und braunes Rauschen (60 s, 16 kHz, s16le mono) in 8 Lautstaerkestufen (je 6 dB)
nach /config/www/noise/<farbe>_<stufe>.pcm. Stufe 7 = Spitze ~ -1 dBFS, Stufe k = 7 - k mal 6 dB leiser.
Endlos-Schleife ohne Knacken: Anfang und Ende werden ueber 0,5 s ueberblendet."""
import array, math, os, random

RATE, SECS = 16000, 60
N = RATE * SECS
OUT = "/config/www/noise"
os.makedirs(OUT, exist_ok=True)
rnd = random.Random(42)
XF = RATE // 2  # 0,5 s Ueberblendung fuer nahtlose Schleife


def pink(n):
    b0 = b1 = b2 = b3 = b4 = b5 = b6 = 0.0
    out = []
    for _ in range(n):
        w = rnd.uniform(-1, 1)
        b0 = 0.99886 * b0 + w * 0.0555179; b1 = 0.99332 * b1 + w * 0.0750759
        b2 = 0.96900 * b2 + w * 0.1538520; b3 = 0.86650 * b3 + w * 0.3104856
        b4 = 0.55000 * b4 + w * 0.5329522; b5 = -0.7616 * b5 - w * 0.0168980
        out.append(b0 + b1 + b2 + b3 + b4 + b5 + b6 + w * 0.5362); b6 = w * 0.115926
    return out


def brown(n):
    b, out = 0.0, []
    for _ in range(n):
        b = (b + 0.02 * rnd.uniform(-1, 1)) / 1.02
        out.append(b)
    return out


def loopable(x):
    # letzte XF Samples mit den ersten ueberblenden, dann vorne abschneiden -> Ende passt an Anfang
    n = len(x) - XF
    y = x[XF:XF + n]
    for i in range(XF):
        a = i / XF
        y[n - XF + i] = x[XF + n - XF + i] * (1 - a) + x[i] * a
    return y[:n]


for name, gen in (("rosa", pink), ("braun", brown)):
    x = loopable(gen(N + XF))
    m = sum(x) / len(x)
    x = [v - m for v in x]  # DC weg (wichtig bei braun)
    peak = max(abs(v) for v in x)
    for k in range(8):
        scale = 0.89 * 32767 / peak * 10 ** (-(7 - k) * 6 / 20)
        a = array.array("h", (max(-32768, min(32767, int(v * scale))) for v in x))
        a = a[:N] if len(a) >= N else a + array.array("h", [0] * (N - len(a)))
        with open("%s/%s_%d.pcm" % (OUT, name, k), "wb") as f:
            a.tofile(f)
    rms = math.sqrt(sum(v * v for v in x) / len(x)) / peak
    print(name, "fertig, RMS/Peak = %.2f" % rms)
print(sorted(os.listdir(OUT)))
