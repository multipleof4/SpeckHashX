"""SpeckHashX as in docs/spec.md, with the number of Speck rounds R as a parameter (34 is the real hash)."""
M = 2**64 - 1
IV = int.from_bytes(b"SHX/904928916087", "little")
LAST, C = 1 << 127, 1 << 126
rol = lambda v, r: (v << r | v >> 64 - r) & M
ror = lambda v, r: rol(v, 64 - r)


def E(a, b, v, R=34):
    k, l, x, y = a & M, [a >> 64, b & M, b >> 64], v >> 64, v & M
    for i in range(R):
        x = (ror(x, 8) + y & M) ^ k
        y = rol(y, 3) ^ x
        l.append((k + ror(l[i], 8) & M) ^ i)
        k = rol(k, 3) ^ l[-1]
    return x << 64 | y


def step(m, g, x, R=34):
    """One step: chunk m, state half g, and x = h ^ count. Returns the new (h, g)."""
    return E(m, g, x, R) ^ x, E(m, g, x ^ C, R) ^ x ^ C


def shx(m, n, R=34):
    h, g, (q, r) = IV, n, divmod(len(m), 16)
    for j in range(q + 1):
        c = m[16 * j:16 * j + 16]
        if j == q: c = c.ljust(15, b"\0") + bytes([r])
        h, g = step(int.from_bytes(c, "little"), g, h ^ 16 * j ^ LAST * (j == q), R)
    return b"".join(E(h, g, j, R).to_bytes(16, "little") for j in range(-(-n // 16)))[:n]


if __name__ == "__main__":
    import sys
    # python ref.py HEX_MESSAGE [BYTES] [ROUNDS]
    a = sys.argv
    print(shx(bytes.fromhex(a[1]), int(a[2]) if len(a) > 2 else 32, int(a[3]) if len(a) > 3 else 34).hex())
