# 02. Guided collision search

November 2026. Done by the author of SpeckHashX with an AI model (Claude). Not an independent review.

## Question

In [01](../01-reduced-rounds/README.md) a SAT solver searched for collisions with no help and stalled at
4 rounds for the hash, 6 for a step from a chosen state and 7 for a step from two different states.
Does it get further when it is told which bits should differ?

## Short answer

| Goal | 01, no hint | 02, with a hint |
|---|---|---|
| Two messages with the same hash | 3 rounds | still 3 |
| Two chunks with the same step output, from a state the solver picks | 5 rounds | still 5 |
| Two step inputs with the same step output, from two different states | 6 rounds | 12 rounds |

- **Hints break free-start collisions wide open.** With a trail to follow, the solver usually finds a pair in under a second,
  where 01's search took seconds or stalled. Up to 12 rounds fell; 13 did not in the time given.
- **The hash itself did not move.** From a random state, no single flipped message bit gives a 4-round hash collision:
  every case tried was proven impossible.
- **The two cipher calls of a step make most message-only trails impossible.** A trail model that treats them as independent
  gives trails that cannot happen, including the message-only trails 01 reported.

## Hints

`guided.py` is 01's collision search with a hint added: the two inputs must differ in a given way, and so
must the words computed on the way. A trail from `trails.py` gives the differences. The hint comes in three strengths:

| Hint | The two inputs must follow |
|---|---|
| whole trail | the differences in every word: the key schedule and both cipher calls, round by round |
| key schedule | the differences in the key schedule only; the cipher calls may go any way |
| input difference | the difference of the inputs only; everything after it is up to the solver |

A hint can rule out every pair. The solver then proves that none exists, usually in seconds,
which is how most of the results below that say "impossible" were obtained.

## Free-start collisions

Two step inputs that differ anywhere and give the same step output. Trails from `trails.py`, mode `f`.

| Rounds | Trail used | Whole trail | Key schedule | Input difference | 01, no hint |
|---|---|---|---|---|---|
| 4 | 2⁷ | 0.2 s | 0.3 s | 0.6 s | 0.4 s |
| 5 | 2²⁵ | 0.2 s | 0.9 s | 10.6 s | 8.5 s |
| 6 | 2⁶⁰ | 0.6 s | 1.2 s | 11.8 s | 10.7 s |

The trails for 4 to 6 rounds are the ones in 01. Times are for two solver copies on a 4-core machine (`results/guided-free-small.jsonl`).

Given a trail it can follow, the solver finds a pair at once, and the whole trail is the strongest hint.
So the work moves to finding trails, round by round:

| Rounds | Trail search | Trails tried | Collision found in |
|---|---|---|---|
| 7 | the cheapest: 2⁷⁴, and none below 2²³ | 1 | 0.3 s |
| 8 | the cheapest: 2⁸⁹, and none below 2²⁴ | 1 | 0.4 s |
| 9 | any under 2²⁷⁰ | 9, of which 8 impossible | 2.5 s, on a trail of 2²²⁴ |
| 10 | any under 2³⁰⁰, exact key schedule | 2, of which 1 impossible | 0.4 s, on a trail of 2²⁶⁷ |
| 11 | any under 2⁴⁴⁰, exact key schedule | 1, the first of 30 found | 0.4 s, on a trail of 2⁴²⁴ |
| 12 | any under 2³⁶⁰, exact key schedule | 2, of which 1 impossible | 80 s, on a trail of 2³⁴⁹ |
| 13 | any under 2³⁹⁰, exact key schedule | none found in 25 minutes | |

A second search at 12 rounds, with a bound of 2⁴⁸⁰, found 27 trails: 25 were proven impossible and 2 ran out of time
at 15 minutes. With the key schedule exact, these failures come from the cipher calls.

- **Without an exact key schedule, most trails fail there.** At 9 rounds the cheapest trail found, 2¹³², is impossible already in the key
  schedule, and at 10 rounds all 30 trails from the plain search are impossible. `trails.py` with `EXACT=1` also computes
  the key schedule on actual values for both inputs, so its trails always have a possible key schedule.
  With it, 10 to 12 rounds fell.
- **Trail costs are not probabilities here.** The 11-round trail costs 2⁴²⁴ in the model, more than the 384 bits a
  free-start pair can choose, yet a pair follows it. The model charges each of the two cipher calls in full,
  and as shown below, the calls are far from independent.
- Free-start collisions do not attack the hash: they need both chaining states chosen. They measure how much of the
  step's strength comes from the attacker not controlling the state. Here, 12 of 34 rounds with a hint.

## One flipped message bit

For a step from one state, or for the hash, the two inputs differ only in the message chunk. The simplest
hint is a single flipped bit. `guided.py` tried each of the 128 bits as the input difference, with nothing else fixed:

| Goal | Rounds | Works | Proven impossible | Out of time |
|---|---|---|---|---|
| Same step output, state of the solver's choice | 4 | 8 | 120 | 0 (60 s each) |
| Same step output, state of the solver's choice | 5 | 5 | 70 | 53 (180 s each) |
| Same 32-byte hash | 4 | 0 | 120 | 8 (300 s each) |

- At 4 rounds the 8 bits that work are bits 0 to 7 of the chunk: its first byte.
- At 5 rounds the bits that work are bits 54, 62 and 63 of the low half and 19 and 27 of the high half.
- For the hash, the 120 impossible bits are the same as for the step. The 8 that remain ran out of time.

With 20 minutes instead of 3, bits 3 and 7 of the chunk also work at 5 rounds, after 16 and 8 minutes;
bits 0, 1, 2, 4, 5 and 6 ran out of time. At 6 rounds, four of the bits that work at 5 (bits 54 and 63 of the low half,
19 and 27 of the high half) each ran 40 minutes with two solver copies. None gave a collision.

## The two cipher calls of a step

A step runs the cipher twice under the same key, on inputs that differ in one bit (bit 126).
The trail model in `trails.py` treats the two calls as independent: it charges each one the cost of the trail.
In fact their values are almost the same, and that makes many trails impossible.

`feasible.py` asks the solver, for each trail, whether any pair of inputs follows it with one call, and with both:

| Trails | Possible with both calls | Possible with one call only | Impossible even with one |
|---|---|---|---|
| 60 message-only, 3 rounds, cost 2⁹⁶ to 2¹³⁰ | 23 | 35 | 2 |
| 40 message-only, 4 rounds, cost 2³⁰⁰ | 0 | 40 | 0 |
| 10 message-only, 4 rounds, exact key schedule, cost 2²³² to 2³⁰⁰ | 0 | 8 | 2 |
| 60 free-start, 5 rounds, cost 2²⁶ to 2³² | 47 | 1 | 12 |

- **Every message-only trail at 4 rounds that we tested is impossible with both calls,** with the key schedule exact or not.
  So are the message-only trails in 01: its 3-round trail of cost 2¹⁰⁵ and its 4-round trail of cost 2²²⁴,
  and a 2²⁰¹ trail found later (`results/feasible-c-earlier.jsonl`). The costs 01 gives for
  message-only trails are therefore costs of trails that cannot happen. Its lower bounds still hold.
- The cheapest 3-round message-only trail found, 2⁹⁶, is possible with both calls.
- Free-start trails rarely have the problem. Their 12 failures even with one call have another cause:
  in all 12 the key schedule alone cannot follow the trail, and in the other 48 it can (`results/keysched-f5.jsonl`). The model treats the additions of Speck's key schedule
  as independent, which they are not, a known effect ([Qin and Wu](https://arxiv.org/abs/2203.09741)).

The 4-round step collisions above do exist, so they follow some trail. `trail_of.py` reads off the trail a pair actually
follows and `weight.py` gives its cost in the same model:

| Flipped bit | Key schedule | Each cipher call | Cost |
|---|---|---|---|
| 0 | 2¹²⁹ | 2¹⁵² | 2⁴³³ |
| 6 | 2¹⁵⁵ | 2⁷⁸ | 2³¹¹ |
| 7 | 2¹⁷¹ | 2¹⁰⁰ | 2³⁷¹ |

All 8 pairs follow trails that cost between 2³¹¹ and 2⁴³³, and both calls follow the same one.
A trail search looking for cheap trails would never find them. They are reachable because the solver works on the values,
and a step from a chosen state has 384 free bits: 128 of message and 256 of state.

## The 4-round hash

For the hash the state is not free: it comes from the message's first chunk. Two experiments:

- **Fixed first chunk.** 16 random first chunks, each with the 8 bits that work for the step: all 128 runs proven impossible,
  each in 18 seconds or less.
- **Many first chunks.** 154 more random first chunks, the 8 bits in turn, 60 seconds each: all proven impossible.

This fits the costs above. From a fixed state only the 128 bits of the second chunk are free, and the trails that
4-round step collisions follow cost 2³¹¹ or more, so a random state almost never allows one.
A 4-round hash collision needs a trail that costs well under 2²⁵⁶ and that both calls can follow. None was found.

## What this does not show

- **Not how strong 34 rounds are.** Like 01, this is a floor set by automated tools in a few hours.
- **"Impossible" is for the hint given.** A result that says impossible rules out that difference or trail, not other ones.
- **Only single-bit message differences were swept.** Differences of two or more bits, and other trails, are untested.
- **The free-start results do not apply to the hash directly.** They let the attacker choose both states, which a hash does not allow.

## How it was run

- Solver: [Kissat](https://github.com/arminbiere/kissat) 4.0.4, one to eight copies per problem with different seeds.
- A rented 32-core machine (AMD EPYC Milan) ran for 3 hours, shared with [03](../03-preimages/README.md).
  The free-start comparison at 4 to 6 rounds and the files `keysched-f5`, `trails-c-earlier`, `feasible-c-earlier`,
  `exact-trails-c4`, `feasible-exact-c4`, `followed-step4` and `weight-step4` come from a 4-core virtual machine.

The code is in [`tools/`](tools/). It starts from 01's and adds:

| File | What it does |
|---|---|
| `guided.py` | The collision search with a hint: a trail at one of three strengths, or a message difference. |
| `feasible.py` | Whether trails can be followed by one cipher call, and by both. |
| `trail_of.py` | The trail a found pair actually follows. |
| `weight.py` | The cost of a trail in `trails.py`'s model. |
| `trails.py` | 01's trail search, with `many` added: many trails under a bound, each with a different key schedule. With `EXACT=1` it also computes the key schedule on values. |

Setup is as in [01](../01-reduced-rounds/README.md#how-it-was-run). The runs behind the results:

```sh
cd docs/cryptanalysis/02-guided-collisions/tools
python guided.py free trail.json all 900 8               # trail: a line of results/trails-f.jsonl
EXACT=1 python trails.py many f 10 300 30 1500 4 > f10.jsonl              # trails for the climb
python guided.py step dm:4:0000000000000080:0000000000000000 in 60 1   # one flipped bit, 4 rounds
FIRST=<32 hex digits> python guided.py hash dm:4:0000000000000080:0000000000000000 in 120 1
python trails.py many c 3 130 60 1200 4 > c3.jsonl && python feasible.py step c3.jsonl 60
python feasible.py ks free f5.jsonl 60                    # the key schedule alone
python trail_of.py found.jsonl > followed.jsonl && python weight.py followed.jsonl
```

Raw output is in `results/`, one line of JSON per result:

| Files | What they hold |
|---|---|
| `guided-free-small` | the free-start comparison at 4 to 6 rounds |
| `trails-f`, `guided-free` | the climb on the cheapest trails, 7 to 9 rounds |
| `fast-trails-f`, `fast-guided-free` | the climb on any trail under a bound, 8 to 10 rounds |
| `exact-*`, `exactb-*`, `exactc-*` | the climbs with the exact key schedule: from 10, from 12, and from 11 with a looser bound |
| `sweep-step4`, `sweep-step5`, `sweep-hash4` | one flipped message bit, all 128 |
| `step5-lowbyte`, `step6` | the longer 5-round runs, and the 6-round runs |
| `hash4-first`, `hash4-mass` | the 4-round hash from fixed first chunks |
| `trails-c3-many`, `trails-c4-many`, `trails-f5-many`, `exact-trails-c4`, `trails-c-earlier` | trails checked for the two calls |
| `feasible-*` | the checks, one line per trail, in the same order |
| `keysched-f5` | the key schedule alone, for the 5-round free-start trails |
| `followed-step4`, `weight-step4` | the trails that the 4-round step collisions follow, and their costs |
