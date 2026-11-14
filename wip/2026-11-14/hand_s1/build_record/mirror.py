"""Mirror every changed or added file of the worktree (against bbf033b) to hand_mirror/<path>. Run from the worktree."""
import shutil, subprocess
from pathlib import Path
MIRROR = Path('/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/hand_mirror')
changed = subprocess.run(['git', 'diff', '--name-only', 'bbf033b'], capture_output=True, text=True, check=True).stdout.split()
added = subprocess.run(['git', 'ls-files', '--others', '--exclude-standard'], capture_output=True, text=True, check=True).stdout.split()
names = sorted(set(changed) | set(added))
for name in names:
    if name.startswith('.claude/'):continue
    src = Path(name)
    if not src.is_file():continue
    dst = MIRROR / name;dst.parent.mkdir(parents=True, exist_ok=True);shutil.copy2(src, dst)
print(len(names), 'files mirrored');print('\n'.join(names))
