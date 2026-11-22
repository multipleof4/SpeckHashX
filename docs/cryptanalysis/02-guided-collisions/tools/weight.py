"""The cost that trails.py's model gives a trail: wk + 2*wd, from the Lipmaa-Moriai weight of each addition.

    python weight.py TRAILS

TRAILS: trails as trails.py or trail_of.py print them, one per line. A trail that the model rules out
(an addition whose output difference cannot happen) is reported with "possible": false.
"""
import json, sys
M = 2**64 - 1
ror = lambda v, r: (v >> r | v << 64 - r) & M


def lm(a, b, c):
    """Weight of the XOR difference a, b -> c through addition mod 2^64, or None if impossible (Lipmaa-Moriai)."""
    eq = lambda x, y, z: ~(x ^ y) & ~(x ^ z) & M
    sh = lambda v: v << 1 & M
    if eq(sh(a), sh(b), sh(c)) & (a ^ b ^ c ^ sh(b)): return None
    return bin(~eq(a, b, c) & (M >> 1)).count("1")


def cost(t):
    h = lambda k: [int(w, 16) for w in t[k]]
    k, l, x, y = h("k"), h("l"), h("x"), h("y")
    R = len(k)
    wk = [lm(k[i], ror(l[i], 8), l[i + 3]) for i in range(R - 1)]
    calls = [(x, y)] + ([(h("x2"), h("y2"))] if "x2" in t else [])
    wd = [[lm(ror(a[i], 8), b[i], a[i + 1] ^ k[i]) for i in range(R)] for a, b in calls]
    if None in wk or any(None in w for w in wd): return dict(possible=False)
    return dict(possible=True, wk=sum(wk), wd=[sum(w) for w in wd], cost=sum(wk) + sum(sum(w) for w in wd) * (2 if len(wd) == 1 else 1))


if __name__ == "__main__":
    for line in open(sys.argv[1]):
        t = json.loads(line)
        print(json.dumps(dict(R=len(t["k"]), source=t.get("source"), **cost(t))))
