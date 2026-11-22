"""Chosen-key XOR-differential trails of the R-round SpeckHashX step, found by SAT.

    python trails.py MODE R [SECONDS] [JOBS]
    python trails.py many MODE R BOUND [COUNT] [SECONDS] [JOBS]

MODE c: the two inputs differ in the message chunk only and the step outputs collide.
MODE f: the two inputs may differ anywhere (free start) and the step outputs collide.
MODE s: no key difference and any output difference, to check the model against published weights.

A trail costs wk + 2*wd: wk for the key schedule, wd for one cipher call, and a step has two.
Prints the cheapest trail found as JSON, with the cost below which none exists,
or "exists": false when no trail exists at any cost.
With many: prints, one per line, up to COUNT trails that cost at most BOUND, no two with the same key schedule.
With EXACT=1 in the environment, the key schedule is also computed on actual values for both inputs,
so every trail found has a key schedule that some pair of keys follows (for modes c and f).
Needs the kissat binary: set KISSAT or put it on PATH.
"""
import json, os, subprocess, sys, time
from pathlib import Path
from pysat.card import CardEnc, EncType

N = 64
KISSAT = os.environ.get("KISSAT", "kissat")
WORK = Path(os.environ.get("WORK", Path(__file__).parent / ".work"))


def rol(v, r): return [v[(j - r) % N] for j in range(N)]
def ror(v, r): return rol(v, N - r)


class Model:
    def __init__(s, R, mode):
        s.n, s.cl = 0, []
        W = s.word
        # Key schedule: k[i] is the key of round i, l[i+3] the sum made in round i.
        s.k, s.l, s.wk = [W()], [W(), W(), W()], []
        for i in range(R - 1):
            c, w = s.add(s.k[i], ror(s.l[i], 8))
            s.l.append(c), s.wk.extend(w), s.k.append(s.xor(rol(s.k[i], 3), c))
        # One cipher call: (x[i], y[i]) is the state before round i.
        s.x, s.y, s.wd = [W()], [W()], []
        for i in range(R):
            c, w = s.add(ror(s.x[i], 8), s.y[i])
            s.wd.extend(w), s.x.append(s.xor(c, s.k[i])), s.y.append(s.xor(rol(s.y[i], 3), s.x[-1]))
        if mode == "c":
            s.cl += [[-b] for v in (s.l[1], s.l[2], s.x[0], s.y[0], s.x[R], s.y[R]) for b in v]
            s.cl.append(s.k[0] + s.l[0])
        elif mode == "s":
            s.cl += [[-b] for v in [s.k[0]] + s.l[:3] for b in v]
            s.cl.append(s.x[0] + s.y[0])
        else:
            # The feed-forward cancels when the output difference equals the input difference.
            s.cl += [c for p, q in zip(s.x[0] + s.y[0], s.x[R] + s.y[R]) for c in ([-p, q], [p, -q])]
            s.cl.append(s.k[0] + s.l[0] + s.l[1] + s.l[2] + s.x[0] + s.y[0])
        if os.environ.get("EXACT") and mode in ("c", "f"): s.exact(R, mode)
        # Data bits count twice: each copy is forced true whenever the original is.
        dup = [v for _ in range(-(-len(s.wd) // N)) for v in s.word()][:len(s.wd)]
        s.cl += [[-a, d] for a, d in zip(s.wd, dup)]
        s.cost = s.wk + s.wd + dup

    def exact(s, R, mode):
        """Ties the key schedule differences to two key schedules computed on values."""
        sides = []
        for side in range(2):
            m = [s.word(), s.word()]
            g = sides[0][2] if mode == "c" and sides else [s.word(), s.word()]
            k, l = [m[0]], [m[1]] + g
            for i in range(R - 1):
                l.append([-b if i >> j & 1 else b for j, b in enumerate(s.vadd(k[i], ror(l[i], 8)))])
                k.append(s.xor(rol(k[i], 3), l[-1]))
            sides.append((k, l, g))
        for (a, b), d in zip(zip(sides[0][0] + sides[0][1], sides[1][0] + sides[1][1]), s.k + s.l):
            for p, q, r in zip(a, b, d): s.cl += [[-p, -q, -r], [-p, q, r], [p, -q, r], [p, q, -r]]

    def vadd(s, a, b):
        """a + b mod 2^64 on values, bit by bit with a carry."""
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

    def word(s):
        s.n += N
        return list(range(s.n - N + 1, s.n + 1))

    def xor(s, a, b):
        c = s.word()
        for p, q, r in zip(a, b, c):
            s.cl += [[-p, -q, -r], [-p, q, r], [p, -q, r], [p, q, -r]]
        return c

    def add(s, a, b):
        """Sum difference c of a + b (Lipmaa-Moriai), and the bits that cost a factor 2."""
        c, w = s.word(), s.word()[:N - 1]
        s.cl += [[-a[0], -b[0], -c[0]], [-a[0], b[0], c[0]], [a[0], -b[0], c[0]], [a[0], b[0], -c[0]]]
        for j in range(N - 1):
            p, q, r, u, v, t = a[j], b[j], c[j], a[j + 1], b[j + 1], c[j + 1]
            # Not all equal at bit j costs w[j]; all equal at bit j fixes the parity of bit j + 1.
            s.cl += [[w[j], -p, q], [w[j], -q, r], [w[j], -r, p]]
            for e in range(8):
                g = [u if e & 1 else -u, v if e & 2 else -v, t if e & 4 else -t]
                # g is false only on the assignment ~e, whose parity is the opposite of e's.
                s.cl.append(([-p, -q, -r] if bin(e).count("1") & 1 else [p, q, r]) + g)
        return c, w

    def launch(s, tag, bound, secs):
        """Starts kissat on 'cost <= bound'."""
        card = CardEnc.atmost(s.cost, bound, top_id=s.n, encoding=EncType.seqcounter).clauses if bound < len(s.cost) else []
        cl = s.cl + card
        nv = max(s.n, max((abs(x) for c in card for x in c), default=0))
        WORK.mkdir(exist_ok=True)
        f = WORK / f"{tag}-{bound}.cnf"
        f.write_text(f"p cnf {nv} {len(cl)}\n" + "".join(" ".join(map(str, c)) + " 0\n" for c in cl))
        out = open(f.with_suffix(".out"), "w")
        return subprocess.Popen([KISSAT, "-q", f"--time={max(1, int(secs))}", str(f)], stdout=out, stderr=out)

    def read(s, tag, bound, R, mode, path=None):
        mod = set()
        for line in open(path or WORK / f"{tag}-{bound}.out"):
            if line.startswith("v"): mod.update(int(x) for x in line[1:].split())
        s.mod = mod
        val = lambda v: f"{sum((b in mod) << j for j, b in enumerate(v)):016x}"
        wk, wd = (sum(b in mod for b in ws) for ws in (s.wk, s.wd))
        return dict(R=R, mode=mode, wk=wk, wd=wd, cost=wk + 2 * wd,
                    k=[*map(val, s.k)], l=[*map(val, s.l)], x=[*map(val, s.x)], y=[*map(val, s.y)])


def search(R, mode, secs, P):
    """Narrows [lo, hi): no trail costs less than lo, the best found costs hi. Probes P bounds at once."""
    m, t0, tag = Model(R, mode), time.time(), f"{mode}{R}"
    lo, hi, best, jobs = 0, len(m.cost) + 1, None, {}
    left = lambda: secs - (time.time() - t0)
    while lo < hi and left() > 0:
        # Spread the probes over the open range, its two ends first.
        for b in sorted({lo + (hi - 1 - lo) * i // max(1, P - 1) for i in range(P)}, key=lambda b: min(b - lo, hi - b)):
            if len(jobs) < P and b not in jobs: jobs[b] = m.launch(tag, b, left())
        time.sleep(.05)
        for b, p in list(jobs.items()):
            if (rc := p.poll()) is None: continue
            del jobs[b]
            if rc == 20: lo = max(lo, b + 1)
            elif rc == 10 and (t := m.read(tag, b, R, mode))["cost"] < hi: best, hi = t, t["cost"]
        for b in [b for b in jobs if b < lo or b >= hi]: jobs.pop(b).kill()
    for p in jobs.values(): p.kill()
    for f in WORK.glob(f"{tag}-*"): f.unlink()
    if not best and lo >= hi: return dict(R=R, mode=mode, exists=False, secs=round(time.time() - t0, 1))
    return dict(best or dict(R=R, mode=mode), no_trail_below=lo, minimal=lo >= hi, secs=round(time.time() - t0, 1))


def many(R, mode, bound, count, secs, P):
    """Trails of cost at most bound, each with a key schedule unlike the ones before. P seeds race on each."""
    m, t0, tag, n = Model(R, mode), time.time(), f"{mode}{R}m{os.getpid()}", 0
    card = CardEnc.atmost(m.cost, bound, top_id=m.n, encoding=EncType.seqcounter).clauses
    nv = max(m.n, max(abs(x) for c in card for x in c))
    keys, block = [b for v in m.k + m.l for b in v], []
    WORK.mkdir(exist_ok=True)
    f = WORK / f"{tag}.cnf"
    while n < count and (left := secs - (time.time() - t0)) > 1:
        cl = m.cl + card + block
        f.write_text(f"p cnf {nv} {len(cl)}\n" + "".join(" ".join(map(str, c)) + " 0\n" for c in cl))
        jobs = [subprocess.Popen([KISSAT, "-q", f"--seed={i}", f"--time={max(1, int(left))}", *["--sat"][:i % 2], str(f)],
                                 stdout=open(WORK / f"{tag}-{i}.out", "w")) for i in range(P)]
        done = None
        while done is None and any(p.poll() is None for p in jobs):
            time.sleep(.05)
            done = next((i for i, p in enumerate(jobs) if p.poll() in (10, 20)), None)
        for p in jobs: p.kill()
        if done is None or jobs[done].returncode != 10: break
        t = m.read(tag, 0, R, mode, WORK / f"{tag}-{done}.out")
        print(json.dumps(t | dict(secs=round(time.time() - t0, 1))), flush=True)
        n += 1
        block.append([-b if b in m.mod else b for b in keys])
    for g in WORK.glob(f"{tag}*"): g.unlink()


if __name__ == "__main__":
    a = sys.argv
    if a[1] == "many":
        n = lambda i, d: type(d)(a[i]) if len(a) > i else d
        many(int(a[3]), a[2], int(a[4]), n(5, 10**9), n(6, 600.0), n(7, os.cpu_count()))
    else:
        print(json.dumps(search(int(a[2]), a[1], float(a[3]) if len(a) > 3 else 600, int(a[4]) if len(a) > 4 else os.cpu_count())))
