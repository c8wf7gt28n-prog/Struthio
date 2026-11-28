#!/bin/bash
apt-get install -y gnupg 2>&1 | grep -E "newly installed"; apt-get clean
export GNUPGHOME=/root/g; rm -rf $GNUPGHOME; mkdir -m 700 $GNUPGHOME
gpg --batch --quiet --passphrase '' --quick-gen-key "Graphite trial archive key <archive@graphite.invalid>" ed25519 sign 1y 2>&1 | tail -1
cd /debs && rm -f InRelease Release.gpg && gpg --batch --yes --clearsign -o InRelease Release && gpg --batch --yes --export > /usr/share/keyrings/graphite-archive-keyring.gpg && echo signed
gpgconf --kill all 2>/dev/null
echo "deb [signed-by=/usr/share/keyrings/graphite-archive-keyring.gpg] file:/debs ./" > /etc/apt/sources.list.d/graphite.list
echo "-- apt-get update with ONLY the folder repository (no network source):"
apt-get update -o Dir::Etc::sourcelist=/etc/apt/sources.list.d/graphite.list -o Dir::Etc::sourceparts=/nonexistent 2>&1 | tail -3
apt-cache policy graphite graphite-session | grep -E "^[a-z]|Candidate|file:" | cut -c1-120
echo "-- with the network sources too: install by NAME from the folder repository (simulation)"
apt-get update 2>&1 | grep -E "^(E|W):|Reading" | head -3
apt-get install -s graphite-session 2>&1 | grep -E "newly installed|^E:|Inst graphite" | cut -c1-160
echo "-- upgrade path: a 1.0-2 would be offered by 'apt upgrade' from this repository (apt-cache madison):"; apt-cache madison graphite | cut -c1-120
