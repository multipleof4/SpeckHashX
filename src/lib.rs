//! SpeckHashX: a variable-output hash built from Speck128/256.
//! Experimental and unreviewed.

const IV: u128 = u128::from_le_bytes(*b"SHX/904928916087");
/// Set in the running total on the last chunk.
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
    /// Current chunk, zero-filled past the bytes received.
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

    fn step(&mut self, m: u128, f: u128) {
        let x = self.h ^ (self.t | f);
        let [a, b] = enc(m, self.g, [x, x ^ C]);
        (self.h, self.g) = (a ^ x, b ^ x ^ C);
    }

    /// Feeds more message bytes.
    pub fn update(&mut self, mut d: &[u8]) -> &mut Self {
        while !d.is_empty() {
            // Bytes held in `b`. A full chunk waits here until more data shows it is not the last.
            let mut i = if self.t == 0 {
                0
            } else {
                (self.t - 1) as usize % 16 + 1
            };
            if i == 16 {
                self.step(u128::from_le_bytes(self.b), 0);
                (self.b, i) = ([0; 16], 0);
            }
            // Whole chunks that are followed by more data skip the buffer.
            while i == 0 && d.len() > 16 {
                self.t += 16;
                self.step(u128::from_le_bytes(d[..16].try_into().unwrap()), 0);
                d = &d[16..];
            }
            let k = d.len().min(16 - i);
            self.b[i..i + k].copy_from_slice(&d[..k]);
            self.t += k as u128;
            d = &d[k..];
        }
        self
    }

    /// Returns the hash of everything fed so far.
    pub fn finalize(&self) -> Vec<u8> {
        let mut s = self.clone();
        s.step(u128::from_le_bytes(s.b), LAST);
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
                "968bf582a5520b3292b7227175bfad8b2e86e49672651916285c9ffb25039e08",
            ),
            (b"abc", 16, "0ac6581d4663285e152e4093de92f540"),
            (
                b"The quick brown fox jumps over the lazy dog",
                32,
                "d9e735f424a21f47c1f1edad622e07972041b7e258440e8db09edf4065d0930d",
            ),
            (b"abc", 1, "20"),
            (
                b"abc",
                100,
                "1f3e16ba48dbc6de416efd6abedf3708ab825cdbd35758839ddc6e86ea53ba1aa94c50c67cf4d539a12feba39f4d3dfe\
                 d2361f482ab444c52f0c2f1eb5542460a4a80ef0c13015c7e83cb26e208ee6d4d55bcc92cda10d8ccce60c58b573515c\
                 a6584d2d",
            ),
            (
                &[0; 16],
                32,
                "ac92179e83147a72c08987beee6f2d31263fa89a7026b2b6b07e14137ab60c1a",
            ),
            (
                &[0; 17],
                32,
                "9148212d6bdfd432b80a0c3c026f851c5b3c3e86285f60cd0dd21a4d3775acc4",
            ),
            (
                &p[..32],
                32,
                "c888a2d185cb581215e7aaa0f9e6cab970dc05713f8ea89724543da5138bb152",
            ),
            (
                &p[..33],
                64,
                "582b3398042df36e62436ca378ed3f63664a61e6a96018218f27ecb83806a99b\
                 80f0394b65f88aa472b82c26ea254bd2c91e9d335944721dd367fc63fddfadd1",
            ),
            (
                &p,
                32,
                "bbc3edc9f53ad7af85ee7aa474275b4909ea89815ab801b9f7437b490ecb49fe",
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
