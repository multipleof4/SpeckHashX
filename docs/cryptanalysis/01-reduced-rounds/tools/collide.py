"""Actual colliding inputs of the R-round SpeckHashX, found by SAT on the values.

    python collide.py MODE R [SECONDS] [JOBS]

MODE step: two chunks with the same step output, for a g and an x of the solver's choice.
MODE free: two step inputs (m, g, x) with the same step output, differing anywhere.
MODE hash: two 32-byte messages with the same 32-byte hash. They share their first 16 bytes.
MODE hash2: the same, but the two messages may differ anywhere.

Every answer is recomputed with ref.py before it is printed.
Needs the kissat binary: set KISSAT or put it on PATH. SEED0 sets the first of the JOBS seeds (0).
"""
import json, os, subprocess, sys, time
from pathlib import Path
from ref import IV, shx, step

N = 64
KISSAT = os.environ.get("KISSAT", "kissat")
WORK = Path(os.environ.get("WORK", Path(__file__).parent / ".work"))
T = 1  # the variable that is always true


def rol(v, r): return [v[(j - r) % N] for j in range(N)]
def ror(v, r): return rol(v, N - r)
def const(c): return [T if c >> j & 1 else -T for j in range(N)]
def flip(v, c): return [-b if c >> j & 1 else b for j, b in enumerate(v)]


class Model:
    def __init__(s): s.n, s.cl = 1, [[T]]

    def word(s):
        s.n += N
        return list(range(s.n - N + 1, s.n + 1))

    def xor(s, a, b):
        c = s.word()
        for p, q, r in zip(a, b, c):
            s.cl += [[-p, -q, -r], [-p, q, r], [p, -q, r], [p, q, -r]]
        return c

    def add(s, a, b):
        """a + b mod 2^64, bit by bit with a carry."""
        o, cy = s.word(), s.word()
        s.cl.append([-cy[0]])
        for j, (p, q, r, c) in enumerate(zip(a, b, o, cy)):
            for e in range(8):
                # r is the parity of p, q, c: rule out the wrong r for each of their 8 values.
                x, y, z = e & 1, e >> 1 & 1, e >> 2
                s.cl.append([-p if x else p, -q if y else q, -c if z else c, r if x ^ y ^ z else -r])
            if j < N - 1:
                d = cy[j + 1]
                s.cl += [[-p, -q, d], [-p, -c, d], [-q, -c, d], [p, q, -d], [p, c, -d], [q, c, -d]]
        return o

    def step(s, m, g, x, R, out=True):
        """m, g, x are (low, high) pairs of words. Returns the cipher outputs, or with out the new (h, g)."""
        k, l = m[0], [m[1], g[0], g[1]]
        a, b, c, d = x[1], x[0], flip(x[1], 1 << 62), x[0]
        for i in range(R):
            a = s.xor(s.add(ror(a, 8), b), k)
            b = s.xor(rol(b, 3), a)
            c = s.xor(s.add(ror(c, 8), d), k)
            d = s.xor(rol(d, 3), c)
            if i < R - 1:
                l.append(flip(s.add(k, ror(l[i], 8)), i))
                k = s.xor(rol(k, 3), l[-1])
        return ((s.xor(b, x[0]), s.xor(a, x[1])), (s.xor(d, x[0]), flip(s.xor(c, x[1]), 1 << 62))) if out else (a, b, c, d)


def build(mode, R):
    s = Model()
    pair = lambda: (s.word(), s.word())
    m = [pair(), pair()]
    if mode == "step":
        st = [(pair(), pair())] * 2
        free, ins = dict(m1=m[0], m2=m[1], g=st[0][0], x=st[0][1]), m
    elif mode == "free":
        st = [(pair(), pair()), (pair(), pair())]
        free = dict(m1=m[0], g1=st[0][0], x1=st[0][1], m2=m[1], g2=st[1][0], x2=st[1][1])
        ins = [m[i] + st[i][0] + st[i][1] for i in (0, 1)]
    else:
        # A first chunk makes the state (g, x) that the second chunk starts from.
        c = [pair()]
        c.append(pair() if mode == "hash2" else c[0])
        st = []
        for ch in c[:1 + (mode == "hash2")]:
            h, g = s.step(ch, (const(32), const(0)), (const(IV & 2**64 - 1), const(IV >> 64)), R)
            st.append((g, (flip(h[0], 16), h[1])))
        if len(st) == 1: st *= 2
        free, ins = dict(c1=c[0], c2=c[1], m1=m[0], m2=m[1]), [c[0] + m[0], c[1] + m[1]]
    # Equal step outputs on both sides; from the same g and x that is equal cipher outputs.
    same = st[0] is st[1]
    o = [s.step(mi, g, x, R, not same) for mi, (g, x) in zip(m, st)]
    bits = lambda t: [b for w in (t if same else t[0] + t[1]) for b in w]
    for p, q in zip(bits(o[0]), bits(o[1])): s.cl += [[-p, q], [p, -q]]
    # The inputs differ: each d is true only where they do, and some d is true.
    d = []
    for p, q in zip(*([b for w in i for b in w] for i in ins)):
        if p != q:
            s.n += 1
            d.append(s.n)
            s.cl += [[-s.n, p, q], [-s.n, -p, -q]]
    s.cl.append(d)
    return s, free


def search(mode, R, secs, P):
    s, free = build(mode, R)
    t0, tag = time.time(), f"{mode}-{R}"
    WORK.mkdir(exist_ok=True)
    f = WORK / f"{tag}.cnf"
    f.write_text(f"p cnf {s.n} {len(s.cl)}\n" + "".join(" ".join(map(str, c)) + " 0\n" for c in s.cl))
    # The same problem under P seeds, every other one tuned for problems that have a solution; the first to finish wins.
    jobs = [subprocess.Popen([KISSAT, "-q", f"--seed={i + int(os.environ.get('SEED0', 0))}", f"--time={int(secs)}", *["--sat"][:i % 2], str(f)],
                             stdout=open(WORK / f"{tag}-{i}.out", "w")) for i in range(P)]
    done = None
    while done is None and any(p.poll() is None for p in jobs):
        time.sleep(.2)
        done = next((i for i, p in enumerate(jobs) if p.poll() in (10, 20)), None)
    for p in jobs: p.kill()
    out = dict(mode=mode, R=R, secs=round(time.time() - t0, 1), found=False)
    if done is not None and jobs[done].returncode == 20: out["impossible"] = True
    elif done is not None:
        mod = {int(v) for line in open(WORK / f"{tag}-{done}.out") if line.startswith("v") for v in line[1:].split()}
        val = lambda w: sum((b in mod) << j for j, b in enumerate(w[0] + w[1]))
        v = {k: val(w) for k, w in free.items()}
        if mode in ("step", "free"):
            a, b = ((v[f"m{i}"], v.get(f"g{i}", v.get("g")), v.get(f"x{i}", v.get("x"))) for i in (1, 2))
            ok = a != b and step(*a, R) == step(*b, R)
            out |= dict(found=True, verified=ok, **{k: f"{x:032x}" for k, x in v.items()})
        else:
            a, b = ((v[c] | v[k] << 128).to_bytes(32, "little") for c, k in (("c1", "m1"), ("c2", "m2")))
            out |= dict(found=True, verified=a != b and shx(a, 32, R) == shx(b, 32, R),
                        message1=a.hex(), message2=b.hex(), hash=shx(a, 32, R).hex())
    for g in [f] + [WORK / f"{tag}-{i}.out" for i in range(P)]: g.unlink()
    return out


if __name__ == "__main__":
    a = sys.argv
    print(json.dumps(search(a[1], int(a[2]), float(a[3]) if len(a) > 3 else 600, int(a[4]) if len(a) > 4 else os.cpu_count())))
