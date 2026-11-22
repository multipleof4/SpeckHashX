"""Colliding inputs of the R-round SpeckHashX step, found by SAT with a differential trail as a hint.

    python guided.py MODE TRAIL [FIX] [SECONDS] [JOBS]

MODE step: two chunks with the same step output, from one state (g, x) of the solver's choice.
MODE hash: two 32-byte messages with the same 32-byte hash. They share their first 16 bytes.
    With FIRST=hex in the environment, the first 16 bytes are fixed to that chunk.
MODE free: two step inputs (m, g, x) with the same step output.
TRAIL: a file with one trail from trails.py as JSON: mode c for step and hash, mode f for free.
    The number of rounds is the trail's. Or dm:R:K:L, a message difference of K (low half) and L (high half)
    in hex for R rounds, which goes with FIX in.
FIX: how much of the trail the two inputs must follow.
    all: every word of the key schedule and of both cipher calls (the default)
    key: the words of the key schedule
    in:  the difference of the inputs only

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
                x, y, z = e & 1, e >> 1 & 1, e >> 2
                s.cl.append([-p if x else p, -q if y else q, -c if z else c, r if x ^ y ^ z else -r])
            if j < N - 1:
                d = cy[j + 1]
                s.cl += [[-p, -q, d], [-p, -c, d], [-q, -c, d], [p, q, -d], [p, c, -d], [q, c, -d]]
        return o

    def diff(s, u, v, d):
        """Words u and v differ by exactly d."""
        for j, (p, q) in enumerate(zip(u, v)):
            s.cl += [[p, q], [-p, -q]] if d >> j & 1 else [[-p, q], [p, -q]]

    def step(s, m, g, x, R):
        """m, g, x are (low, high) pairs of words. Returns the new (h, g) and every word on the way:
        k[i] and l[i] as in trails.py, and the states (x, y) of the two cipher calls before each round."""
        k, l = [m[0]], [m[1], g[0], g[1]]
        a, b, c, d = [x[1]], [x[0]], [flip(x[1], 1 << 62)], [x[0]]
        for i in range(R):
            a.append(s.xor(s.add(ror(a[i], 8), b[i]), k[i]))
            b.append(s.xor(rol(b[i], 3), a[-1]))
            c.append(s.xor(s.add(ror(c[i], 8), d[i]), k[i]))
            d.append(s.xor(rol(d[i], 3), c[-1]))
            if i < R - 1:
                l.append(flip(s.add(k[i], ror(l[i], 8)), i))
                k.append(s.xor(rol(k[i], 3), l[-1]))
        out = (s.xor(b[R], x[0]), s.xor(a[R], x[1])), (s.xor(d[R], x[0]), flip(s.xor(c[R], x[1]), 1 << 62))
        return out, dict(k=k, l=l, x=a, y=b, x2=c, y2=d)


def build(mode, t, fix, calls=2):
    """calls=1 asks only for the first cipher call to collide and to follow the trail: a check, not an attack."""
    R, h = t["R"], lambda v: [int(w, 16) for w in v]
    tk, tl, tx, ty = h(t["k"]), h(t["l"]), h(t["x"]), h(t["y"])
    # A trail may give the second call its own path; trails.py's do not.
    tx2, ty2 = h(t.get("x2", t["x"])), h(t.get("y2", t["y"]))
    s = Model()
    pair = lambda: (s.word(), s.word())
    m = [pair(), pair()]
    if mode == "step":
        gx = [pair(), pair()]
        st = [gx, gx]
        free = dict(m1=m[0], m2=m[1], g=gx[0], x=gx[1])
    elif mode == "hash":
        # The shared first chunk makes the state that the two second chunks start from.
        c1 = pair()
        if os.environ.get("FIRST"):
            v = int.from_bytes(bytes.fromhex(os.environ["FIRST"]), "little")
            for w, c in zip(c1[0] + c1[1], const(v & 2**64 - 1) + const(v >> 64)): s.cl.append([w if c > 0 else -w])
        (h1, g1), _ = s.step(c1, (const(32), const(0)), (const(IV & 2**64 - 1), const(IV >> 64)), R)
        st = [(g1, (flip(h1[0], 16), h1[1]))] * 2
        free = dict(c1=c1, m1=m[0], m2=m[1])
    else:
        st = [(pair(), pair()), (pair(), pair())]
        free = dict(m1=m[0], g1=st[0][0], x1=st[0][1], m2=m[1], g2=st[1][0], x2=st[1][1])
    (o1, w1), (o2, w2) = (s.step(mi, g, x, R) for mi, (g, x) in zip(m, st))
    # The step outputs are equal.
    for u, v in zip(*((o[0] + o[1])[:2 * calls] for o in (o1, o2))): s.diff(u, v, 0)
    # The inputs differ as the trail says, and so does every word that FIX names.
    s.diff(m[0][0], m[1][0], tk[0]), s.diff(m[0][1], m[1][1], tl[0])
    if mode == "free":
        for i, d in ((0, tl[1]), (1, tl[2])): s.diff(st[0][0][i], st[1][0][i], d)
        s.diff(st[0][1][0], st[1][1][0], ty[0]), s.diff(st[0][1][1], st[1][1][1], tx[0])
    if fix in ("all", "key"):
        for i in range(1, R): s.diff(w1["k"][i], w2["k"][i], tk[i])
        for i in range(3, R + 2): s.diff(w1["l"][i], w2["l"][i], tl[i])
    if fix == "all":
        for i in range(1, R + 1):
            for a, b in (("x", tx), ("y", ty), ("x2", tx2), ("y2", ty2))[:2 * calls]: s.diff(w1[a][i], w2[a][i], b[i])
    return s, free


def search(mode, t, fix, secs, P):
    s, free = build(mode, t, fix)
    t0, tag = time.time(), f"g{os.getpid()}"
    WORK.mkdir(exist_ok=True)
    f = WORK / f"{tag}.cnf"
    f.write_text(f"p cnf {s.n} {len(s.cl)}\n" + "".join(" ".join(map(str, c)) + " 0\n" for c in s.cl))
    s0 = int(os.environ.get("SEED0", 0))
    # The same problem under P seeds, every other one tuned for problems that have a solution; the first to finish wins.
    jobs = [subprocess.Popen([KISSAT, "-q", f"--seed={i + s0}", f"--time={max(1, int(secs))}", *["--sat"][:i % 2], str(f)],
                             stdout=open(WORK / f"{tag}-{i}.out", "w")) for i in range(P)]
    done = None
    while done is None and any(p.poll() is None for p in jobs):
        time.sleep(.1)
        done = next((i for i, p in enumerate(jobs) if p.poll() in (10, 20)), None)
    for p in jobs: p.kill()
    R = t["R"]
    out = dict(mode=mode, R=R, fix=fix, **{k: t[k] for k in ("cost", "dm") if k in t}, secs=round(time.time() - t0, 1), found=False)
    if mode == "hash" and os.environ.get("FIRST"): out["first"] = os.environ["FIRST"]
    if done is not None and jobs[done].returncode == 20: out["impossible"] = True
    elif done is not None:
        mod = {int(v) for line in open(WORK / f"{tag}-{done}.out") if line.startswith("v") for v in line[1:].split()}
        val = lambda w: sum((b in mod) << j for j, b in enumerate(w[0] + w[1]))
        v = {k: val(w) for k, w in free.items()}
        if mode == "hash":
            a, b = ((v["c1"] | v[k] << 128).to_bytes(32, "little") for k in ("m1", "m2"))
            out |= dict(found=True, verified=a != b and shx(a, 32, R) == shx(b, 32, R),
                        message1=a.hex(), message2=b.hex(), hash=shx(a, 32, R).hex())
        else:
            a, b = ((v[f"m{i}"], v.get(f"g{i}", v.get("g")), v.get(f"x{i}", v.get("x"))) for i in (1, 2))
            out |= dict(found=True, verified=a != b and step(*a, R) == step(*b, R), **{k: f"{x:032x}" for k, x in v.items()})
    for g in [f] + [WORK / f"{tag}-{i}.out" for i in range(P)]: g.unlink(missing_ok=True)
    return out


if __name__ == "__main__":
    a = sys.argv
    if a[2].startswith("dm:"):
        _, R, K, L = a[2].split(":")
        z = ["0" * 16] * (int(R) + 2)
        t = dict(R=int(R), k=[K] + z[:int(R) - 1], l=[L] + z, x=z[:int(R) + 1], y=z[:int(R) + 1], dm=[K, L])
    else: t = json.loads(Path(a[2]).read_text())
    print(json.dumps(search(a[1], t, a[3] if len(a) > 3 else "all", float(a[4]) if len(a) > 4 else 600,
                            int(a[5]) if len(a) > 5 else os.cpu_count())), flush=True)
