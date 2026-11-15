import { hex } from 'speckhashx'
import './style.css'

const [msg, len, out, bytes, copy, bg] = ['msg', 'len', 'out', 'bytes', 'copy', 'bg'].map(i => document.getElementById(i))

const show = () => {
  out.textContent = hex(msg.value, +len.value)
  bytes.textContent = `${len.value} byte${len.value == 1 ? '' : 's'}`
}

// Background: real hashes of 0, 1, 2, …, about one per 10,000 px² at the size set in style.css.
const fill = () => bg.textContent = Array.from({ length: innerWidth * innerHeight / 1e4 + 9 }, (_, i) => hex(`${i}`)).join('  ')

msg.oninput = len.oninput = show
onresize = fill
copy.onclick = async () => {
  await navigator.clipboard.writeText(out.textContent)
  copy.textContent = 'Copied'
  setTimeout(() => copy.textContent = 'Copy', 1200)
}
fill()
show()
