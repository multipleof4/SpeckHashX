# Tools

Code shared by the analyses in this folder. Every tool takes the number of Speck rounds as a parameter,
so the same code attacks a weakened hash and checks the real one (34 rounds).

| File | What it does |
|---|---|
| `ref.py` | The hash as in [spec.md](../../spec.md), with the round count as a parameter. Everything else is checked against it. |
| `collide.py` | Asks a SAT solver for two actual inputs that collide. |
| `trails.py` | Asks a SAT solver for the cheapest differential trail, and proves that none is cheaper. |
| `shx.cl`, `run.py` | Experiments that run the hash billions of times, on a GPU or on all CPU cores. |

## Setup

```sh
uv venv .venv
uv pip install --python .venv/bin/python python-sat numpy pyopencl pocl-binary-distribution
git clone --depth 1 https://github.com/arminbiere/kissat && (cd kissat && ./configure && make)
export KISSAT=$PWD/kissat/build/kissat
```

`pocl-binary-distribution` runs the OpenCL code on the CPU; it needs `gcc` installed. With a GPU and its driver, `run.py` uses the GPU instead.

## Use

```sh
python ref.py 616263 32 34         # hash of "abc" (hex), 32 bytes, 34 rounds
python run.py check                # the OpenCL code against ref.py
python collide.py hash 3           # two messages with the same 3-round hash
python collide.py step 5           # two chunks with the same 5-round step output
python trails.py f 4 > trail.json  # cheapest free-start trail of the 4-round step
python run.py hunt trail.json 24 any   # run 2^24 input pairs along that trail
python run.py scan 10 14 24        # bit-flip counts for rounds 10 to 14
python run.py pairs 7 32           # colliding pairs among 2^32 seven-byte hashes
```

Each tool prints one line of JSON per result. The top of each file says what its arguments mean.
