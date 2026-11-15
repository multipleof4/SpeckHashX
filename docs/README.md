# SpeckHashX

A hash function with any output length, built from the Speck128/256 block cipher.
One Rust source produces both the Rust crate and the WebAssembly npm package.

> **Experimental.** This design is new and has not been reviewed by anyone.

## Use

Rust (`cargo add speckhashx`):

```rust
let h = speckhashx::hash(b"abc", 32); // Vec<u8> of 32 bytes

let mut s = speckhashx::Hasher::new(32);
s.update(b"ab").update(b"c");
assert_eq!(s.finalize(), h);
```

JavaScript (`npm i speckhashx`; works in Node, Bun and browsers):

```js
import { hash, hex, Hasher } from 'speckhashx'

hex('abc')        // '968bf582a5520b32…', 32 bytes by default
hash(bytes, 64)   // Uint8Array of 64 bytes
new Hasher(32).update('ab').update('c').digest()
```

Strings are hashed as UTF-8. Hashes of different output lengths are unrelated:
a 16-byte hash is not the start of the 32-byte hash of the same message.

## Test vectors

Output is 32 bytes unless noted.

| Message | Hash |
|---|---|
| empty | `2353e9fb3e8415144a2ba616b57448957d0a72c4003fd759e6bf96e6a3b57317` |
| `abc` | `968bf582a5520b3292b7227175bfad8b2e86e49672651916285c9ffb25039e08` |
| `abc`, 16-byte output | `0ac6581d4663285e152e4093de92f540` |
| `The quick brown fox jumps over the lazy dog` | `d9e735f424a21f47c1f1edad622e07972041b7e258440e8db09edf4065d0930d` |

## Build

```sh
cargo test                              # Rust crate
cd npm && bun run build && bun test     # wasm + npm package
```

`npm/build.js` compiles the crate for `wasm32-unknown-unknown` and inlines the result as
base64 in `npm/wasm.js`, so the package has no dependencies and needs no bundler setup.

## License

[CC0 1.0](../LICENSE): public domain, the same terms as Speck itself.
