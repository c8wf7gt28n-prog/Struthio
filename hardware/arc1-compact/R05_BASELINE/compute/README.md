# Compact transform/culling primitive

Read [CONTRACT.md](CONTRACT.md) for numeric, ABI and handshake details and
[VERIFICATION.md](VERIFICATION.md) for executed checks and limitations.

```
make check-c
make check-hdl IVERILOG=/path/to/iverilog VVP=/path/to/vvp
python3 tests/run_verification.py --iverilog /path/to/iverilog --vvp /path/to/vvp
```

Public C ABI: [arc1_transform.h](arc1_transform.h). The shared-library target is
`build/libarc1_transform.so`, suitable for ctypes. [tests/test_reference.py](tests/test_reference.py)
shows the exact structure declarations. Root code must serialize transport fields
explicitly rather than transmitting native C structs.

The C implementation needs C11 fixed-width integers; tests need GCC/Clang,
Python 3 and, for HDL simulation, Icarus with SystemVerilog support. No third-party
source/IP is bundled. Build products and generated vectors live in `build/`.
