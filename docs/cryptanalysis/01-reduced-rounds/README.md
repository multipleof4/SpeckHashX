# 01. A first look at reduced rounds

November 2026. Done by the author of SpeckHashX with an AI model (Claude). Not an independent review.

## Question

SpeckHashX runs 34 rounds of Speck in every cipher call. How many of them can simple, automated attacks break?

## Short answer

| Attack | Breaks | Stopped at |
|---|---|---|
| Two messages with the same hash | 3 rounds, in 2 seconds | 4 rounds |
| Two chunks with the same step output, from a state the attacker picks | 5 rounds, in 22 seconds | 6 rounds |
| Two step inputs with the same step output, from two different states | 6 rounds, in 11 seconds | 7 rounds |
| A flipped input bit that still shows in the output | 11 rounds | 12 rounds |
| Statistics of the full 34-round hash | nothing unusual | |

"Stopped" means the search did not finish in the time it was given. It is not a proof that no attack exists there.

## Collisions found by a solver

`collide.py` writes the computation of two inputs as one large formula and asks a SAT solver for values that make
the outputs equal. Every answer was recomputed with the reference before it was recorded.

| Goal | 2 rounds | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|
| Same 32-byte hash, two 32-byte messages (a collision) | found, 0.2 s | found, 2 s | not found: 13 runs of 44 min | | | |
| Same step output, same state of the solver's choice (semi-free-start) | impossible | 1 s | 3 s | 22 s | not found: 9 runs of 44 min | |
| Same step output, two different states (free-start) | 0.2 s | 0.4 s | 0.4 s | 9 s | 11 s | not found: 4 runs of 20 min, 4 of 13 min |

- The first row is the real attack. The other two give the attacker control of the hash's inner state, which a real
  attacker does not have. Breaking them does not break the hash; they are a standard way to measure a hash's margin.
- "Impossible" means the solver proved that no such pair exists.
- At 2 rounds the solver proved that two messages with the same first 16 bytes cannot collide. The pair it found differs in both chunks.
- None of the pairs found collide at 34 rounds.

### Check one yourself

Two messages with the same 3-round hash:

```sh
cd docs/cryptanalysis/tools
python ref.py f3fb9f10796786983915704e0ef17273b0347f68ff2fed3b642e3761f4a558f6 32 3
python ref.py f3fb9f10796786983915704e0ef17273b79fd01534bfebd9e895f8fc364b485b 32 3
```

Both print `0edab5e9d32c2304026a7651f8aae4bed7d8b5e9d32c2210536a7651f8aae5b2`. With `34` in place of `3` they differ.
The other pairs are in `results/collide-*.jsonl`.

## Differential trails

A trail is a recipe: change these input bits, and with some probability the changes cancel by the end.
`trails.py` finds the cheapest recipe for a step collision and can prove that none is cheaper.
A cost of 2²⁵ means about 2²⁵ random tries per collision.

Inputs that may differ anywhere (free-start):

| Rounds | Cheapest trail found | No trail is cheaper than | Run for real |
|---|---|---|---|
| 3 | 2⁰: one key word is not used before round 4 | 2⁰ | |
| 4 | 2⁷ | 2⁷, so this one is the cheapest | 245,522 collisions in 2²⁴ pairs: one pair in 68 |
| 5 | 2²⁵ | 2²² | 2,002 collisions in 2³¹ pairs: one pair in 2²⁰ |
| 6 | 2⁶⁰ | 2²⁰ | not run |

Inputs that differ in the message chunk only: no trail exists at 2 rounds. At 3 rounds the cheapest found costs 2¹⁰⁵
(none below 2⁴⁵), at 4 rounds 2²²⁴ (none below 2²⁸). These two searches ran for only 150 seconds each.

Two things this taught us:

- **Trail costs are upper limits, not estimates.** They count random tries. The solver above solves for the inputs
  instead, and it found a 3-round collision in 2 seconds where the trail says 2¹⁰⁵ tries, and a 6-round free-start collision in 11 seconds where the trail says 2⁶⁰.
- **The two cipher calls of a step are not independent.** The cost formula charges the cipher part of a trail twice,
  once per call. Measured, the 5-round trail holds once in 2²⁰ and not once in 2²⁵: the second call follows almost for free.
  Its input differs from the first call's in a single bit.

The trail model was checked on plain Speck128 with no key difference: it gives 0, 1, 3, 6 and 10 as the lowest trail weights for
1 to 5 rounds, each proven lowest, and finds 15 for 6 rounds (`results/trails-check.jsonl`). We believe these are the published values
but did not check them against a paper.

## Bit flips

Flip one of the 384 input bits of a step (chunk, `g`, `x`) and each of the 256 output bits should flip half the time.
`run.py scan` counts how often each one does: 98,304 measurements per round count.

| Rounds | Inputs per input bit | Measurements off a fair coin | Largest deviation |
|---|---|---|---|
| 8 | 2¹⁸ | 21,285 | |
| 9 | 2¹⁸ | 9,683 | |
| 10 | 2²⁴ | 5,461 | 2,691 standard deviations |
| 11 | 2²⁴ | 1,155 | 681 |
| 12 | 2²⁴ | 0 | 4.6 |
| 13 | 2²⁴ | 0 | 4.2 |
| 14 | 2²⁴ | 0 | 4.9 |
| 34 | 2²² | 0 | 4.2 |

Chance alone gives a largest deviation between about 4.2 and 5 among 98,304 measurements. "Off a fair coin" counts those above 5.5.
The last bias to go, at 11 rounds, comes from the high half of `g`, the key word that Speck uses last.

## The full hash on short outputs

A 7-byte hash has 2⁵⁶ possible values, so among 2³² messages about 128 pairs should share a hash by chance.
Far more would mean the output is not spread evenly. `run.py pairs` hashes the 8-byte messages 0, 1, 2, … and counts.

| Rounds | Output | Messages | Colliding pairs | Expected by chance |
|---|---|---|---|---|
| 34 | 7 bytes | 2³² | 110 | 128, give or take 11 |
| 34 | 5 bytes | 2²⁴ | 124 | 128, give or take 11 |
| 6 | 5 bytes | 2²⁴ | 138 | 128, give or take 11 |
| 3 | 5 bytes | 2²⁴ | 6,320 | 128, give or take 11 |

The full hash behaves as chance predicts, and the test does catch a weak version: 3 rounds fail it badly.

## What this does not show

- **Not how strong 34 rounds are.** These are the first attacks an automated tool finds, given under an hour.
  Published attacks on Speck128/256 used as a cipher [reach 25 of its 34 rounds](https://en.wikipedia.org/wiki/Speck_(cipher)#Cryptanalysis). Attacking a hash is a different problem,
  and these numbers do not say how far dedicated attacks would get.
- **"Not found" is not "impossible".** Longer runs, more seeds or a better encoding may break the next round.
- **The full-hash tests can only catch gross flaws.** A hash can pass them and still be breakable.
- **Much is untested:** preimages, rotational, boomerang, linear and algebraic attacks, messages of more than two chunks,
  the output stage, and output lengths other than 32 bytes for the hash collisions.

## How it was run

- Solver: [Kissat](https://github.com/arminbiere/kissat) 4.0.4, several copies per problem with different seeds.
- The 44-minute searches, the 2²⁴ and 34-round scans, the 2³² count and the 5 and 6-round trail searches ran on a rented
  32-core machine (AMD EPYC Milan, 61 GB) for 48 minutes. Everything else ran on a 4-core virtual machine.
- No GPU was used: none was in stock. The OpenCL code ran on the CPU.

```sh
cd docs/cryptanalysis/tools           # setup: see tools/README.md
python collide.py hash 4 2658 7       # mode, rounds, seconds, copies; also hash2 4, step 5, step 6, free 1 to 7
python trails.py f 5 664 4            # also f 3, f 4, f 6, and c 2 to c 4
python run.py hunt trail.json 31 any  # a trail from trails.py, 2^31 pairs
python run.py scan 10 14 24           # also 1 to 9 at 18, and 34 at 22
python run.py pairs 7 32              # also 5 24 with 3, 6 and 34 rounds
```

Raw output is in `results/`: one line of JSON per result. The files ending in `-small`, and `collide-free`, `hunt` and `trails-check`,
are from the 4-core machine; the last line of `collide-free` and all other files are from the rented one.
