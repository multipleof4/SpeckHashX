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
base(&h, 16);             // "f9d38f0c372695b6…", hex
base(&h, 36);             // "685qrcbn2jal82op…"

let mut s = Hasher::new(32);
s.update(b"ab").update(b"c");
assert_eq!(s.finalize(), h);
```

[JavaScript](https://www.npmjs.com/package/speckhashx) (`npm i speckhashx`; works in Node, Bun and browsers):

```js
import { shx, Hasher } from 'speckhashx'

shx('abc')             // the 32 bytes of the hash, a Uint8Array
shx('abc').hex()       // 'f9d38f0c372695b6…'
shx('abc').base(36)    // '685qrcbn2jal82op…'
shx('abc', 16).hex()   // 'dbfecc39d9de1f99…', 16 bytes
shx(bytes, 64)         // 64 bytes
new Hasher(32).update('ab').update('c').digest().base(64)
```

The number after the message is the output length in bytes; in JavaScript it is optional and defaults to 32.

Strings are hashed as UTF-8, and an `ArrayBuffer`, typed array or `DataView` as its bytes;
anything else throws. Hashes of different output lengths are unrelated:
a 16-byte hash is not the start of the 32-byte hash of the same message.

`base` takes 2 to 36, or 64. `hex` is base 16.

## Test vectors

Output is 32 bytes unless noted.

| Message | Hash |
|---|---|
| empty | `2353e9fb3e8415144a2ba616b57448957d0a72c4003fd759e6bf96e6a3b57317` |
| `abc` | `f9d38f0c372695b67d5c06c25421beaede279d9a6da9422cfecfa18e638e96f3` |
| `abc`, 16-byte output | `dbfecc39d9de1f993d00a90030e89294` |
| `The quick brown fox jumps over the lazy dog` | `edb6137d9032d6a8e607754a0a29e18702b578d512d119a9f249f5bb4f6ac353` |
| `abc`, in base 36 | `685qrcbn2jal82oppuwq48513j85gc1pqczm0niqxoyejmijub` |
| `abc`, in base 64 | `-dOPDDcmlbZ9XAbCVCG-rt4nnZptqUIs_s-hjmOOlvM` |

## License

[CC0 1.0](../LICENSE): public domain, the same terms as Speck itself.
