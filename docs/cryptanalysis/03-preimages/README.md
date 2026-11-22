# 03. Preimages

November 2026. Done by the author of SpeckHashX with an AI model (Claude). Not an independent review.

## Question

Given a hash, can a SAT solver find a message that has it? Up to how many rounds?

[01](../01-reduced-rounds/README.md) and [02](../02-guided-collisions/README.md) looked for collisions, two messages
with the same hash. A preimage is harder in general: the target is fixed, so there is no birthday shortcut.
For a short secret message, brute force tries every message of that length.

## Setup

`preimage.py` hashes a random message of `L` bytes with `R` rounds to an output of `N` bytes, then gives the solver
`L`, `N`, `R` and the hash, and asks for any `L`-byte message with that hash. Messages are shorter than 16 bytes,
so the hash is one step and the output stage. Every answer was recomputed with the reference.

Brute force needs about 2^(8L) tries when the output is at least as long as the message, and 2^(8N) when it is shorter.

## Results

Each cell says how many targets were found, and in how long. Every try had 20 minutes, except the 5-round pushes below.

| Message | Output | Brute force | 2 rounds | 3 rounds | 4 rounds | 5 rounds |
|---|---|---|---|---|---|---|
| 8 bytes | 32 bytes | 2⁶⁴ | | | 3 of 3, in 1 to 4 s | 0 of 1; also not in 60 minutes with 4 copies |
| 12 bytes | 32 bytes | 2⁹⁶ | | | 2 of 3, in 20 to 91 s | not in 60 minutes with 4 copies |
| 15 bytes | 32 bytes | 2¹²⁰ | | 1 of 1, in 1 to 2 s | 2 of 3, in 18 to 61 s | 0 of 1; also not in 60 minutes with 4 copies |
| 15 bytes | 8 bytes | 2⁶⁴ | 1 of 1, in 0.1 s | 3 of 3, in 4 to 152 s | 0 of 1 | |

Blank cells were not tried: each climb started where the solver was expected to win at once.

- **Four rounds fall.** At 4 rounds an unknown 8-byte message comes back from its 32-byte hash in about a second,
  where brute force would hash 2⁶⁴ messages. Longer messages take longer and sometimes run out of time.
- **Five rounds held.** No preimage was found at 5 rounds in any setting.
- **A longer output helps the solver.** Every bit of the target is a constraint it can work with. With an 8-byte output
  the solver reached only 3 rounds, though brute force is no cheaper than for an 8-byte message.
- **With an 8-byte output the answer is a different message.** Many 15-byte messages share an 8-byte hash, and the solver returns
  one of them, not the secret one: a second preimage. With a 32-byte output it returned the secret message every time,
  as expected when the hash is longer than the message.

## What this does not show

- **Not how strong 34 rounds are.** Like 01 and 02, this is a floor set by automated tools in a few hours.
- **Only one-chunk messages.** Longer messages give an attacker more freedom; meet-in-the-middle methods were not tried.
- **Few targets per setting.** Three random messages at 4 rounds and one elsewhere, so the times are examples, not averages.

## How it was run

- Solver: [Kissat](https://github.com/arminbiere/kissat) 4.0.4, two copies per problem with different seeds.
- On a rented 32-core machine (AMD EPYC Milan), 20 minutes per try. A climb stopped at the first round count that ran out of time.
- The climbs were started twice by mistake, once with 4 solver copies and once with 2, and ran side by side for a few minutes.
  Both runs' lines are in `results/`, which is why some settings have two times.

The code is in [`tools/`](tools/): `preimage.py` and the reference `ref.py`. Setup is as in [01](../01-reduced-rounds/README.md#how-it-was-run).

```sh
cd docs/cryptanalysis/03-preimages/tools
python preimage.py 4 8 32 1 1200 2   # rounds, message bytes, output bytes, seed, seconds, solver copies
```

Raw output is in `results/`: `climb-*.jsonl` per setting with target 1, `more-targets.jsonl` with targets 2 and 3,
and `push-5rounds.jsonl` with the 60-minute tries.
