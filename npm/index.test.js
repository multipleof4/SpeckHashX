import { expect, test } from 'bun:test'
import * as m from './index.js'

const { Hasher, shx } = m, p = Uint8Array.from({ length: 1000 }, (_, i) => i * 7 % 251)

// Same answers as the Rust tests, from an independent Python implementation.
test('known answers', () => {
  expect(shx('').hex()).toBe('2353e9fb3e8415144a2ba616b57448957d0a72c4003fd759e6bf96e6a3b57317')
  expect(shx('abc').hex()).toBe('f9d38f0c372695b67d5c06c25421beaede279d9a6da9422cfecfa18e638e96f3')
  expect(shx('abc', 16).hex()).toBe('dbfecc39d9de1f993d00a90030e89294')
  expect(shx('The quick brown fox jumps over the lazy dog').hex()).toBe('edb6137d9032d6a8e607754a0a29e18702b578d512d119a9f249f5bb4f6ac353')
  expect(shx('abc', 1).hex()).toBe('b3')
  expect(shx(new Uint8Array(17)).hex()).toBe('8424162ee390487cdb4e6e468a923363ea63bb89ea37b254b73bf227eae7fb4f')
  expect(shx(p.subarray(0, 33), 64).hex()).toBe('e3a90c0dce6d78767691510c890a40cf2e2ce8933729baf072f1ed3e7bfcd52345b9a8d1b2b0c7089405e5921ff9b8102150844d8a84cac92857eff650982d44')
  expect(shx(p).hex()).toBe('8a0d7524c6ee6ef86b6cfd7de2727ede7b74dc8c32430626c892b20380ad5427')
})

test('known answers in other bases', () => {
  const h = shx('abc')
  expect(h.base(2)).toBe('1111100111010011100011110000110000110111001001101001010110110110011111010101110000000110110000100101010000100001101111101010111011011110001001111001110110011010011011011010100101000010001011001111111011001111101000011000111001100011100011101001011011110011')
  expect(h.base(10)).toBe('112999691306956569769269184981788655759217413943854614658490461780486682220275')
  expect(h.base(16)).toBe(h.hex())
  expect(h.base(32)).toBe('1uejhs63e9klmpulo1m2aggrtbmu4uepkrd988mftjt1hphot5nj')
  expect(h.base(36)).toBe('685qrcbn2jal82oppuwq48513j85gc1pqczm0niqxoyejmijub')
  expect(h.base(64)).toBe('-dOPDDcmlbZ9XAbCVCG-rt4nnZptqUIs_s-hjmOOlvM')
  expect(shx('abc', 16).base(36)).toBe('d0vfm401wkr6oew7tm0tef0k4')
  // Leading zeros stay.
  expect(shx('').base(10)).toBe('015979212887220042755496585023260168943665753206110443921945613077242631779095')
  expect(shx('').base(36)).toBe('0vp4xr6nktgf2khkk0szu4la2ak25np163qt437hvy1sj6ls0n')
  expect(shx('abc', 0).base(36)).toBe('')
  expect(new Hasher().update('ab').update('c').digest().base(36)).toBe(h.base(36))
})

test('every base matches BigInt and Buffer', () => {
  for (let n = 0; n < 80; n++) {
    const h = shx(`${n}`, n).fill(0, 0, n % 7 ? 0 : n % 5), b = Buffer.from(h), v = BigInt('0x0' + b.toString('hex'))
    expect(h.hex()).toBe(b.toString('hex'))
    expect(h.base(64)).toBe(b.toString('base64url'))
    for (let r = 2; r < 37; r++)
      expect(h.base(r)).toBe(n ? v.toString(r).padStart((256n ** BigInt(n) - 1n).toString(r).length, '0') : '')
  }
})

test('refused bases and lengths', () => {
  const h = shx('abc'), l = shx('abc', 1025)
  for (const r of [0, 1, 37, 63, 65, -2, 3.5, NaN, Infinity, '36', 36n, null, undefined]) expect(() => h.base(r)).toThrow(RangeError)
  expect(() => l.base(10)).toThrow(RangeError)
  expect(l.base(8).length).toBe(2734)
  expect(l.hex().length).toBe(2050)
  expect(l.base(64).length).toBe(1367)
  expect(shx('abc', 1024).base(10).length).toBe(2467)
})

test('the result is its bytes', () => {
  const h = shx('abc')
  expect(h).toBeInstanceOf(Uint8Array)
  expect(h.length).toBe(32)
  expect([...h.subarray(0, 4)]).toEqual([0xf9, 0xd3, 0x8f, 0x0c])
  expect(h.slice(0, 4).hex()).toBe('f9d38f0c')
  expect(Object.keys(m).sort()).toEqual(['Hasher', 'shx'])
})

test('streaming, large input and long output', () => {
  const big = new Uint8Array(200_000).map((_, i) => i * 31), s = new Hasher(1000)
  for (let i = 0; i < big.length; i += 777) s.update(big.subarray(i, i + 777))
  expect(s.digest()).toEqual(shx(big, 1000))
  expect(s.update('x').digest()).toEqual(shx(Uint8Array.of(...big, 120), 1000))
  expect(shx('abc', 0).length).toBe(0)
  expect(() => shx('abc', -1)).toThrow(RangeError)
})

test('input types', () => {
  const b = Uint8Array.of(0, 97, 98, 99, 0)
  for (const d of [b.subarray(1, 4), b.buffer.slice(1, 4), new DataView(b.buffer, 1, 3), Buffer.from('abc')])
    expect(shx(d).hex()).toBe(shx('abc').hex())
  expect(shx(new Uint16Array(b.buffer.slice(1, 3))).hex()).toBe(shx('ab').hex())
  for (const d of [12345, {}, true, null, undefined, [97, 98, 99]]) expect(() => shx(d)).toThrow(TypeError)
})
