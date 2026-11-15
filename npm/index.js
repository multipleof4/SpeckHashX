import b from './wasm.js'

const x = (await WebAssembly.instantiate(Uint8Array.from(atob(b), c => c.charCodeAt(0)))).instance.exports
const S = 65536, p = x.shx_alloc(S), te = new TextEncoder
const mem = (p, n) => new Uint8Array(x.memory.buffer, p, n)
const reg = new FinalizationRegistry(x.shx_drop)

export class Hasher {
  #h
  #n

  constructor(n = 32) {
    if (!Number.isInteger(n) || n < 0 || n > 2 ** 30) throw RangeError('output length must be an integer from 0 to 2^30 bytes')
    reg.register(this, this.#h = x.shx_new(this.#n = n))
  }

  update(d) {
    if (typeof d == 'string') d = te.encode(d)
    else if (ArrayBuffer.isView(d)) d = new Uint8Array(d.buffer, d.byteOffset, d.byteLength)
    else if (d instanceof ArrayBuffer) d = new Uint8Array(d)
    else throw TypeError('data must be a string, ArrayBuffer or typed array')
    for (let i = 0; i < d.length; i += S) {
      const c = d.subarray(i, i + S)
      mem(p, S).set(c)
      x.shx_update(this.#h, p, c.length)
    }
    return this
  }

  digest() {
    const o = x.shx_finalize(this.#h), r = mem(o, this.#n).slice()
    x.shx_free(o, this.#n)
    return r
  }
}

export const hash = (d, n) => new Hasher(n).update(d).digest()
export const hex = (d, n) => Array.from(hash(d, n), v => v.toString(16).padStart(2, '0')).join('')
