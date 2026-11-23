<img src="https://vibegif.direct-img.link/octopus/wiggle.webp" width="64" align="right" alt="An octopus wiggling its arms">

# SpeckHashX

A hash function with any output length, built from the Speck128/256 block cipher.
One Rust source produces both the Rust crate and the WebAssembly npm package.

> **Experimental.** This design is new.

## Use

[Rust](https://crates.io/crates/speckhashx) (`cargo add speckhashx`):

```rust
use speckhashx::{Hasher, base, hash};

let h = hash(b"abc", 32); // Vec<u8> of 32 bytes
base(&h, 16);             // "F9D38F0C372695B6…", hex
base(&h, 62);             // "xEySOeSw03P6yQX1…"

let mut s = Hasher::new(32);
s.update(b"ab").update(b"c");
assert_eq!(s.finalize(), h);
```

[JavaScript](https://www.npmjs.com/package/speckhashx) (`npm i speckhashx`; works in Node, Bun and browsers):

```js
import { shx, Hasher } from 'speckhashx'

shx('abc')             // the 32 bytes of the hash, a Uint8Array
shx('abc').hex()       // 'F9D38F0C372695B6…'
shx('abc').base(62)    // 'xEySOeSw03P6yQX1…'
shx('abc', 16).hex()   // 'DBFECC39D9DE1F99…', 16 bytes
shx(bytes, 64)         // 64 bytes
new Hasher(32).update('ab').update('c').digest().base(64)
```

The number after the message is the output length in bytes; in JavaScript it is optional and defaults to 32.

Strings are hashed as UTF-8, and an `ArrayBuffer`, typed array or `DataView` as its bytes;
anything else throws. Hashes of different output lengths are unrelated:
a 16-byte hash is not the start of the 32-byte hash of the same message.

`base` takes 2 to 62, or 64. `hex` is base 16.

## Test vectors

Output is 32 bytes unless noted.

| Message | Hash |
|---|---|
| empty | `2353E9FB3E8415144A2BA616B57448957D0A72C4003FD759E6BF96E6A3B57317` |
| `abc` | `F9D38F0C372695B67D5C06C25421BEAEDE279D9A6DA9422CFECFA18E638E96F3` |
| `abc`, 16-byte output | `DBFECC39D9DE1F993D00A90030E89294` |
| `The quick brown fox jumps over the lazy dog` | `EDB6137D9032D6A8E607754A0A29E18702B578D512D119A9F249F5BB4F6AC353` |
| `abc`, in base 36 | `685QRCBN2JAL82OPPUWQ48513J85GC1PQCZM0NIQXOYEJMIJUB` |
| `abc`, in base 62 | `xEySOeSw03P6yQX1jTkBhtsGxk21oAxPxH4xCtxpHGN` |
| `abc`, in base 64 | `-dOPDDcmlbZ9XAbCVCG-rt4nnZptqUIs_s-hjmOOlvM` |

## Docs

- [Specification](https://github.com/multipleof4/SpeckHashX/blob/main/docs/spec.md)
- [Output bases](https://github.com/multipleof4/SpeckHashX/blob/main/docs/base.md)
- [Output length and security](https://github.com/multipleof4/SpeckHashX/blob/main/docs/output-length.md)
- [Cryptanalysis](https://github.com/multipleof4/SpeckHashX/blob/main/docs/cryptanalysis/README.md)
- [Build](https://github.com/multipleof4/SpeckHashX/blob/main/docs/build.md)

## License

[CC0 1.0](../LICENSE): public domain, the same terms as Speck itself.
