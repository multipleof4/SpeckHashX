# Output length and security

SpeckHashX lets you choose how many bytes of hash you get.
This page explains what that choice does to security.

## The short version

Security grows with the output length up to 32 bytes, then stays the same.
A 64-byte or 1,000-byte hash is exactly as strong as a 32-byte one.

| Output | Tries to find two messages with the same hash | Tries to find a message for a given hash |
|---|---|---|
| 8 bytes | 2³² | 2⁶⁴ |
| 16 bytes | 2⁶⁴ | 2¹²⁸ |
| 32 bytes | 2¹²⁸ | 2²⁵⁶ |
| 64 bytes or more | 2¹²⁸ | 2²⁵⁶ |

These are the costs of brute force; no faster attack is known.
The design is new and has not been reviewed by anyone, so they are its targets, not proven facts.

## Why it stays the same

However long the message and the output are, the hash keeps 32 bytes of state inside.
The output is that state stretched to the length you asked for.

Two messages that reach the same state give the same hash, whatever the length.
Finding such a pair takes about 2¹²⁸ tries whether the output is 32 bytes or 1,000,
so a longer output cannot be harder to attack than the 32 bytes behind it.

## Below 32 bytes

Every byte you remove divides the first number by 16 and the second by 256.
Use 32 bytes when someone might try to forge a match:
the 2⁶⁴ tries for a 16-byte hash are within reach of a well-funded attacker.

## Above 32 bytes

A longer output gives more bytes, not more strength.
It is for when you need to fill something larger,
such as a long ID or a stream of random-looking bytes.

## Each length is its own hash

The output length is mixed in at the start, so hashes of different lengths are unrelated:
a 16-byte hash is not the start of the 32-byte hash of the same message.
Ask for the length you want; cutting a longer hash down does not give the shorter one.

## Limits

The Rust crate takes any length that fits in memory.
The npm package accepts up to 2³⁰ bytes (about 1 GB).

As text, bases 2, 4, 8, 16, 32 and 64 take a hash of any length; the other bases take up to 1,024 bytes ([why](base.md#speed)).
