# Cryptanalysis

<img src="https://vibegif.direct-img.link/octopus/wiggle.webp" width="128" alt="An octopus wiggling its arms">

Attempts to break SpeckHashX, kept in one place so that anyone can check them, repeat them and go further.

> **This is not a review.** Everything here so far was done by the author of the hash with an AI model.
> Nobody independent has analysed SpeckHashX. The numbers below say how far simple, automated attacks got.
> They do not say that better attacks do not exist.

## How to read this

SpeckHashX mixes each chunk with 34 rounds of Speck. A hash cannot be tested by trying messages until two collide:
at full strength that takes about 2¹²⁸ tries, far beyond any computer. So the hash is weakened on purpose, to
3 rounds, 4 rounds and so on, and attacked at each strength. The round count where the attacks stop working,
compared with 34, is the margin.

## Where things stand

| Attack | Breaks | Out of | From |
|---|---|---|---|
| Two messages with the same hash | 3 rounds | 34 | [01](01-reduced-rounds/README.md) |
| A message with a given hash | 4 rounds | 34 | [03](03-preimages/README.md) |
| Two chunks with the same step output, from a state the attacker picks | 5 rounds | 34 | [01](01-reduced-rounds/README.md), [02](02-guided-collisions/README.md) |
| Two step inputs with the same step output, from two different states | 12 rounds | 34 | [02](02-guided-collisions/README.md) |
| A flipped input bit that still shows in the output | 11 rounds | 34 | [01](01-reduced-rounds/README.md) |
| Statistical tests of the full hash | none failed | | [01](01-reduced-rounds/README.md) |

Only the first two rows are attacks on the hash itself. The next two give the attacker control of the hash's inner state,
which a real attacker does not have. Attacks of this kind are a standard way to measure a hash's margin.

These are the attacks automated tools found in a few hours of computing. They do not show where dedicated attacks would stop.

[02](02-guided-collisions/README.md) found that the trail costs 01 gives for message-only differences belong to trails
that cannot happen, because the two cipher calls of a step cannot both follow them. 01's lower bounds still hold.

## Analyses

| # | When | What was tried |
|---|---|---|
| [01](01-reduced-rounds/README.md) | November 2026 | A first look: collisions found by a SAT solver, differential trails, bit-flip statistics, and collision counts on short outputs of the full hash. |
| [02](02-guided-collisions/README.md) | November 2026 | Collisions found by a SAT solver given a hint: a trail or a message difference. Which trails the two cipher calls of a step can follow. |
| [03](03-preimages/README.md) | November 2026 | Preimages found by a SAT solver, for messages of 8 to 15 bytes. |

## Open targets

Each of these would be new. If you reach one, please open an issue.

1. Two messages with the same 4-round hash. In 02 no single flipped message bit worked from a random state.
2. A message with a given 5-round hash.
3. A 6-round step collision from one chosen state, or a 13-round one from two different states.
4. A bias in the step output at 12 rounds or more.
5. A trail model that accounts for both cipher calls of a step. In 02, every 4-round message-only trail it gave was impossible with both calls.
6. Anything by rotational, boomerang, linear or algebraic methods. None of these has been tried.

## Layout

One folder per analysis, `NN-name/`, and each one stands alone:

- `README.md` says what was asked, how it was tested, what came out and what it does not show.
- `tools/` holds the code that produced the results.
- `results/` holds the raw output.

## Adding an analysis

1. Make the next numbered folder, with a `README.md`, a `tools/` folder and a `results/` folder.
2. Copy any code you want to reuse from an earlier analysis into the new `tools/` and change it there.
   Never change an earlier analysis's code: its results have to keep matching it.
3. Say who did the work and with what, and give the commands that reproduce it.
4. Add a row to **Analyses**, and update **Where things stand** and **Open targets** if a number moved.
