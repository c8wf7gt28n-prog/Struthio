#!/bin/bash
# save_dist.sh: copy the small, finished outputs of the 1.1 panels and builders from scratch into the repository and push,
# so a usage reset or a replaced container loses at most a few minutes. Safe to run at any time, as often as wanted.
#   bash wip/build_tools/save_dist.sh          one save
#   bash wip/build_tools/save_dist.sh loop     a save every 5 minutes for about 115 minutes (run it in the background)
# It copies only notes (.md, .json, small .py prototypes, .txt summaries) at most two folders deep under $S/work/dist,
# never a throwaway copy of the tree, a chroot, frames or logs; files over 400 kB are skipped. It commits only its own
# folder (a path-limited commit), so it never carries someone else's staged work.
S=/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad
R=/home/user/Struthio; D=$S/work/dist; OUT=$R/wip/2026-11-27_distribution/partial
PRIVATE=$S/work/private_patterns.txt        # scratch only: the owner's own details, one per line; never in the repository

one() {
  [ -d "$D" ] || { echo "no $D (scratch gone?)"; return 0; }
  mkdir -p "$OUT"
  cd "$D" || return 0
  find . -maxdepth 3 -type f \( -name '*.md' -o -name '*.json' -o -name '*.txt' -o -name '*.sh' -o -path '*/proto/*.py' \) -size -400k \
      -not -path '*/copy/*' -not -path '*/copy_*' -not -path '*/chroot*' -not -path '*/frames/*' -not -path '*/wraphome*' \
      -not -path '*/tree/*' -not -path '*/raw/*' -not -name 'private_patterns.txt' -print0 2>/dev/null |
    while IFS= read -r -d '' f; do
      if [ -f "$PRIVATE" ] && grep -q -i -F -f "$PRIVATE" "$f" 2>/dev/null; then echo "SKIPPED (holds the owner's details): $f"; continue; fi
      if grep -q -i 'privaterelay' "$f" 2>/dev/null; then echo "SKIPPED (an address): $f"; continue; fi
      mkdir -p "$OUT/$(dirname "$f")"; cp -p "$f" "$OUT/$f"
    done
  # the briefs of running builders and their saved patches are small text too
  for g in "$S"/work/briefs/110_*.md; do [ -f "$g" ] && mkdir -p "$OUT/briefs" && cp -p "$g" "$OUT/briefs/"; done
  # the builders' own saves: their patch (under 3 MB), their notes and their result
  mkdir -p "$OUT/b110"
  find "$S/work/b110" -maxdepth 1 -type f \( -name '*.patch' -o -name '*.progress.md' -o -name '*.build.result.json' \) -size -3000k -print0 2>/dev/null |
    while IFS= read -r -d '' f; do
      if [ -f "$PRIVATE" ] && grep -q -i -F -f "$PRIVATE" "$f" 2>/dev/null; then echo "SKIPPED (holds the owner's details): $f"; continue; fi
      cp -p "$f" "$OUT/b110/"
    done
  cd "$R" || return 0
  for try in 1 2 3; do
    git add -A "wip/2026-11-27_distribution/partial" 2>/dev/null && break; sleep 5
  done
  if git diff --cached --quiet -- "wip/2026-11-27_distribution/partial"; then echo "$(date -u +%H:%M) nothing new"; return 0; fi
  for try in 1 2 3; do
    git commit -q -m "Saved: partial outputs of the 1.1 panels ($(date -u +%H:%M) UTC)

Co-Authored-By: Claude Fable 5.2 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01SSUMdyhHQH2idKFXpgDCV8" -- "wip/2026-11-27_distribution/partial" && break; sleep 5
  done
  for try in 1 2 3 4; do git push -q -u origin claude/epic-galileo-c7k11y && break; sleep $((try*4)); done
  echo "$(date -u +%H:%M) saved: $(git log --oneline -1 | cut -c1-70)"
}

if [ "$1" = loop ]; then for i in $(seq 1 23); do one; sleep 300; done; one; else one; fi
