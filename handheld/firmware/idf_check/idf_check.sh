#!/usr/bin/env bash
# STRUTHIO HANDHELD · compile every firmware source against the REAL ESP-IDF
# headers (syntax and types only; no Xtensa toolchain needed, nothing linked).
#
# Fetches by git, pinned (sparse, headers only, ~150 MB, cached in
# handheld/build/idf_check):
#   ESP-IDF v5.5.5; esp_lcd_axs15231b 2.1.1 (esp-iot-solution @88152bf);
#   esp_io_expander 1.2.1 + tca9554 2.0.3, esp_lcd_touch 1.2.1 (esp-bsp @73ee07b);
#   esp_codec_dev 1.5.2 (esp-adf @d6e1ef5)
# generates the real sdkconfig.h from ESP-IDF's Kconfig and our
# sdkconfig.defaults with Espressif's kconfgen (pip esp-idf-kconfig), then
# checks main/*.c, main/*.cpp and the struthio component sources with
# -Wall -Wextra -Werror: a 32-bit target, newlib headers (apt libnewlib-dev),
# ESP-IDF's own headers as system headers.
#
# This catches API mismatches (wrong struct fields, signatures, missing
# functions) that the host shim (host_test, make compile) cannot. It does NOT
# replace `idf.py build`: no code generation, linking or Xtensa-specific checks.
#   handheld/firmware/idf_check/idf_check.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
FW="$(cd "$HERE/.." && pwd)"
H="$(cd "$FW/.." && pwd)"
C="${IDF_CHECK_CACHE:-$H/build/idf_check}"
mkdir -p "$C"
fetch() {   # dir url ref paths...
  local dir=$1 url=$2 ref=$3; shift 3
  if [ ! -d "$C/$dir/.git" ]; then
    git clone -q --filter=blob:none --no-checkout "$url" "$C/$dir"
    git -C "$C/$dir" sparse-checkout set --no-cone "$@"
    git -C "$C/$dir" fetch -q --depth 1 origin "$ref"
    git -C "$C/$dir" checkout -q FETCH_HEAD
  fi
}
fetch esp-idf https://github.com/espressif/esp-idf.git v5.5.5 \
  '/Kconfig' '/sdkconfig.rename*' '/components/**/include/**' '/components/**/*.h' '/components/**/Kconfig*' \
  '/components/**/sdkconfig.rename*' '/components/freertos/**' '/components/xtensa/**' '/components/soc/esp32s3/**' '/components/esp_rom/**'
fetch iot https://github.com/espressif/esp-iot-solution.git 88152bff24d5fbc05ff2ffed3d5208c247711ded '/components/display/lcd/esp_lcd_axs15231b/**'
fetch bsp https://github.com/espressif/esp-bsp.git 73ee07b1ad56f865f13a2739be8bb6808c1da58a \
  '/components/io_expander/esp_io_expander/**' '/components/io_expander/esp_io_expander_tca9554/**' '/components/lcd_touch/esp_lcd_touch/**'
fetch adf https://github.com/espressif/esp-adf.git d6e1ef5ccf29ca52dcb8332a3232505366755012 '/components/esp_codec_dev/**'
python3 -c "import kconfgen" 2>/dev/null || { echo "need: pip install esp-idf-kconfig"; exit 2; }
[ -d /usr/include/newlib ] || { echo "need: apt-get install libnewlib-dev"; exit 2; }

IDF="$C/esp-idf"; I="$IDF/components"
# --- sdkconfig.h, as the build system would generate it --------------------------------
{
  find "$I" -maxdepth 2 -name Kconfig | sort | sed 's/.*/source "&"/'
  for k in "$FW"/components/*/Kconfig "$C"/adf/components/esp_codec_dev/Kconfig "$C"/bsp/components/io_expander/esp_io_expander/Kconfig \
           "$C"/bsp/components/lcd_touch/esp_lcd_touch/Kconfig; do [ -f "$k" ] && echo "source \"$k\""; done
} > "$C/kconfigs.in"
find "$I" -maxdepth 2 -name Kconfig.projbuild | sort | sed 's/.*/source "&"/' > "$C/kconfigs_projbuild.in"
printf 'CONFIG_IDF_TARGET="esp32s3"\n' > "$C/target.defaults"
( cd "$IDF" && python3 -m kconfgen --kconfig Kconfig --sdkconfig-rename sdkconfig.rename --config "$C/sdkconfig" \
    --defaults "$C/target.defaults" --defaults "$FW/sdkconfig.defaults" \
    --env IDF_TARGET=esp32s3 --env IDF_PATH="$IDF" --env IDF_TOOLCHAIN=gcc --env IDF_INIT_VERSION=5.5.5 --env IDF_ENV_FPGA= \
    --env IDF_CI_BUILD= --env IDF_DOC_BUILD= --env IDF_MINIMAL_BUILD=n \
    --env COMPONENT_KCONFIGS_SOURCE_FILE="$C/kconfigs.in" --env COMPONENT_KCONFIGS_PROJBUILD_SOURCE_FILE="$C/kconfigs_projbuild.in" \
    --output header "$C/sdkconfig.h" --output config "$C/sdkconfig" >/dev/null 2>"$C/kconfgen.log" ) \
  || { cat "$C/kconfgen.log"; exit 1; }
# --- include path: ESP-IDF for esp32s3 (other targets' trees left out) ---------------------
python3 - "$I" "$C" > "$C/incs.txt" <<'PY'
import os, sys
I, C = sys.argv[1], sys.argv[2]
others = {'esp32','esp32s2','esp32c2','esp32c3','esp32c5','esp32c6','esp32c61','esp32h2','esp32h21','esp32h4','esp32p4','linux','riscv'}
first = [f'{I}/freertos/config/include', f'{I}/freertos/config/include/freertos', f'{I}/freertos/config/xtensa/include',
  f'{I}/freertos/FreeRTOS-Kernel/include', f'{I}/freertos/FreeRTOS-Kernel/include/freertos', f'{I}/freertos/FreeRTOS-Kernel/portable/xtensa/include',
  f'{I}/freertos/FreeRTOS-Kernel/portable/xtensa/include/freertos', f'{I}/freertos/esp_additions/include', f'{I}/freertos/esp_additions/include/freertos',
  f'{I}/xtensa/esp32s3/include', f'{I}/xtensa/include', f'{I}/xtensa/deprecated_include', f'{I}/esp_rom/esp32s3/include',
  f'{I}/esp_rom/esp32s3/include/esp32s3', f'{I}/esp_rom/esp32s3', f'{I}/soc/esp32s3/include', f'{I}/soc/esp32s3/register',
  f'{I}/hal/esp32s3/include', f'{I}/esp_hw_support/include/soc', f'{I}/esp_hw_support/port/esp32s3/include', f'{I}/esp_hw_support/port/esp32s3/private_include']
rest = []
for root, ds, fs in os.walk(I):
    parts = root[len(I) + 1:].split('/')
    if any(p in others for p in parts) or parts[-1] in ('test', 'test_apps', 'tests', 'host_test', 'examples'):
        ds[:] = []; continue
    if os.path.basename(root) in ('include', 'platform_include', 'private_include', 'priv_include') or root.endswith('/esp32s3'):
        rest.append(root)
dirs = first + sorted(set(rest) - set(first))
dirs += [f'{C}/iot/components/display/lcd/esp_lcd_axs15231b/include', f'{C}/bsp/components/io_expander/esp_io_expander/include',
         f'{C}/bsp/components/io_expander/esp_io_expander_tca9554/include', f'{C}/bsp/components/lcd_touch/esp_lcd_touch/include',
         f'{C}/adf/components/esp_codec_dev/include', f'{C}/adf/components/esp_codec_dev/interface', f'{C}/adf/components/esp_codec_dev/device/include']
print('\n'.join(d for d in dirs if os.path.isdir(d)))
PY
# --- compile ---------------------------------------------------------------------------
INC=$(sed 's/^/-isystem /' "$C/incs.txt" | tr '\n' ' ')
XP="-isystem $FW/components/XPowersLib/src -isystem $FW/components/XPowersLib/src/REG"
OURS="-I$FW/main -I$H/core -I$H/render -I$H/audio -I$C"
DEFS="-DESP_PLATFORM -DIDF_VER=\"v5.5.5\" -D_GNU_SOURCE -D__XTENSA__=1 -D_POSIX_READER_WRITER_LOCKS"
GCCINC=$(gcc -print-file-name=include)
fails=0
for f in "$FW"/main/*.c "$FW"/main/*.cpp "$H"/core/*.c "$H"/render/*.c "$H"/audio/*.c; do
  case "$f" in
    *.cpp) cmd=(g++ -std=gnu++2b -m32 -fsyntax-only -nostdinc -nostdinc++ -isystem "$HERE/cxxshim" -isystem "$GCCINC" -isystem /usr/include/newlib) ;;
    *)     cmd=(gcc -std=gnu17 -m32 -fsyntax-only -nostdinc -isystem "$GCCINC" -isystem /usr/include/newlib) ;;
  esac
  if out=$("${cmd[@]}" $DEFS -Wall -Wextra -Werror $INC $XP $OURS "$f" 2>&1); then echo "  ok   ${f#$H/}"; else echo "  FAIL ${f#$H/}"; echo "$out" | grep -E "error" | head -5; fails=$((fails + 1)); fi
done
if [ $fails -eq 0 ]; then echo "PASS: firmware compiles against the real ESP-IDF 5.5.5 headers (syntax + types; not an idf.py build)"; else echo "FAIL: $fails file(s)"; exit 1; fi
