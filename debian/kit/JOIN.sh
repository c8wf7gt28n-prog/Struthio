#!/usr/bin/env bash
# 1.1 PK1: put the kit's repository together: check the kit's files (KIT.sha256), unpack every KAS_NNN.zip into
# ./repo, check every piece by sha256, join the pieces of each large file, check the joined file, then check every file
# of the repository (SHA256SUMS). Needs only bash, coreutils and python3 (for the ZIPs; unzip is not needed).
#   bash JOIN.sh          (in the kit's folder, as your ordinary user)
set -euo pipefail
cd "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ -f KIT.sha256 ]]; then
  sha256sum --quiet -c KIT.sha256 || { echo 'A kit file does not match KIT.sha256: copy the kit again.' >&2; exit 1; }
fi
rm -rf repo
for z in KAS_*.zip; do python3 -m zipfile -e "$z" . ; done
while read -r sum name whole; do
  [[ -n "$sum" ]] || continue
  if [[ "$whole" == WHOLE ]]; then
    cat "repo/$name".[0-9][0-9][0-9] > "repo/$name"
    echo "$sum  repo/$name" | sha256sum --quiet -c - || { echo "The joined file $name does not match." >&2; exit 1; }
    rm -f "repo/$name".[0-9][0-9][0-9]
  else
    echo "$sum  repo/$name" | sha256sum --quiet -c - || { echo "The piece $name does not match." >&2; exit 1; }
  fi
done < PIECES.sha256
( cd repo && sha256sum --quiet -c ../SHA256SUMS ) || { echo 'A file of the repository does not match SHA256SUMS.' >&2; exit 1; }
echo "JOINED AND CHECKED: $(ls repo/*.deb | wc -l) packages in $(pwd)/repo"
