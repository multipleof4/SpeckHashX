# Build

```sh
cargo test                              # Rust crate
cd npm && bun run build && bun test     # wasm + npm package
cd site && bun install && bun run build  # the site, which uses the published npm package
```

`npm/build.js` compiles the crate for `wasm32-unknown-unknown` and inlines the result as
base64 in `npm/wasm.js`, so the package has no dependencies and needs no bundler setup.
