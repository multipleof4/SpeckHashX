//! SpeckHashX: a variable-output hash built from Speck128/256.
//! Experimental and unreviewed.

const IV: u128 = u128::from_le_bytes(*b"SHX/904928916087");
/// Set in the count of earlier bytes on the last chunk.
const LAST: u128 = 1 << 127;
/// Separates the second cipher call of a step from the first.
const C: u128 = 1 << 126;

/// Speck128/256 encryption of `N` blocks under the 32-byte key `a ‖ b`.
/// The key schedule runs in the same loop, so `k` is the key of round `i`.
fn enc<const N: usize>(a: u128, b: u128, v: [u128; N]) -> [u128; N] {
    let (mut k, mut l) = (a as u64, [(a >> 64) as u64, b as u64, (b >> 64) as u64]);
    let mut s = v.map(|v| ((v >> 64) as u64, v as u64));
    for i in 0..34u64 {
        for (x, y) in &mut s {
            *x = x.rotate_right(8).wrapping_add(*y) ^ k;
            *y = y.rotate_left(3) ^ *x;
        }
        let n = k.wrapping_add(l[0].rotate_right(8)) ^ i;
        (k, l) = (k.rotate_left(3) ^ n, [l[1], l[2], n]);
    }
    s.map(|(x, y)| (x as u128) << 64 | y as u128)
}

/// Streaming hasher. `finalize` does not consume it, so more data can follow.
#[derive(Clone)]
pub struct Hasher {
    h: u128,
    g: u128,
    /// Total message bytes received.
    t: u128,
    /// The `t % 16` bytes not yet stepped, zero-filled.
    b: [u8; 16],
    n: usize,
}

impl Hasher {
    /// Starts a hash whose output will be `n` bytes long.
    pub fn new(n: usize) -> Self {
        Self {
            h: IV,
            g: n as u128,
            t: 0,
            b: [0; 16],
            n,
        }
    }

    /// Mixes in chunk `m`; `t` is the message bytes before it, with `LAST` set on the last chunk.
    fn step(&mut self, m: u128, t: u128) {
        let x = self.h ^ t;
        let [a, b] = enc(m, self.g, [x, x ^ C]);
        (self.h, self.g) = (a ^ x, b ^ x ^ C);
    }

    /// Feeds more message bytes.
    pub fn update(&mut self, mut d: &[u8]) -> &mut Self {
        while !d.is_empty() {
            let i = self.t as usize % 16;
            // Whole chunks skip the buffer.
            while i == 0 && d.len() >= 16 {
                self.step(u128::from_le_bytes(d[..16].try_into().unwrap()), self.t);
                (self.t, d) = (self.t + 16, &d[16..]);
            }
            let k = d.len().min(16 - i);
            self.b[i..i + k].copy_from_slice(&d[..k]);
            (self.t, d) = (self.t + k as u128, &d[k..]);
            if i + k == 16 {
                self.step(u128::from_le_bytes(self.b), self.t - 16);
                self.b = [0; 16];
            }
        }
        self
    }

    /// Returns the hash of everything fed so far.
    pub fn finalize(&self) -> Vec<u8> {
        // The last chunk is the 0 to 15 bytes left over; its final byte says how many.
        let (mut s, i) = (self.clone(), self.t % 16);
        s.b[15] = i as u8;
        s.step(u128::from_le_bytes(s.b), (s.t - i) | LAST);
        let mut o = vec![0; s.n];
        for (j, c) in o.chunks_mut(64).enumerate() {
            let v = enc(
                s.h,
                s.g,
                core::array::from_fn::<_, 4, _>(|i| (4 * j + i) as u128),
            );
            for (c, v) in c.chunks_mut(16).zip(v) {
                c.copy_from_slice(&v.to_le_bytes()[..c.len()]);
            }
        }
        o
    }
}

/// Hashes `m` to `n` bytes.
pub fn hash(m: &[u8], n: usize) -> Vec<u8> {
    Hasher::new(n).update(m).finalize()
}

#[cfg(feature = "wasm")]
mod wasm {
    use super::Hasher;
    use std::slice;

    #[unsafe(no_mangle)]
    extern "C" fn shx_alloc(n: usize) -> *mut u8 {
        Box::into_raw(vec![0u8; n].into_boxed_slice()) as _
    }

    #[unsafe(no_mangle)]
    unsafe extern "C" fn shx_free(p: *mut u8, n: usize) {
        drop(unsafe { Box::from_raw(std::ptr::slice_from_raw_parts_mut(p, n)) })
    }

    #[unsafe(no_mangle)]
    extern "C" fn shx_new(n: usize) -> *mut Hasher {
        Box::into_raw(Box::new(Hasher::new(n)))
    }

    #[unsafe(no_mangle)]
    unsafe extern "C" fn shx_update(h: *mut Hasher, p: *const u8, n: usize) {
        unsafe { (*h).update(slice::from_raw_parts(p, n)) };
    }

    /// Returns `n` output bytes; release them with `shx_free`.
    #[unsafe(no_mangle)]
    unsafe extern "C" fn shx_finalize(h: *const Hasher) -> *mut u8 {
        Box::into_raw(unsafe { &*h }.finalize().into_boxed_slice()) as _
    }

    #[unsafe(no_mangle)]
    unsafe extern "C" fn shx_drop(h: *mut Hasher) {
        drop(unsafe { Box::from_raw(h) })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn hex(b: &[u8]) -> String {
        b.iter().map(|v| format!("{v:02x}")).collect()
    }

    /// Test vector from the Speck paper, in the byte order of the Speck implementation guide.
    #[test]
    fn speck128_256() {
        let k: [u8; 32] = core::array::from_fn(|i| i as u8);
        let [a, b] = [&k[..16], &k[16..]].map(|v| u128::from_le_bytes(v.try_into().unwrap()));
        let c = enc(a, b, [u128::from_le_bytes(*b"pooner. In those")])[0];
        assert_eq!(hex(&c.to_le_bytes()), "438f189c8db4ee4e3ef5c00504010941");
    }

    /// Answers from an independent Python implementation of the same design.
    #[test]
    fn known_answers() {
        let p: Vec<u8> = (0..1000).map(|i| (i * 7 % 251) as u8).collect();
        for (m, n, o) in [
            (
                &b""[..],
                32,
                "2353e9fb3e8415144a2ba616b57448957d0a72c4003fd759e6bf96e6a3b57317",
            ),
            (
                b"abc",
                32,
                "f9d38f0c372695b67d5c06c25421beaede279d9a6da9422cfecfa18e638e96f3",
            ),
            (b"abc", 16, "dbfecc39d9de1f993d00a90030e89294"),
            (
                b"The quick brown fox jumps over the lazy dog",
                32,
                "edb6137d9032d6a8e607754a0a29e18702b578d512d119a9f249f5bb4f6ac353",
            ),
            (b"abc", 1, "b3"),
            (
                b"abc",
                100,
                "7a41bdac404270a33a1f3c45f868f67dc3dba424aa723eec919f414f89d6d04491b61a19876240db1cb5689f899379e1\
                 6540aad99d5239df6c78e79a9f62385f99990fa0f238cf3e32f8d4e4f9018c9466626cae2a38066f33bb27ece2261444\
                 11026525",
            ),
            (
                &[0; 16],
                32,
                "bd4938adba89371630c40ed5ade8ea29f4c1c366c0f26ea17a6dac4074e4cbad",
            ),
            (
                &[0; 17],
                32,
                "8424162ee390487cdb4e6e468a923363ea63bb89ea37b254b73bf227eae7fb4f",
            ),
            (
                &p[..32],
                32,
                "1260b1178d37c0d9477cd98d710c9e8ba0ce350786af0f8211a15a1991559ee2",
            ),
            (
                &p[..33],
                64,
                "e3a90c0dce6d78767691510c890a40cf2e2ce8933729baf072f1ed3e7bfcd523\
                 45b9a8d1b2b0c7089405e5921ff9b8102150844d8a84cac92857eff650982d44",
            ),
            (
                &p,
                32,
                "8a0d7524c6ee6ef86b6cfd7de2727ede7b74dc8c32430626c892b20380ad5427",
            ),
        ] {
            assert_eq!(hex(&hash(m, n)), o, "{} bytes -> {n}", m.len());
        }
    }

    #[test]
    fn streaming_matches_one_shot() {
        let m: Vec<u8> = (0..80).collect();
        for l in 0..=m.len() {
            for a in 0..=l {
                for b in [a, (a + 16).min(l), l] {
                    let mut s = Hasher::new(32);
                    s.update(&m[..a]).update(&m[a..b]).update(&m[b..l]);
                    assert_eq!(s.finalize(), hash(&m[..l], 32), "{l} {a} {b}");
                }
            }
        }
    }

    #[test]
    fn finalize_can_be_followed_by_more_data() {
        let mut s = Hasher::new(32);
        assert_eq!(s.update(b"ab").finalize(), hash(b"ab", 32));
        assert_eq!(s.update(b"c").finalize(), hash(b"abc", 32));
    }

    #[test]
    fn inputs_and_lengths_are_separated() {
        assert_ne!(hash(b"abc", 32), hash(b"abc\0", 32));
        assert_ne!(hash(&[0; 16], 32), hash(&[0; 32], 32));
        assert_ne!(hash(b"", 32), hash(&[0], 32));
        assert_ne!(hash(b"abc", 16), hash(b"abc", 32)[..16]);
        assert_eq!(hash(b"abc", 0), []);
    }
}
