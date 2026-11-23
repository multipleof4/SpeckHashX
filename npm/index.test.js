import { expect, test } from 'bun:test'
import * as m from './index.js'

const { Hasher, shx } = m, p = Uint8Array.from({ length: 1000 }, (_, i) => i * 7 % 251)
const D = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'

// Same answers as the Rust tests, from an independent Python implementation.
test('known answers', () => {
  expect(shx('').hex()).toBe('2353E9FB3E8415144A2BA616B57448957D0A72C4003FD759E6BF96E6A3B57317')
  expect(shx('abc').hex()).toBe('F9D38F0C372695B67D5C06C25421BEAEDE279D9A6DA9422CFECFA18E638E96F3')
  expect(shx('abc', 16).hex()).toBe('DBFECC39D9DE1F993D00A90030E89294')
  expect(shx('The quick brown fox jumps over the lazy dog').hex()).toBe('EDB6137D9032D6A8E607754A0A29E18702B578D512D119A9F249F5BB4F6AC353')
  expect(shx('abc', 1).hex()).toBe('B3')
  expect(shx(new Uint8Array(17)).hex()).toBe('8424162EE390487CDB4E6E468A923363EA63BB89EA37B254B73BF227EAE7FB4F')
  expect(shx(p.subarray(0, 33), 64).hex()).toBe('E3A90C0DCE6D78767691510C890A40CF2E2CE8933729BAF072F1ED3E7BFCD52345B9A8D1B2B0C7089405E5921FF9B8102150844D8A84CAC92857EFF650982D44')
  expect(shx(p).hex()).toBe('8A0D7524C6EE6EF86B6CFD7DE2727EDE7B74DC8C32430626C892B20380AD5427')
})

test('known answers in other bases', () => {
  const h = shx('abc')
  expect(h.base(2)).toBe('1111100111010011100011110000110000110111001001101001010110110110011111010101110000000110110000100101010000100001101111101010111011011110001001111001110110011010011011011010100101000010001011001111111011001111101000011000111001100011100011101001011011110011')
  expect(h.base(10)).toBe('112999691306956569769269184981788655759217413943854614658490461780486682220275')
  expect(h.base(16)).toBe(h.hex())
  expect(h.base(32)).toBe('1UEJHS63E9KLMPULO1M2AGGRTBMU4UEPKRD988MFTJT1HPHOT5NJ')
  expect(h.base(36)).toBe('685QRCBN2JAL82OPPUWQ48513J85GC1PQCZM0NIQXOYEJMIJUB')
  expect(h.base(37)).toBe('1N6DHPaAZXaYRF5CZ40A6490WXXANKDRB976MHT6UKYVS64UZZ')
  expect(h.base(58)).toBe('GlCZv1U9WjFaWgqO4ht5kjtDePnC7QvhQah3ks5ruSah')
  expect(h.base(62)).toBe('xEySOeSw03P6yQX1jTkBhtsGxk21oAxPxH4xCtxpHGN')
  expect(h.base(64)).toBe('-dOPDDcmlbZ9XAbCVCG-rt4nnZptqUIs_s-hjmOOlvM')
  expect(shx('abc', 16).base(36)).toBe('D0VFM401WKR6OEW7TM0TEF0K4')
  expect(shx('abc', 16).base(62)).toBe('6h7lH5g2lldpEWa6X8YesG')
  // Leading zeros stay.
  expect(shx('').base(10)).toBe('015979212887220042755496585023260168943665753206110443921945613077242631779095')
  expect(shx('').base(36)).toBe('0VP4XR6NKTGF2KHKK0SZU4LA2AK25NP163QT437HVY1SJ6LS0N')
  expect(shx('abc', 0).base(62)).toBe('')
  expect(new Hasher().update('ab').update('c').digest().base(62)).toBe(h.base(62))
})

test('every base matches BigInt and Buffer', () => {
  for (let n = 0; n < 80; n++) {
    const h = shx(`${n}`, n).fill(0, 0, n % 7 ? 0 : n % 5), b = Buffer.from(h)
    expect(h.hex()).toBe(b.toString('hex').toUpperCase())
    expect(h.base(64)).toBe(b.toString('base64url'))
    for (let r = 2n; r < 63n; r++) {
      let o = ''
      for (let v = BigInt('0x0' + b.toString('hex')), k = 256n ** BigInt(n) - 1n; k; v /= r, k /= r) o = D[v % r] + o
      expect(h.base(Number(r))).toBe(o)
    }
  }
})

// Digits, then uppercase, then lowercase is the order text sorts in.
test('text sorts in the order of the numbers', () => {
  const h = Array.from({ length: 300 }, (_, i) => shx(`${i}`, 6))
  for (const r of [10, 16, 36, 62]) {
    const t = h.map(v => v.base(r))
    expect([...t].sort()).toEqual([...t].sort((a, b) => BigInt('0x' + h[t.indexOf(a)].hex()) < BigInt('0x' + h[t.indexOf(b)].hex()) ? -1 : 1))
  }
})

test('refused bases and lengths', () => {
  const h = shx('abc'), l = shx('abc', 1025)
  for (const r of [0, 1, 63, 65, -2, 3.5, NaN, Infinity, '36', 36n, null, undefined]) expect(() => h.base(r)).toThrow(RangeError)
  expect(() => l.base(10)).toThrow(RangeError)
  expect(() => l.base(62)).toThrow(RangeError)
  expect(l.base(8).length).toBe(2734)
  expect(l.hex().length).toBe(2050)
  expect(l.base(64).length).toBe(1367)
  expect(shx('abc', 1024).base(10).length).toBe(2467)
  expect(shx('abc', 1024).base(62).length).toBe(1376)
})

test('the result is its bytes', () => {
  const h = shx('abc')
  expect(h).toBeInstanceOf(Uint8Array)
  expect(h.length).toBe(32)
  expect([...h.subarray(0, 4)]).toEqual([0xf9, 0xd3, 0x8f, 0x0c])
  expect(h.slice(0, 4).hex()).toBe('F9D38F0C')
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
