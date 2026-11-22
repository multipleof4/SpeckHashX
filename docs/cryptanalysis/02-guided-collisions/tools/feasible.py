"""Whether trails from trails.py can be followed by actual values: by one cipher call of the step, and by both.

    python feasible.py MODE TRAILS [SECONDS]
    python feasible.py ks MODE TRAILS [SECONDS]

MODE step for trails of mode c, free for trails of mode f. TRAILS: a file of trails, one per line,
as trails.py many prints them. For each trail prints whether a pair of inputs exists that collides and
follows the trail's key schedule (key) or the whole trail (all), with one call or with both calls of the step.
true means such a pair exists, false that the solver proved none does, null that it ran out of time.
With ks: whether the key schedule alone can follow the trail, for some pair of keys (m, g).
"""
import json, os, subprocess, sys
import guided as G


def sat(mode, t, fix, calls, secs):
    s, _ = G.build(mode, t, fix, calls)
    G.WORK.mkdir(exist_ok=True)
    f = G.WORK / f"feasible{os.getpid()}.cnf"
    f.write_text(f"p cnf {s.n} {len(s.cl)}\n" + "".join(" ".join(map(str, c)) + " 0\n" for c in s.cl))
    rc = subprocess.run([G.KISSAT, "-q", "-n", f"--time={secs}", str(f)], stdout=subprocess.DEVNULL).returncode
    f.unlink()
    return {10: True, 20: False}.get(rc)


def keysched(mode, t, secs):
    R, h = t["R"], lambda v: [int(w, 16) for w in v]
    tk, tl = h(t["k"]), h(t["l"])
    s = G.Model()
    pair = lambda: (s.word(), s.word())
    g0 = pair()
    ws = []
    for side in range(2):
        m, g = pair(), g0 if mode == "step" else pair()
        k, l = [m[0]], [m[1], g[0], g[1]]
        for i in range(R - 1):
            l.append(G.flip(s.add(k[i], G.ror(l[i], 8)), i))
            k.append(s.xor(G.rol(k[i], 3), l[-1]))
        ws.append((k, l))
    for i in range(R): s.diff(ws[0][0][i], ws[1][0][i], tk[i])
    for i in range(R + 2): s.diff(ws[0][1][i], ws[1][1][i], tl[i])
    G.WORK.mkdir(exist_ok=True)
    f = G.WORK / f"keysched{os.getpid()}.cnf"
    f.write_text(f"p cnf {s.n} {len(s.cl)}\n" + "".join(" ".join(map(str, c)) + " 0\n" for c in s.cl))
    rc = subprocess.run([G.KISSAT, "-q", "-n", f"--time={secs}", str(f)], stdout=subprocess.DEVNULL).returncode
    f.unlink()
    return {10: True, 20: False}.get(rc)


if __name__ == "__main__":
    if sys.argv[1] == "ks":
        mode, secs = sys.argv[2], int(sys.argv[4]) if len(sys.argv) > 4 else 60
        for line in open(sys.argv[3]):
            t = json.loads(line)
            print(json.dumps(dict(R=t["R"], cost=t["cost"], keysched=keysched(mode, t, secs))), flush=True)
        sys.exit()
    mode, secs = sys.argv[1], int(sys.argv[3]) if len(sys.argv) > 3 else 60
    for line in open(sys.argv[2]):
        t = json.loads(line)
        r = {f"{fix}_{c}call": sat(mode, t, fix, c, secs) for fix in ("key", "all") for c in (1, 2)}
        print(json.dumps(dict(R=t["R"], cost=t["cost"], wk=t["wk"], wd=t["wd"], **r)), flush=True)
