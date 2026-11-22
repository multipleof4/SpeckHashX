"""A message with a given R-round SpeckHashX hash, found by SAT.

    python preimage.py R L N [SEED] [SECONDS] [JOBS]

The target is the N-byte, R-round hash of a random L-byte message (L below 16, so one chunk), made from SEED.
The solver is told L and the target, and looks for any L-byte message with that hash.
Brute force takes about 2^(8L) tries when L < N, and 2^(8N) when L >= N.

Every answer is recomputed with ref.py before it is printed.
Needs the kissat binary: set KISSAT or put it on PATH.
"""
import json, os, random, subprocess, sys, time
from pathlib import Path
from ref import IV, LAST, shx

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

    def speck(s, key, v, R):
        """Speck with R rounds under the key words (k, l0, l1, l2) on v = (x, y). Returns (x, y)."""
        k, l = key[0], list(key[1:])
        x, y = v
        for i in range(R):
            x = s.xor(s.add(ror(x, 8), y), k)
            y = s.xor(rol(y, 3), x)
            if i < R - 1:
                l.append(flip(s.add(k, ror(l[i], 8)), i))
                k = s.xor(rol(k, 3), l[-1])
        return x, y


def build(R, L, n, target):
    s = Model()
    m = (s.word(), s.word())
    # The last chunk: the L message bytes, zeros, then the byte L.
    pad = (L << 120)
    for j in range(128):
        if j >= 8 * L: s.cl.append([(m[0] + m[1])[j] if pad >> j & 1 else -(m[0] + m[1])[j]])
    g, x = (const(n & 2**64 - 1), const(n >> 64)), (const(IV & 2**64 - 1), const((IV ^ LAST) >> 64))
    key = (m[0], m[1], g[0], g[1])
    x1, y1 = s.speck(key, (x[1], x[0]), R)
    x2, y2 = s.speck(key, (flip(x[1], 1 << 62), x[0]), R)
    h = (s.xor(y1, x[0]), s.xor(x1, x[1]))
    g = (s.xor(y2, x[0]), flip(s.xor(x2, x[1]), 1 << 62))
    # Output block j is Speck under the key (h, g) on the number j.
    bits = []
    for j in range(-(-n // 16)):
        ox, oy = s.speck((h[0], h[1], g[0], g[1]), (const(0), const(j)), R)
        bits += oy + ox
    t = int.from_bytes(target, "little")
    for j in range(8 * n): s.cl.append([bits[j] if t >> j & 1 else -bits[j]])
    return s, m


def search(R, L, n, seed, secs, P):
    msg = random.Random(seed).randbytes(L)
    target = shx(msg, n, R)
    s, m = build(R, L, n, target)
    t0, tag = time.time(), f"p{os.getpid()}"
    WORK.mkdir(exist_ok=True)
    f = WORK / f"{tag}.cnf"
    f.write_text(f"p cnf {s.n} {len(s.cl)}\n" + "".join(" ".join(map(str, c)) + " 0\n" for c in s.cl))
    jobs = [subprocess.Popen([KISSAT, "-q", f"--seed={i}", f"--time={max(1, int(secs))}", *["--sat"][:i % 2], str(f)],
                             stdout=open(WORK / f"{tag}-{i}.out", "w")) for i in range(P)]
    done = None
    while done is None and any(p.poll() is None for p in jobs):
        time.sleep(.1)
        done = next((i for i, p in enumerate(jobs) if p.poll() in (10, 20)), None)
    for p in jobs: p.kill()
    out = dict(R=R, L=L, bytes=n, seed=seed, target=target.hex(), secs=round(time.time() - t0, 1), found=False)
    if done is not None and jobs[done].returncode == 10:
        mod = {int(v) for line in open(WORK / f"{tag}-{done}.out") if line.startswith("v") for v in line[1:].split()}
        v = sum((b in mod) << j for j, b in enumerate(m[0] + m[1]))
        found = v.to_bytes(16, "little")[:L]
        out |= dict(found=True, verified=shx(found, n, R) == target, message=found.hex(), same_as_secret=found == msg)
    elif done is not None: out["impossible"] = True
    for g in [f] + [WORK / f"{tag}-{i}.out" for i in range(P)]: g.unlink(missing_ok=True)
    return out


if __name__ == "__main__":
    a = sys.argv
    n = lambda i, d: type(d)(a[i]) if len(a) > i else d
    print(json.dumps(search(int(a[1]), int(a[2]), int(a[3]), n(4, 1), n(5, 600.0), n(6, os.cpu_count()))), flush=True)
