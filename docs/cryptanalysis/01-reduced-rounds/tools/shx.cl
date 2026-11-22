// The SpeckHashX step with R Speck rounds instead of 34, and the two experiments run on it.
// An input is 6 words: s[0..1] = m, s[2..3] = g, s[4..5] = x (h ^ count), low half first.
typedef ulong u;
#define ROR8(v) rotate(v, 56UL)
#define ROL3(v) rotate(v, 3UL)
#define C 0x4000000000000000UL  // bit 126 of x is bit 62 of its high half

static u rnd(u *z) {  // splitmix64
    u v = *z += 0x9E3779B97F4A7C15UL;
    v = (v ^ v >> 30) * 0xBF58476D1CE4E5B9UL;
    v = (v ^ v >> 27) * 0x94D049BB133111EBUL;
    return v ^ v >> 31;
}

// o[0..1] = new h, o[2..3] = new g.
static void step(const u *s, int R, u *o) {
    u k = s[0], l0 = s[1], l1 = s[2], l2 = s[3], a = s[5], b = s[4], c = a ^ C, d = b;
    for (int i = 0; i < R; i++) {
        a = (ROR8(a) + b) ^ k, b = ROL3(b) ^ a;
        c = (ROR8(c) + d) ^ k, d = ROL3(d) ^ c;
        u n = (k + ROR8(l0)) ^ (u)i;
        k = ROL3(k) ^ n, l0 = l1, l1 = l2, l2 = n;
    }
    o[0] = b ^ s[4], o[1] = a ^ s[5], o[2] = d ^ s[4], o[3] = c ^ s[5] ^ C;
}

// Work item g flips input bit g % 384 on n random inputs (n < 65536) and adds,
// for each of the 256 output bits, how often it flipped to cnt[384][256].
__kernel void scan(u seed, int R, int n, __global volatile uint *cnt) {
    size_t g = get_global_id(0);
    int f = g % 384;
    u z = seed ^ (g + 1) * 0xD1342543DE82EF95UL, pl[4][16], s[6], p[4], q[4];
    for (int j = 0; j < 64; j++) pl[j >> 4][j & 15] = 0;
    for (int t = 0; t < n; t++) {
        for (int j = 0; j < 6; j++) s[j] = rnd(&z);
        step(s, R, p);
        s[f >> 6] ^= 1UL << (f & 63);
        step(s, R, q);
        // pl[j] is 64 counters of 16 bits, one bit plane per word: add 1 where the outputs differ.
        for (int j = 0; j < 4; j++)
            for (u v = p[j] ^ q[j], i = 0; v; i++) {
                u carry = pl[j][i] & v;
                pl[j][i] ^= v, v = carry;
            }
    }
    for (int j = 0; j < 256; j++) {
        uint c = 0;
        for (int i = 0; i < 16; i++) c |= (uint)(pl[j >> 6][i] >> (j & 63) & 1) << i;
        atomic_add(&cnt[f * 256 + j], c);
    }
}

// Runs n pairs of inputs that differ by dl through the step side by side.
// Word j of an input is random if bit j of rmask is set, else base[j].
// tk[i] is the trail's key difference of round i, tx[i] and ty[i] its state difference before round i.
// With follow set, a pair stops at the first round that leaves the trail, and surv[2i] and surv[2i+1]
// count the pairs whose key and whose state still matched in round i. Without it only the end is checked.
// A pair whose two step outputs are equal is a hit: its first input goes to hits, up to 16 of them.
__kernel void hunt(u seed, int R, int n, int follow, uint rmask, __global const u *base, __global const u *dl,
                   __global const u *tk, __global const u *tx, __global const u *ty,
                   __global volatile uint *surv, __global u *hits, __global volatile uint *nhit) {
    u z = seed ^ (get_global_id(0) + 1) * 0xD1342543DE82EF95UL, s[6];
    uint sv[80];
    for (int i = 0; i < 2 * R; i++) sv[i] = 0;
    for (int t = 0; t < n; t++) {
        for (int j = 0; j < 6; j++) s[j] = rmask >> j & 1 ? rnd(&z) : base[j];
        u k = s[0], l0 = s[1], l1 = s[2], l2 = s[3], a = s[5], b = s[4], c = a ^ C, d = b;
        u K = k ^ dl[0], L0 = l0 ^ dl[1], L1 = l1 ^ dl[2], L2 = l2 ^ dl[3], A = a ^ dl[5], B = b ^ dl[4], Cc = A ^ C, D = B;
        int i = 0;
        for (; i < R; i++) {
            if (follow && (k ^ K) != tk[i]) break;
            sv[2 * i]++;
            a = (ROR8(a) + b) ^ k, b = ROL3(b) ^ a, A = (ROR8(A) + B) ^ K, B = ROL3(B) ^ A;
            c = (ROR8(c) + d) ^ k, d = ROL3(d) ^ c, Cc = (ROR8(Cc) + D) ^ K, D = ROL3(D) ^ Cc;
            if (follow && ((a ^ A) != tx[i + 1] || (b ^ B) != ty[i + 1] || (c ^ Cc) != tx[i + 1] || (d ^ D) != ty[i + 1])) break;
            sv[2 * i + 1]++;
            u n1 = (k + ROR8(l0)) ^ (u)i, n2 = (K + ROR8(L0)) ^ (u)i;
            k = ROL3(k) ^ n1, l0 = l1, l1 = l2, l2 = n1, K = ROL3(K) ^ n2, L0 = L1, L1 = L2, L2 = n2;
        }
        // The feed-forward cancels when the cipher outputs differ by exactly the input difference.
        if (i == R && (a ^ A) == dl[5] && (b ^ B) == dl[4] && (c ^ Cc) == dl[5] && (d ^ D) == dl[4]) {
            uint h = atomic_inc(nhit);
            if (h < 16) for (int j = 0; j < 6; j++) hits[6 * h + j] = s[j];
        }
    }
    for (int i = 0; i < 2 * R; i++) atomic_add(&surv[i], sv[i]);
}

// The whole hash, with R rounds, of the 8-byte message that is the number first + i: out[i] is its first
// nb bytes (nb <= 8) as a number. Such a message is one chunk, the last one, so the hash is one step and one output block.
__kernel void full(u first, int R, int nb, __global u *out) {
    u i = get_global_id(0), s[6] = {first + i, 8UL << 56, (u)nb, 0, 0x393430392f584853UL, 0x3738303631393832UL ^ 1UL << 63}, o[4];
    step(s, R, o);
    // Speck under the key (h, g) on block number 0; the first 8 bytes of the block are its low half.
    u k = o[0], l0 = o[1], l1 = o[2], l2 = o[3], a = 0, b = 0;
    for (int j = 0; j < R; j++) {
        a = (ROR8(a) + b) ^ k, b = ROL3(b) ^ a;
        u n = (k + ROR8(l0)) ^ (u)j;
        k = ROL3(k) ^ n, l0 = l1, l1 = l2, l2 = n;
    }
    out[i] = nb < 8 ? b & ((1UL << 8 * nb) - 1) : b;
}
