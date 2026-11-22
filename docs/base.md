# Output bases

SpeckHashX gives a hash as bytes. This page explains how those bytes become text in the base you ask for.

## The short version

- **Any base from 2 to 36, and base 64.** Base 16 is hex and base 10 is decimal.
- **Big-endian, as expected.** Every base writes the same number the hex shows.
- **Zero-padded.** In every base, a hash of a given length always gives text of the same length.
- **Fastest: base 64, then 32, 16, 8, 4 and 2.** Every other base is slower and takes a hash of up to 1,024 bytes.

## Asking for a base

JavaScript:

```js
import { shx } from 'speckhashx'

shx('abc').hex()      // 'f9d38f0c372695b6…', the same as .base(16)
shx('abc').base(36)   // '685qrcbn2jal82op…'
shx('abc').base(10)   // '1129996913069565…'
shx('abc').base(64)   // '-dOPDDcmlbZ9XAbC…'
```

Rust:

```rust
use speckhashx::{base, hash};

base(&hash(b"abc", 32), 36); // "685qrcbn2jal82op…"
```

Bases 2 to 36 use the digits `0` to `9`, then `a` to `z`, always lowercase.
Any other base is refused: JavaScript throws a `RangeError` and Rust panics.

## Big-endian, as expected

To write a hash in a base like 10 or 36, its bytes are first read as one big number.
SpeckHashX reads them big-endian: the first byte is the biggest part of the number, the way hex already reads.

So every base from 2 to 36 shows the same number.
Paste the hex into a base converter that handles big numbers and it gives the same decimal or base 36 text,
apart from the zeros at the front.
This is the convention nearly every hash and cryptography tool follows.

Inside, SpeckHashX computes with little-endian words, as BLAKE3 does.
That decides which bytes come out; it does not change how they are written.

## Zero padding

Every base keeps its leading zeros.
The length of the text depends only on the length of the hash and the base, never on the hash itself:

| Base | 16-byte hash | 32-byte hash | 64-byte hash |
|---|---|---|---|
| 2 | 128 characters | 256 | 512 |
| 4 | 64 | 128 | 256 |
| 8 | 43 | 86 | 171 |
| 10 | 39 | 78 | 155 |
| 16 | 32 | 64 | 128 |
| 32 | 26 | 52 | 103 |
| 36 | 25 | 50 | 100 |
| 64 | 22 | 43 | 86 |

The text is as long as the largest hash of that length needs.
A hash that is a smaller number starts with zeros to fill it, as hex has always done with a hash like `0a3f…`.

Decimal shows it most: a 32-byte hash is always 78 digits, and about 86% of them start with `0`,
because the largest 32-byte number only just reaches 78 digits.
A converter prints the same number without those zeros.

## Base 64

Base 64 is URL-safe base64 as in [RFC 4648](https://www.rfc-editor.org/rfc/rfc4648):
the letters, the digits, `-` and `_`, with no `=` at the end.
It packs the bytes in order, three bytes to four characters, so any base64url decoder gives the bytes back.
It follows the same rule as the other bases: its length is fixed, and zero bits at the front show as `A`, its zero digit.

Base 32 is not that kind of encoding: it is the number in base 32, in the digits `0` to `9` and `a` to `v`,
not the Base32 of RFC 4648.

## Speed

Time to write a 32-byte hash as text, fastest first:

| Base | Characters | Rust | JavaScript (Node) |
|---|---|---|---|
| 64 | 43 | 306 nanoseconds | 1,025 nanoseconds |
| 32 | 52 | 461 | 1,361 |
| 16 | 64 | 527 | 1,461 |
| 8 | 86 | 680 | 1,771 |
| 4 | 128 | 915 | 1,956 |
| 2 | 256 | 1,605 | 2,877 |
| 36 | 50 | 2,522 | 4,439 |
| 20 | 60 | 2,591 | 4,753 |
| 10 | 78 | 3,109 | 5,443 |
| 6 | 100 | 3,624 | 6,265 |
| 3 | 162 | 5,376 | 8,565 |

Measured on one machine; other processors differ, but the order stays.
For scale, hashing a short message takes about 250 nanoseconds in Rust on the same machine.

The bases fall into two groups:

- **Bases 2, 4, 8, 16, 32 and 64.** A digit is a whole number of bits, so the text is read straight off the bytes.
  The time grows in step with the length, a larger base is faster because it writes fewer characters,
  and there is no length limit.
- **Every other base.** The whole number has to be divided again and again, so twice the length is four times the work.
  These take a hash of up to 1,024 bytes, which is about 1 millisecond in Rust; base 16 writes the same hash in about 10 microseconds.

In JavaScript, `.hex()` is `.base(16)`.

The exact rules, with test vectors, are in the [specification](spec.md#text).
