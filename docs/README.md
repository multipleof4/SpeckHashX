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

hex('abc')        // 'f9d38f0c372695b6…', 32 bytes by default
hash(bytes, 64)   // Uint8Array of 64 bytes
new Hasher(32).update('ab').update('c').digest()
```

Strings are hashed as UTF-8, and an `ArrayBuffer`, typed array or `DataView` as its bytes;
anything else throws. Hashes of different output lengths are unrelated:
a 16-byte hash is not the start of the 32-byte hash of the same message.

## Test vectors

Output is 32 bytes unless noted.

| Message | Hash |
|---|---|
| empty | `2353e9fb3e8415144a2ba616b57448957d0a72c4003fd759e6bf96e6a3b57317` |
| `abc` | `f9d38f0c372695b67d5c06c25421beaede279d9a6da9422cfecfa18e638e96f3` |
| `abc`, 16-byte output | `dbfecc39d9de1f993d00a90030e89294` |
| `The quick brown fox jumps over the lazy dog` | `edb6137d9032d6a8e607754a0a29e18702b578d512d119a9f249f5bb4f6ac353` |

## Build

```sh
cargo test                              # Rust crate
cd npm && bun run build && bun test     # wasm + npm package
cd site && bun install && bun run build  # the site, which uses the published npm package
```

`npm/build.js` compiles the crate for `wasm32-unknown-unknown` and inlines the result as
base64 in `npm/wasm.js`, so the package has no dependencies and needs no bundler setup.

## License

[CC0 1.0](../LICENSE): public domain, the same terms as Speck itself.
