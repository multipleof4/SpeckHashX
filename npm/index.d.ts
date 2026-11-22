/** A string is hashed as UTF-8; a buffer, typed array or DataView as its bytes. Anything else throws. */
type Data = string | ArrayBuffer | ArrayBufferView

/** A hash: its bytes, with methods that give them as text. */
export interface Hash extends Uint8Array {
  /** Lowercase hex, two characters per byte; the same as `base(16)`. */
  hex(): string
  /**
   * The bytes as text in base `r`.
   * Bases 2 to 36 give them as one big-endian number in the digits `0-9a-z`, leading zeros kept;
   * in a base other than 2, 4, 8, 16 and 32 the hash can be at most 1,024 bytes.
   * Base 64 is base64url with no `=` at the end.
   */
  base(r: number): string
}

/** Streaming hasher. `n` is the output length in bytes (default 32). */
export class Hasher {
  constructor(n?: number)
  update(d: Data): this
  /** Returns the hash of everything fed so far; more `update` calls may follow. */
  digest(): Hash
}
/** Hashes `d` to `n` bytes (default 32). */
export function shx(d: Data, n?: number): Hash
