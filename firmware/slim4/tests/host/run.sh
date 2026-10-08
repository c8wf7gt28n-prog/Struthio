#!/bin/sh
# Host test of the power policy (no ESP-IDF needed, any C compiler): sh tests/host/run.sh
set -e
here=$(cd "$(dirname "$0")" && pwd)
root=$(cd "$here/../.." && pwd)
out=$(mktemp)
trap 'rm -f "$out"' EXIT
${CC:-cc} -std=c11 -Wall -Wextra -Wno-unused-function -Wno-unused-parameter -Wno-unused-variable \
    -I "$here/sdk" -I "$root/components/slim4_bsp/include" -I "$root/components/slim4_types/include" \
    "$here/test_power_policy.c" -o "$out"
"$out"
