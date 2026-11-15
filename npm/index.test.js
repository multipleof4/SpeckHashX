import { expect, test } from 'bun:test'
import { Hasher, hash, hex } from './index.js'

const p = Uint8Array.from({ length: 1000 }, (_, i) => i * 7 % 251)

// Same answers as the Rust tests, from an independent Python implementation.
test('known answers', () => {
  expect(hex('')).toBe('2353e9fb3e8415144a2ba616b57448957d0a72c4003fd759e6bf96e6a3b57317')
  expect(hex('abc')).toBe('968bf582a5520b3292b7227175bfad8b2e86e49672651916285c9ffb25039e08')
  expect(hex('abc', 16)).toBe('0ac6581d4663285e152e4093de92f540')
  expect(hex('The quick brown fox jumps over the lazy dog')).toBe('d9e735f424a21f47c1f1edad622e07972041b7e258440e8db09edf4065d0930d')
  expect(hex('abc', 1)).toBe('20')
  expect(hex(new Uint8Array(17))).toBe('9148212d6bdfd432b80a0c3c026f851c5b3c3e86285f60cd0dd21a4d3775acc4')
  expect(hex(p.subarray(0, 33), 64)).toBe('582b3398042df36e62436ca378ed3f63664a61e6a96018218f27ecb83806a99b80f0394b65f88aa472b82c26ea254bd2c91e9d335944721dd367fc63fddfadd1')
  expect(hex(p)).toBe('bbc3edc9f53ad7af85ee7aa474275b4909ea89815ab801b9f7437b490ecb49fe')
})

test('streaming, large input and long output', () => {
  const big = new Uint8Array(200_000).map((_, i) => i * 31), s = new Hasher(1000)
  for (let i = 0; i < big.length; i += 777) s.update(big.subarray(i, i + 777))
  expect(s.digest()).toEqual(hash(big, 1000))
  expect(s.update('x').digest()).toEqual(hash(Uint8Array.of(...big, 120), 1000))
  expect(hash('abc', 0).length).toBe(0)
  expect(() => hash('abc', -1)).toThrow(RangeError)
})
