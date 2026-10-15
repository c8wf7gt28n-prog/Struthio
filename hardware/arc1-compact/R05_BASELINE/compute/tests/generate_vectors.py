#!/usr/bin/env python3
"""Independent unbounded-integer oracle; no C/RTL arithmetic is imported."""
import argparse
import random
from pathlib import Path

Q = 1 << 16
LO, HI = -(1 << 31), (1 << 31) - 1


def oracle(job):
    x0, y0, x1, y1, a, b, c, d, e, f, width, height, tag = job
    if x0 > x1 or y0 > y1 or not width or not height:
        return (0, 0, 0, 0, 4)
    corners = []
    clipped = False
    for x, y in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
        transformed = []
        for k0, k1, t in ((a, b, c), (d, e, f)):
            exact = k0 * x + k1 * y + t * Q
            sign = -1 if exact < 0 else 1
            rounded = sign * ((abs(exact) + Q // 2) // Q)
            clipped |= not LO <= rounded <= HI
            transformed.append(max(LO, min(HI, rounded)))
        corners.append(transformed)
    xs, ys = zip(*corners)
    box = (min(xs), min(ys), max(xs), max(ys))
    visible = box[2] >= 0 and box[3] >= 0 and box[0] <= width * Q and box[1] <= height * Q
    return box + (int(visible) | (int(clipped) << 1),)


def vectors():
    identity = (Q, 0, 0, 0, Q, 0)
    manual = [
        ((0, 0, Q, Q, *identity, 1024, 600), (0, 0, Q, Q, 1)),
        ((0, 0, Q, Q, 0, -Q, 3*Q, Q, 0, 2*Q, 4, 4), (2*Q, 2*Q, 3*Q, 3*Q, 1)),
        ((0, 0, Q, Q, -Q, 0, 0, 0, Q, 0, 4, 4), (-Q, 0, 0, Q, 1)),
        ((0, 0, Q, Q, Q, 0, -2*Q, 0, Q, 0, 4, 4), (-2*Q, 0, -Q, Q, 0)),
        ((1, 0, 1, 0, Q//2, 0, 0, Q//2, 0, 0, 1, 1), (1, 1, 1, 1, 1)),
        ((1, 0, 1, 0, -Q//2, 0, 0, Q//2, 0, 0, 1, 1), (-1, 1, -1, 1, 0)),
        ((LO, LO, LO, LO, LO, LO, LO, 0, Q, 0, 1, 1), (HI, LO, HI, LO, 2)),
        ((HI, HI, HI, HI, LO, LO, LO, 0, 0, 0, 1, 1), (LO, 0, LO, 0, 2)),
        ((LO, LO, LO, LO, LO, HI, 0, 0, 0, 0, 1, 1), (Q//2, 0, Q//2, 0, 1)),
        ((Q, 0, 0, Q, *identity, 1, 1), (0, 0, 0, 0, 4)),
        ((0, 0, Q, Q, *identity, 0, 1), (0, 0, 0, 0, 4)),
        ((0, 0, Q, Q, *identity, 1, 0), (0, 0, 0, 0, 4)),
        ((Q, Q, Q, Q, *identity, 1, 1), (Q, Q, Q, Q, 1)),
        ((HI, HI, HI, HI, *identity, 65535, 65535), (HI, HI, HI, HI, 1)),
        ((HI, 0, HI, 0, Q+1, 0, 0, 0, Q, 0, 65535, 1), (HI, 0, HI, 0, 3)),
    ]
    for i, (inputs, expected) in enumerate(manual):
        job = inputs + (i,)
        assert oracle(job) == expected, (i, oracle(job), expected)
        yield job, expected
    rng = random.Random(0xA1C05)
    tag = len(manual)
    for _ in range(450):
        bounds = [rng.randint(LO, HI) for _ in range(4)]
        if rng.randrange(5):
            bounds = [min(bounds[0], bounds[2]), min(bounds[1], bounds[3]),
                      max(bounds[0], bounds[2]), max(bounds[1], bounds[3])]
        job = (*bounds, *(rng.randint(LO, HI) for _ in range(6)),
               rng.randint(0, 65535), rng.randint(0, 65535), tag)
        yield job, oracle(job)
        tag += 1
    for _ in range(450):
        x, y = rng.randint(-1000*Q, 1000*Q), rng.randint(-1000*Q, 1000*Q)
        bounds = (x, y, x + rng.randint(0, 512*Q), y + rng.randint(0, 512*Q))
        matrix = (rng.randint(-4*Q, 4*Q), rng.randint(-4*Q, 4*Q), rng.randint(-1024*Q, 1024*Q),
                  rng.randint(-4*Q, 4*Q), rng.randint(-4*Q, 4*Q), rng.randint(-600*Q, 600*Q))
        job = (*bounds, *matrix, 1024, 600, tag)
        yield job, oracle(job)
        tag += 1
    # Sub-LSB/tie cases and signed extremes around exact output boundaries.
    values = [LO, LO+1, -Q-1, -Q, -32769, -32768, -1, 0, 1, 32767, 32768, Q, HI-1, HI]
    for _ in range(250):
        x, y = rng.choice(values), rng.choice(values)
        job = (x, y, x, y, *(rng.choice(values) for _ in range(6)),
               rng.choice((1, 1024, 32768, 65535)), rng.choice((1, 600, 32768, 65535)), tag)
        yield job, oracle(job)
        tag += 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    records = list(vectors())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('w') as stream:
        for job, result in records:
            stream.write(' '.join(f'{v & 0xffffffff:08x}' for v in (*job, *result)) + '\n')
    print(f'Generated {len(records)} deterministic oracle vectors (15 hand-checked cases).')


if __name__ == '__main__':
    main()
