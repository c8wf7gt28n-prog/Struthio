This independent Python reference models the proposed ARC1 framing contract
using only the Python standard library. `codec.py` does not load the C codec.

`golden_vectors.json` contains complete little-endian frames, valid decoded
fields, and deliberate invalid/truncated/checksum/maximum-size examples. Most
invalid structural frames carry a correct CRC to isolate structural rejection.
The maximum payload is 4096 bytes and the maximum complete frame is 4120 bytes.

Regenerate vectors from the development root:

```sh
python3 protocol/reference/generate_vectors.py
```

Run the reference and C differential checks:

```sh
python3 -m unittest discover -s protocol/tests -p 'test_reference.py' -v
```

The ctypes checks require `protocol/build/libarc1_protocol.so`; if it is absent,
those checks are reported as skipped. Build that library before acceptance.
The reference-only tests still run without a C compiler or library.

These are host software checks. They establish no SPI signaling, F133 firmware
boot, FPGA fit/timing, BT820 operation, or measured hardware result.
