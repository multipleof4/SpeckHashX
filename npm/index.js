import b from './wasm.js'

const x = (await WebAssembly.instantiate(Uint8Array.from(atob(b), c => c.charCodeAt(0)))).instance.exports
const S = 65536, p = x.shx_alloc(S), te = new TextEncoder, td = new TextDecoder
const mem = (p, n) => new Uint8Array(x.memory.buffer, p, n)
const reg = new FinalizationRegistry(x.shx_drop)

// The bytes of a hash, with methods that give them as text.
class Hash extends Uint8Array {
  base(r) {
    const n = this.length
    if (!Number.isInteger(r) || r != 64 && (r < 2 || r > 62)) throw RangeError('base must be an integer from 2 to 62, or 64')
    if (r & r - 1 && n > 1024) throw RangeError('bases other than 2, 4, 8, 16, 32 and 64 take at most 1024 bytes')
    const i = x.shx_alloc(n)
    mem(i, n).set(this)
    const o = x.shx_base(i, n, r), l = new DataView(x.memory.buffer).getUint32(o, true), s = td.decode(mem(o + 4, l))
    x.shx_free(i, n)
    x.shx_free(o, l + 4)
    return s
  }

  hex() {
    return this.base(16)
  }
}

// A new hasher in wasm memory for an output of `n` bytes.
const make = n => {
  if (!Number.isInteger(n) || n < 0 || n > 2 ** 30) throw RangeError('output length must be an integer from 0 to 2^30 bytes')
  return x.shx_new(n)
}

const feed = (h, d) => {
  if (typeof d == 'string') d = te.encode(d)
  else if (ArrayBuffer.isView(d)) d = new Uint8Array(d.buffer, d.byteOffset, d.byteLength)
  else if (d instanceof ArrayBuffer) d = new Uint8Array(d)
  else throw TypeError('data must be a string, ArrayBuffer or typed array')
  for (let i = 0; i < d.length; i += S) {
    const c = d.subarray(i, i + S)
    mem(p, S).set(c)
    x.shx_update(h, p, c.length)
  }
}

const fin = (h, n) => {
  const o = x.shx_finalize(h), r = new Hash(mem(o, n))
  x.shx_free(o, n)
  return r
}

export class Hasher {
  #h
  #n

  constructor(n = 32) {
    reg.register(this, this.#h = make(this.#n = n))
  }

  update(d) {
    feed(this.#h, d)
    return this
  }

  digest() {
    return fin(this.#h, this.#n)
  }
}

// Frees its hasher on the way out; a `Hasher` is left to the garbage collector.
export const shx = (d, n = 32) => {
  const h = make(n)
  try {
    feed(h, d)
    return fin(h, n)
  } finally {
    x.shx_drop(h)
  }
}
