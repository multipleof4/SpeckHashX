import { expect, test } from 'bun:test'
import { Hasher, hash, hex } from './index.js'

const p = Uint8Array.from({ length: 1000 }, (_, i) => i * 7 % 251)

// Same answers as the Rust tests, from an independent Python implementation.
test('known answers', () => {
  expect(hex('')).toBe('2353e9fb3e8415144a2ba616b57448957d0a72c4003fd759e6bf96e6a3b57317')
  expect(hex('abc')).toBe('f9d38f0c372695b67d5c06c25421beaede279d9a6da9422cfecfa18e638e96f3')
  expect(hex('abc', 16)).toBe('dbfecc39d9de1f993d00a90030e89294')
  expect(hex('The quick brown fox jumps over the lazy dog')).toBe('edb6137d9032d6a8e607754a0a29e18702b578d512d119a9f249f5bb4f6ac353')
  expect(hex('abc', 1)).toBe('b3')
  expect(hex(new Uint8Array(17))).toBe('8424162ee390487cdb4e6e468a923363ea63bb89ea37b254b73bf227eae7fb4f')
  expect(hex(p.subarray(0, 33), 64)).toBe('e3a90c0dce6d78767691510c890a40cf2e2ce8933729baf072f1ed3e7bfcd52345b9a8d1b2b0c7089405e5921ff9b8102150844d8a84cac92857eff650982d44')
  expect(hex(p)).toBe('8a0d7524c6ee6ef86b6cfd7de2727ede7b74dc8c32430626c892b20380ad5427')
})

test('streaming, large input and long output', () => {
  const big = new Uint8Array(200_000).map((_, i) => i * 31), s = new Hasher(1000)
  for (let i = 0; i < big.length; i += 777) s.update(big.subarray(i, i + 777))
  expect(s.digest()).toEqual(hash(big, 1000))
  expect(s.update('x').digest()).toEqual(hash(Uint8Array.of(...big, 120), 1000))
  expect(hash('abc', 0).length).toBe(0)
  expect(() => hash('abc', -1)).toThrow(RangeError)
})

test('input types', () => {
  const b = Uint8Array.of(0, 97, 98, 99, 0)
  for (const d of [b.subarray(1, 4), b.buffer.slice(1, 4), new DataView(b.buffer, 1, 3), Buffer.from('abc')])
    expect(hex(d)).toBe(hex('abc'))
  expect(hex(new Uint16Array(b.buffer.slice(1, 3)))).toBe(hex('ab'))
  for (const d of [12345, {}, true, null, undefined, [97, 98, 99]]) expect(() => hash(d)).toThrow(TypeError)
})
