"""Runs the experiments of shx.cl on the first GPU found, or on the CPU when there is none.

    python run.py check                  the kernel's step against the reference, at 34 rounds
    python run.py scan R0 R1 LOG2N       bit-flip counts for rounds R0..R1, 2^LOG2N inputs per input bit
    python run.py hunt TRAIL LOG2N [any] 2^LOG2N pairs along a trail from trails.py (a JSON file)
    python run.py pairs NB LOG2N [R]     colliding pairs among the NB-byte hashes of 2^LOG2N messages, R rounds (34)

hunt keeps g and x at the values of a message's first chunk with 32 bytes of output, so a hit is a pair of
16-byte messages with the same hash; with `any`, g and x are random too.
"""
import json, sys, time
from pathlib import Path
import numpy as np, pyopencl as cl

from ref import C, E, IV, M, shx, step


def device():
    ds = [d for p in cl.get_platforms() for d in p.get_devices()]
    return sorted(ds, key=lambda d: d.type != cl.device_type.GPU)[0]


dev = device()
ctx = cl.Context([dev])
q = cl.CommandQueue(ctx)
prg = cl.Program(ctx, (Path(__file__).parent / "shx.cl").read_text()).build()
kscan, khunt, kfull = (cl.Kernel(prg, n) for n in ("scan", "hunt", "full"))
buf = lambda a: cl.Buffer(ctx, cl.mem_flags.READ_WRITE | cl.mem_flags.COPY_HOST_PTR, hostbuf=a)
words = lambda *v: np.array([w for x in v for w in (x & M, x >> 64)], np.uint64)


def read(b, dtype, n):
    a = np.empty(n, dtype)
    cl.enqueue_copy(q, a, b).wait()
    return a


def hunt(R, log2n, dl, tk, tx, ty, base, rmask, follow=1, seed=1):
    """Returns the pairs run, the per-round survivor counts, the number of hits and the first hits."""
    per, items = 1 << 12, 1 << 18
    surv, hits, done, nh = np.zeros(2 * R, object), [], 0, 0
    bs = [buf(np.array(v, np.uint64)) for v in (base, dl, tk, tx, ty)]
    while done < 1 << log2n:
        g = min(items, -(-((1 << log2n) - done) // per))
        sv, hb, nb = buf(np.zeros(2 * R, np.uint32)), buf(np.zeros(96, np.uint64)), buf(np.zeros(1, np.uint32))
        khunt(q, (g,), None, np.uint64(seed + done), np.int32(R), np.int32(per), np.int32(follow), np.uint32(rmask), *bs, sv, hb, nb).wait()
        n = int(read(nb, np.uint32, 1)[0])
        hits += read(hb, np.uint64, 96).reshape(16, 6)[:min(n, 16)].tolist()
        surv, done, nh = surv + read(sv, np.uint32, 2 * R).astype(object), done + g * per, nh + n
    return done, surv, nh, hits


def main(a):
    if a[0] == "check":
        # One 34-round step of a message's first chunk, against the reference.
        m, n = bytes(range(16)), 40
        base, dl, z = words(int.from_bytes(m, "little"), n, IV), np.zeros(6, np.uint64), np.zeros(35, np.uint64)
        _, surv, nh, hits = hunt(34, 0, dl, z, z, z, base, 0)
        ok = shx(b"abc", 32).hex().startswith("f9d38f0c372695b6") and shx(bytes(range(33)), 40).hex().startswith("b8c0dc3da2049a43")
        # With no difference every pair follows the all-zero trail and collides.
        print(dev.name, "| reference vectors", "ok" if ok else "WRONG", "| kernel", "ok" if nh == 4096 and all(surv == 4096) else "WRONG")
        cnt = buf(np.zeros(384 * 256, np.uint32))
        kscan(q, (384,), None, np.uint64(7), np.int32(34), np.int32(1), cnt).wait()
        # The same pseudorandom inputs in Python: the flip of input bit f must flip the same output bits.
        got, bad = read(cnt, np.uint32, 384 * 256).reshape(384, 256), 0
        for f in range(0, 384, 37):
            z, s = (7 ^ (f + 1) * 0xD1342543DE82EF95) & M, []
            for _ in range(6):
                z = (z + 0x9E3779B97F4A7C15) & M
                v = (z ^ z >> 30) * 0xBF58476D1CE4E5B9 & M
                v = (v ^ v >> 27) * 0x94D049BB133111EB & M
                s.append(v ^ v >> 31)
            def out(s):
                m, g, x = (s[2 * i] | s[2 * i + 1] << 64 for i in range(3))
                return E(m, g, x) ^ x | (E(m, g, x ^ C) ^ x ^ C) << 128
            t = list(s)
            t[f >> 6] ^= 1 << (f & 63)
            d = out(s) ^ out(t)
            bad += any(int(got[f, j]) != d >> j & 1 for j in range(256))
        print("scan kernel", "ok" if not bad else "WRONG")
    elif a[0] == "scan":
        N = 1 << int(a[3])
        per = min(N, 1 << 12)
        for R in range(int(a[1]), int(a[2]) + 1):
            t0, tot, done = time.time(), np.zeros(384 * 256, np.uint64), 0
            while done < N:
                g, cnt = min(N - done, 1 << 28) // per, buf(np.zeros(384 * 256, np.uint32))
                kscan(q, (384 * g,), None, np.uint64(R << 40 | done), np.int32(R), np.int32(per), cnt).wait()
                tot, done = tot + read(cnt, np.uint32, 384 * 256), done + g * per
            zs = np.abs((tot.astype(np.float64) - N / 2) / (N / 4) ** .5).reshape(384, 256)
            # 98,304 cells: by chance alone the largest |z| is about 4.5, and above 5.5 about once in 270 runs.
            print(json.dumps(dict(R=R, log2n=int(a[3]), max_z=round(float(zs.max()), 2), cells_over_5_5=int((zs > 5.5).sum()),
                                  never_or_always=int(((tot == 0) | (tot == N)).sum()),
                                  worst_input_bit=int(zs.max(1).argmax()), secs=round(time.time() - t0, 1))), flush=True)
    elif a[0] == "pairs":
        nb, N, R, t0 = int(a[1]), 1 << int(a[2]), int(a[3]) if len(a) > 3 else 34, time.time()
        v, part = np.empty(N, np.uint64), min(N, 1 << 24)
        ob = cl.Buffer(ctx, cl.mem_flags.WRITE_ONLY, 8 * part)
        for i in range(0, N, part):
            kfull(q, (part,), None, np.uint64(i), np.int32(R), np.int32(nb), ob).wait()
            cl.enqueue_copy(q, v[i:i + part], ob).wait()
        # The kernel against the reference, on the first and the last message.
        ok = all(int.from_bytes(shx(i.to_bytes(8, "little"), nb, R), "little") == int(v[i]) for i in (0, 1, N - 1))
        v.sort()
        # Equal neighbours after sorting; a value seen r times makes r - 1 of them in a row, and r(r-1)/2 pairs.
        eq = np.concatenate([np.flatnonzero(v[i + 1:i + part + 1] == v[i:min(i + part, N - 1)]) + i for i in range(0, N - 1, part)])
        runs = np.diff(np.flatnonzero(np.concatenate(([True], np.diff(eq) != 1, [True])))) if len(eq) else np.array([], np.int64)
        pairs = int((runs * (runs + 1) // 2).sum())
        exp = N * (N - 1) / 2 / 256.0**nb
        print(json.dumps(dict(bytes=nb, R=R, messages_log2=int(a[2]), pairs=pairs, expected=round(exp, 1),
                              sd=round(exp**.5, 1), kernel_matches_reference=bool(ok), secs=round(time.time() - t0, 1), device=dev.name)))
    elif a[0] == "hunt":
        t, t0 = json.loads(Path(a[1]).read_text()), time.time()
        R, h = t["R"], lambda v: [int(x, 16) for x in v]
        k, l, x, y = h(t["k"]), h(t["l"]), h(t["x"]), h(t["y"])
        dl = [k[0], l[0], l[1], l[2], y[0], x[0]]
        free = len(a) > 3
        done, surv, nh, hits = hunt(R, int(a[2]), dl, k + [0] * (R - len(k)), x, y, words(0, 32, IV), 63 if free else 3)
        out = dict(R=R, cost=t["cost"], pairs_log2=int(a[2]), hits=nh, secs=round(time.time() - t0, 1), device=dev.name,
                   survivors=[int(v) for v in surv])
        if hits:
            # Recompute the hit with the reference: the two inputs must give the same step output.
            s1 = hits[0]
            ins = [[s1[2 * i] | s1[2 * i + 1] << 64 for i in range(3)], [(s1[2 * i] ^ dl[2 * i]) | (s1[2 * i + 1] ^ dl[2 * i + 1]) << 64 for i in range(3)]]
            o = [step(*i, R) for i in ins]
            out |= dict(verified=o[0] == o[1], input1=[f"{v:032x}" for v in ins[0]], input2=[f"{v:032x}" for v in ins[1]])
            if not free:
                m1, m2 = (v[0].to_bytes(16, "little") for v in ins)
                out |= dict(message1=m1.hex(), message2=m2.hex(), hash1=shx(m1, 32, R).hex(), hash2=shx(m2, 32, R).hex())
        print(json.dumps(out))


if __name__ == "__main__": main(sys.argv[1:])
