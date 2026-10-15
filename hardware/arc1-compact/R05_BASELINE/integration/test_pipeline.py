import struct
import unittest

from pipeline import (EndpointModel, HEADER, JOB, RESULT, MAX_OBJECTS, Native,
                      pack_jobs, reference_scene, run_scene, unpack_result)


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.native = Native()

    def setUp(self):
        self.endpoint = EndpointModel(self.native)
        self.endpoint.process(self.native.encode(1, 7, 0))
        self.record = reference_scene()[0][1]

    def submit(self, sequence=1, payload=None, epoch=7):
        return self.endpoint.process(self.native.encode(
            0x10, epoch, sequence, pack_jobs([self.record]) if payload is None else payload))

    def result(self, replies):
        return unpack_result(self.native.decode(replies[1])[3])

    def test_known_scene_and_budget(self):
        r = run_scene()
        self.assertEqual((r['objects'], r['transformed_objects'], r['visible'], r['culled']), (256, 64, 218, 38))
        self.assertEqual((r['request_bytes_per_frame'], r['response_bytes_per_frame']), (12416, 6528))
        self.assertFalse(r['hardware_verified'])

    def test_duplicate_replays_identical_result(self):
        first = self.submit()
        retry = self.submit()
        self.assertEqual(first[1], retry[1])
        self.assertEqual(self.endpoint.execution_batches, 1)

    def test_cache_loss_is_explicit_and_not_reexecution(self):
        self.submit()
        self.endpoint.cache.clear()
        self.assertEqual(self.result(self.submit()), (4, []))
        self.assertEqual(self.endpoint.execution_batches, 1)

    def test_same_epoch_hello_preserves_result(self):
        first = self.submit()
        self.endpoint.process(self.native.encode(1, 7, 0))
        self.assertEqual(first[1], self.submit()[1])
        self.assertEqual(self.endpoint.execution_batches, 1)

    def test_new_epoch_clears_cache_and_old_job_rejected(self):
        self.submit()
        self.endpoint.process(self.native.encode(1, 8, 0))
        self.assertFalse(self.endpoint.cache)
        old = self.submit(sequence=2)
        self.assertEqual(len(old), 1)
        self.assertEqual(struct.unpack('<HHI', self.native.decode(old[0])[3])[0], 17)
        self.assertEqual(self.result(self.submit(epoch=8))[0], 0)

    def test_application_errors_complete_without_leaking_credit(self):
        bad = [b'\0', HEADER.pack(2, 1, 1, 0) + JOB.pack(*self.record),
               HEADER.pack(1, 9, 1, 0) + JOB.pack(*self.record),
               HEADER.pack(1, 1, 0, 0), HEADER.pack(1, 1, 1, 1) + JOB.pack(*self.record),
               HEADER.pack(1, 1, 2, 0) + JOB.pack(*self.record)]
        for sequence, payload in enumerate(bad, 1):
            replies = self.submit(sequence, payload)
            self.assertNotEqual(self.result(replies)[0], 0)
            self.assertEqual(struct.unpack('<HHI', self.native.decode(replies[-1])[3])[:2], (2, 8))
        self.assertEqual(self.result(self.submit(len(bad) + 1))[0], 0)

    def test_corrupt_frame_does_not_consume_sequence(self):
        frame = bytearray(self.native.encode(0x10, 7, 1, pack_jobs([self.record])))
        frame[-1] ^= 1
        with self.assertRaises(ValueError):
            self.endpoint.process(bytes(frame))
        self.assertEqual(self.result(self.submit())[0], 0)

    def test_empty_job_is_rejected_by_transport_before_application(self):
        with self.assertRaises(ValueError):
            self.native.encode(0x10, 7, 1, b'')
        self.assertEqual(self.endpoint.execution_batches, 0)
        self.assertEqual(self.result(self.submit())[0], 0)

    def test_wrong_duplicate_payload_never_dispatches(self):
        self.submit()
        changed = list(self.record)
        changed[-1] += 1
        replies = self.submit(payload=pack_jobs([changed]))
        self.assertEqual(len(replies), 1)
        self.assertEqual(struct.unpack('<HHI', self.native.decode(replies[0])[3])[0], 21)
        self.assertEqual(self.endpoint.execution_batches, 1)

    def test_signed_fields_and_invalid_rectangle(self):
        record = list(self.record)
        record[0], record[2] = 65536, -65536
        status, rows = self.result(self.submit(payload=pack_jobs([record])))
        self.assertEqual(status, 0)
        self.assertEqual(rows[0][-1], 4)

    def test_job_count_limits_and_result_shape(self):
        self.assertEqual(MAX_OBJECTS, 85)
        for records in ([], [self.record] * 86):
            with self.assertRaises(ValueError): pack_jobs(records)
        with self.assertRaises(ValueError): unpack_result(HEADER.pack(1, 1, 1, 0))
        with self.assertRaises(ValueError): unpack_result(HEADER.pack(1, 1, 0, 99))

    def test_python_wire_fields_never_silently_wrap(self):
        for kind, epoch, sequence in [(257, 7, 0), (-1, 7, 0), (1, -1, 0),
                                      (1, 2**32, 0), (0x10, 7, -1),
                                      (0x10, 7, 2**32), (True, 7, 0)]:
            with self.assertRaises(ValueError):
                self.native.encode(kind, epoch, sequence)
        self.assertEqual(self.endpoint.execution_batches, 0)

    def test_result_success_count_and_flag_contract(self):
        with self.assertRaises(ValueError): unpack_result(HEADER.pack(1, 1, 0, 0))
        with self.assertRaises(ValueError):
            unpack_result(HEADER.pack(1, 1, 1, 0) + RESULT.pack(1, 0, 0, 1, 1, 8))


if __name__ == '__main__':
    unittest.main(verbosity=2)
