/** A string is hashed as UTF-8; a buffer, typed array or DataView as its bytes. Anything else throws. */
type Data = string | ArrayBuffer | ArrayBufferView

/** Streaming hasher. `n` is the output length in bytes (default 32). */
export class Hasher {
  constructor(n?: number)
  update(d: Data): this
  /** Returns the hash of everything fed so far; more `update` calls may follow. */
  digest(): Uint8Array
}
export function hash(d: Data, n?: number): Uint8Array
export function hex(d: Data, n?: number): string
