/** Streaming hasher. `n` is the output length in bytes (default 32). */
export class Hasher {
  constructor(n?: number)
  update(d: Uint8Array | string): this
  /** Returns the hash of everything fed so far; more `update` calls may follow. */
  digest(): Uint8Array
}
export function hash(d: Uint8Array | string, n?: number): Uint8Array
export function hex(d: Uint8Array | string, n?: number): string
