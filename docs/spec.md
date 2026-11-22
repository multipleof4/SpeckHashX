<img src="https://vibegif.direct-img.link/octopus/wiggle.webp" width="64" align="right" alt="An octopus wiggling its arms">

# Specification

This page defines SpeckHashX: everything needed to compute it without reading the source.

> **Experimental.** This design is new and has not been reviewed by anyone.

SpeckHashX takes a message of `L` bytes and an output length of `n` bytes, and returns `n` bytes.

## Notation

- A *word* is an unsigned 128-bit integer. A *half* is an unsigned 64-bit integer.
- `lo(w)` and `hi(w)` are the low and high halves of a word: `w = hi(w)·2⁶⁴ + lo(w)`.
- `^` is XOR. `+` on halves is addition modulo 2⁶⁴.
- `rol(x, r)` and `ror(x, r)` rotate a half left and right by `r` bits.
- Bytes and words convert in little-endian order: the first of the 16 bytes holds the lowest 8 bits of the word.
- `‖` joins byte strings.

<img src="https://vibegif.direct-img.link/padlock/unlock.webp" width="64" align="right" alt="A key turning in a padlock">

## The cipher

`E(a, b, v)` is Speck128/256 ([paper](https://eprint.iacr.org/2013/404)): it encrypts the word `v` under the key made of the words `a` and `b`.

```
k, l[0], l[1], l[2] = lo(a), hi(a), lo(b), hi(b)
x, y = hi(v), lo(v)

for i = 0 … 33:
    x = (ror(x, 8) + y) ^ k
    y = rol(y, 3) ^ x
    l[i+3] = (k + ror(l[i], 8)) ^ i
    k = rol(k, 3) ^ l[i+3]

E(a, b, v) = x·2⁶⁴ + y
```

As bytes, the key is the 16 bytes of `a` followed by the 16 bytes of `b`, and the block is the 16 bytes of `v`.
This is the byte order of the [Speck implementation guide](https://nsacyber.github.io/simon-speck/implementations/ImplementationGuide1.1.pdf).
In it, the Speck128/256 test vector from the paper reads:

```
key         000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f
plaintext   706f6f6e65722e20496e2074686f7365
ciphertext  438f189c8db4ee4e3ef5c00504010941
```

<img src="https://vibegif.direct-img.link/clock/tick.webp" width="64" align="right" alt="An alarm clock ticking">

## Constants

| Name | Value |
|---|---|
| `IV` | the 16 ASCII bytes `SHX/904928916087` as a word, `0x3738303631393832393430392f584853` |
| `LAST` | 2¹²⁷ |
| `C` | 2¹²⁶ |

The digits in `IV` are a timestamp of some sort.

## Chunks

Let `q = ⌊L / 16⌋` and `r = L mod 16`. The message becomes `q + 1` chunks of 16 bytes, each read as a word:

- `m[0]` to `m[q-1]` are the first `16·q` bytes of the message, 16 at a time.
- `m[q]`, the last chunk, is the remaining `r` bytes, then `15 - r` zero bytes, then one byte with the value `r`.

There is always a last chunk. When `L` is a multiple of 16 it is 16 zero bytes.

Each chunk has a count, the number of message bytes before it, with `LAST` added on the last chunk:

```
t[j] = 16·j           for j < q
t[q] = 16·q + LAST
```

<img src="https://vibegif.direct-img.link/gear/turn.webp" width="64" align="right" alt="Two gears turning against each other">

## Steps

The state is two words, `h` and `g`. It starts from `IV` and the output length, and takes one step per chunk:

```
h, g = IV, n

for j = 0 … q:
    x = h ^ t[j]
    h, g = E(m[j], g, x) ^ x,  E(m[j], g, x ^ C) ^ x ^ C
```

Both cipher calls of a step use the same key: the `g` in it is the value from before the step.

<img src="https://vibegif.direct-img.link/spring/boing.webp" width="64" align="right" alt="A spring toy stretching up and squashing down">

## Output

The final state is the key, and a block number is the input:

```
block[j] = the 16 bytes of E(h, g, j)        for j = 0, 1, 2, …
hash     = the first n bytes of block[0] ‖ block[1] ‖ block[2] ‖ …
```

With `n = 0` the hash is empty.

## Text

The hash is `n` bytes. Its text in base `r` is defined for `r` from 2 to 36, and for `r = 64`.

### Bases 2 to 36

The bytes are read as one number `v`, big-endian: the first byte holds the highest 8 bits.
`v` is written in base `r`, highest digit first, in the digits `0` to `9` then `a` to `z`.
It gets as many digits as the largest hash of that length, `256ⁿ - 1`, needs, so a smaller `v` starts with zeros:

```
v, m, text = the hash as a number, 256ⁿ - 1, ""

while m > 0:
    text = digit(v mod r) ‖ text
    v, m = ⌊v / r⌋, ⌊m / r⌋
```

- Base 16 is the usual hex: two digits for each byte, in the order of the bytes.
- Every base writes the same number, so the text in one base converts to the text in another, leading zeros aside.
- Base 32 is that number in base 32, not the Base32 of [RFC 4648](https://www.rfc-editor.org/rfc/rfc4648).
- With `n = 0` the text is empty.

The words inside the hash are little-endian; the text is big-endian so that it matches the hex.

### Base 64

Base 64 is `base64url` from section 5 of [RFC 4648](https://www.rfc-editor.org/rfc/rfc4648), with no `=` at the end.

## Limits

- `L` is below 2¹²⁶, so the count never reaches the bits of `C` and `LAST`.
- `n` is below 2¹²⁸, so it fits in `g`.

The limits of the crate and the npm package are in [output-length.md](output-length.md#limits).

## Related constructions

- XORing a cipher call's input into its output is the feed-forward of the Davies–Meyer construction.
- Two such calls under one key, on inputs that differ by a constant, with half of the state in the key next to the message chunk,
  is the compression function of [Hirose's double-block-length construction](https://doi.org/10.1007/11799313_14) (FSE 2006).
  SpeckHashX XORs the count into the input of both calls.
- The output is the cipher in counter mode.

## Reference implementation

Python, written from this page. It reproduces every test vector below and in the crate's tests.

```python
import base64

M = 2**64 - 1
IV = int.from_bytes(b"SHX/904928916087", "little")
LAST, C = 1 << 127, 1 << 126
rol = lambda v, r: (v << r | v >> 64 - r) & M
ror = lambda v, r: rol(v, 64 - r)


def E(a, b, v):
    k, l, x, y = a & M, [a >> 64, b & M, b >> 64], v >> 64, v & M
    for i in range(34):
        x = (ror(x, 8) + y & M) ^ k
        y = rol(y, 3) ^ x
        l.append((k + ror(l[i], 8) & M) ^ i)
        k = rol(k, 3) ^ l[-1]
    return x << 64 | y


def shx(m, n):
    h, g, (q, r) = IV, n, divmod(len(m), 16)
    for j in range(q + 1):
        c = m[16 * j:16 * j + 16]
        if j == q: c = c.ljust(15, b"\0") + bytes([r])
        k, x = int.from_bytes(c, "little"), h ^ 16 * j ^ LAST * (j == q)
        h, g = E(k, g, x) ^ x, E(k, g, x ^ C) ^ x ^ C
    return b"".join(E(h, g, j).to_bytes(16, "little") for j in range(-(-n // 16)))[:n]


def text(h, r):
    if r == 64: return base64.urlsafe_b64encode(h).decode().rstrip("=")
    v, m, o = int.from_bytes(h, "big"), 256 ** len(h) - 1, ""
    while m: v, m, o = v // r, m // r, "0123456789abcdefghijklmnopqrstuvwxyz"[v % r] + o
    return o
```

<img src="https://vibegif.direct-img.link/check/done.webp" width="64" align="right" alt="A check mark drawing itself in a badge">

## Test vectors

Chunks, `h` and `g` are shown as their 16 bytes; `h` and `g` are the state after the step for the chunk above them.

The empty message, `n = 32`:

```
chunk 0  00000000000000000000000000000000   count LAST
h        a16feaa95237f043c4e8d8eca66edeed
g        6c70c50822e7bbb24ec9e06d71929c47

hash     2353e9fb3e8415144a2ba616b57448957d0a72c4003fd759e6bf96e6a3b57317
```

`abc`, `n = 32`:

```
chunk 0  61626300000000000000000000000003   count LAST
h        30a537040c1c520f09908412b9c9b2e5
g        9ec14fdb97954ce81cc4542afd0e3a03

hash     f9d38f0c372695b67d5c06c25421beaede279d9a6da9422cfecfa18e638e96f3
```

The 33 bytes `00 01 02 … 20`, `n = 40`:

```
chunk 0  000102030405060708090a0b0c0d0e0f   count 0
h        9de36bdab0a07b4ca4abc294e8e8e531
g        79254459af53e5edaef867b058fd34bd

chunk 1  101112131415161718191a1b1c1d1e1f   count 16
h        c7ca0083d8c5928b29abc8fe222de5d2
g        bfef48e92833ed6275617f784db8d47c

chunk 2  20000000000000000000000000000001   count 32 + LAST
h        3adda8807352f6863e424d0920d093fc
g        86f3c8ea60891785edaa97f1af989859

hash     b8c0dc3da2049a432cce4b3a4de9674431c283031eb63924a1a74c9f4d78c977a8aabdf8cd9a0ff4
```

As text, the hash of `abc` with `n = 32`:

```
base 10  112999691306956569769269184981788655759217413943854614658490461780486682220275
base 16  f9d38f0c372695b67d5c06c25421beaede279d9a6da9422cfecfa18e638e96f3
base 32  1uejhs63e9klmpulo1m2aggrtbmu4uepkrd988mftjt1hphot5nj
base 36  685qrcbn2jal82oppuwq48513j85gc1pqczm0niqxoyejmijub
base 64  -dOPDDcmlbZ9XAbCVCG-rt4nnZptqUIs_s-hjmOOlvM
```

The hash of the empty message with `n = 32`, which starts with a zero in both bases:

```
base 10  015979212887220042755496585023260168943665753206110443921945613077242631779095
base 36  0vp4xr6nktgf2khkk0szu4la2ak25np163qt437hvy1sj6ls0n
```

The hash of `abc` with `n = 1`, the byte `b3`:

```
base 2   10110011
base 10  179
base 36  4z
base 64  sw
```

More hashes are in the [README](README.md#test-vectors) and in the tests of `src/lib.rs`.
