#!/bin/sh
# Host tests (no ESP-IDF needed, any C compiler): sh tests/host/run.sh
#   test_power_policy.c    the power policy (slim4_power.c against the sdk/ stubs)
#   test_selftest_logic.c  the self-test decisions (slim4_selftest_logic.c, on a simulated board)
#   test_radio_logic.c     the radio RF plan, TX power cap, ping packets and RADIO self-test line
set -e
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../.." && pwd)
out=$(mktemp)
trap 'rm -f "$out"' EXIT
for test in test_power_policy test_selftest_logic test_radio_logic; do
    echo "== $test"
    ${CC:-cc} -std=c11 -Wall -Wextra -Wno-unused-function -Wno-unused-parameter -Wno-unused-variable \
        -I "$here/sdk" -I "$root/components/slim4_bsp/include" -I "$root/components/slim4_types/include" \
        "$here/$test.c" -o "$out"
    "$out"
done
