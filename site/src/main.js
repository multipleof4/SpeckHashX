import { shx } from 'speckhashx'
import './style.css'

const [msg, len, base, out, bytes, copy, bg] = ['msg', 'len', 'base', 'out', 'bytes', 'copy', 'bg'].map(i => document.getElementById(i))

// Every base .base() takes: 2 to 62, and 64.
const names = { 2: 'binary', 8: 'octal', 10: 'decimal', 16: 'hex', 64: 'base64url' }
base.innerHTML = Array.from({ length: 62 }, (_, i) => i < 61 ? i + 2 : 64)
  .map(r => `<option value="${r}"${r == 16 ? ' selected' : ''}>${r}${names[r] ? ` (${names[r]})` : ''}</option>`).join('')

const show = () => {
  out.textContent = shx(msg.value, +len.value).base(+base.value)
  bytes.textContent = `${len.value} byte${len.value == 1 ? '' : 's'}`
}

// Background: real hashes of 0, 1, 2, …, about one per 10,000 px² at the size set in style.css.
const fill = () => bg.textContent = Array.from({ length: innerWidth * innerHeight / 1e4 + 9 }, (_, i) => shx(`${i}`).hex()).join('  ')

msg.oninput = len.oninput = base.onchange = show
onresize = fill
copy.onclick = async () => {
  await navigator.clipboard.writeText(out.textContent)
  copy.textContent = 'Copied'
  setTimeout(() => copy.textContent = 'Copy', 1200)
}
fill()
show()
