"""The trail that a pair of step inputs actually follows, from a result line of guided.py or collide.py.

    python trail_of.py RESULTS [R]

RESULTS: a file of result lines; the ones with found true and mode step or free are used.
Prints one trail per pair, in the format of trails.py, with x2 and y2 for the second cipher call.
"""
import json, sys
from ref import M, C, rol, ror


def words(m, g, x, R):
    """Every word of the step on (m, g, x), as in trails.py: k, l, and (x, y) of both calls before each round."""
    k, l = [m & M], [m >> 64, g & M, g >> 64]
    s = [[x >> 64], [x & M], [(x ^ C) >> 64], [x & M]]
    for i in range(R):
        for a, b in ((0, 1), (2, 3)):
            s[a].append((ror(s[a][i], 8) + s[b][i] & M) ^ k[i])
            s[b].append(rol(s[b][i], 3) ^ s[a][-1])
        if i < R - 1:
            l.append((k[i] + ror(l[i], 8) & M) ^ i)
            k.append(rol(k[i], 3) ^ l[-1])
    return dict(k=k, l=l, x=s[0], y=s[1], x2=s[2], y2=s[3])


if __name__ == "__main__":
    for line in open(sys.argv[1]):
        r = json.loads(line)
        if not r.get("found") or r["mode"] not in ("step", "free"): continue
        h = lambda k: int(r[k], 16)
        a, b = ((h(f"m{i}"), h(f"g{i}") if f"g{i}" in r else h("g"), h(f"x{i}") if f"x{i}" in r else h("x")) for i in (1, 2))
        R = r["R"]
        u, v = words(*a, R), words(*b, R)
        t = {k: [f"{p ^ q:016x}" for p, q in zip(u[k], v[k])] for k in u}
        print(json.dumps(dict(R=R, mode="c" if r["mode"] == "step" else "f", source=r.get("dm"), **t)))
