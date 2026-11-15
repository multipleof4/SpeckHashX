// Compiles the Rust crate to WebAssembly, inlines it as base64 in wasm.js, and copies the README and LICENSE in.
import { $ } from 'bun'

const t = 'wasm32-unknown-unknown', r = `${import.meta.dir}/..`
await $`cargo rustc --lib --release --crate-type cdylib --target ${t} --features wasm`.cwd(r)
const w = await Bun.file(`${r}/target/${t}/release/speckhashx.wasm`).bytes()
await Bun.write(`${import.meta.dir}/wasm.js`, `export default '${Buffer.from(w).toString('base64')}'\n`)
await Bun.write(`${import.meta.dir}/README.md`, (await Bun.file(`${r}/docs/README.md`).text()).replace('../LICENSE', 'LICENSE'))
await Bun.write(`${import.meta.dir}/LICENSE`, Bun.file(`${r}/LICENSE`))
console.log(`wasm: ${w.length} bytes`)
