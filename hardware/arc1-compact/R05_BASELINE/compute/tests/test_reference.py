#!/usr/bin/env python3
"""Exercise the public shared-library ABI against the independent Python oracle."""
import argparse
import ctypes as C
from pathlib import Path
from generate_vectors import vectors


class Job(C.Structure):
    _fields_ = [(k, C.c_int32) for k in ('xmin', 'ymin', 'xmax', 'ymax', 'm00', 'm01', 'm02', 'm10', 'm11', 'm12')]
    _fields_ += [('viewport_width', C.c_uint16), ('viewport_height', C.c_uint16), ('tag', C.c_uint32)]


class Result(C.Structure):
    _fields_ = [('tag', C.c_uint32)] + [(k, C.c_int32) for k in ('minx', 'miny', 'maxx', 'maxy')] + [('flags', C.c_uint32)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('library', type=Path)
    args = parser.parse_args()
    lib = C.CDLL(str(args.library.resolve()))
    lib.arc1_transform_rectangle.argtypes = [C.POINTER(Job), C.POINTER(Result)]
    lib.arc1_transform_rectangle.restype = None
    lib.arc1_transform_batch.argtypes = [C.POINTER(Job), C.POINTER(Result), C.c_size_t]
    lib.arc1_transform_batch.restype = None
    assert C.sizeof(Job) == 48 and C.sizeof(Result) == 24 and Job.tag.offset == 44
    records = list(vectors())
    jobs = (Job * len(records))(*(Job(*job) for job, _ in records))
    results = (Result * len(records))()
    lib.arc1_transform_batch(None, None, 0)
    lib.arc1_transform_batch(jobs, results, len(records))
    for i, ((job, expected), actual) in enumerate(zip(records, results)):
        single = Result()
        lib.arc1_transform_rectangle(C.byref(jobs[i]), C.byref(single))
        for result in (actual, single):
            got = tuple(getattr(result, k) for k in ('minx', 'miny', 'maxx', 'maxy', 'flags'))
            assert got == expected and result.tag == job[-1], (i, got, expected, result.tag)
    print(f'PASS C ABI: {len(records)} batch and {len(records)} scalar oracle comparisons; zero-count/null batch.')


if __name__ == '__main__':
    main()
