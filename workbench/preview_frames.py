"""Qt-independent bounded game frame discovery for HOST_SIM preview.

This examines only images explicitly numbered by the trace of the same host run.
A game preview is not a hardware simulation or an independent physical frame.
"""
from __future__ import annotations

from pathlib import Path

MAX_PREVIEW_IMAGES = 120


def discover(sim_dir, since=0, max_images=MAX_PREVIEW_IMAGES):
    """Return (frame_number, Path) pairs, sorted and strictly bound to the trace.

    Reject missing/old/invalid frames and never follow symlinks to outside the
    simulation output folder. Images are at most MAX_PREVIEW_IMAGES.
    """
    folder = Path(sim_dir).resolve()
    trace = folder / 'trace.txt'
    if not trace.is_file() or not 1 <= max_images <= MAX_PREVIEW_IMAGES:
        return []
    try:
        if trace.stat().st_mtime < since - 1:
            return []
        lines = trace.read_text(encoding='ascii').splitlines()
        identifiers = []
        last = -1
        for line in lines:
            parts = line.split()
            if len(parts) != 3 or len(parts[2]) != 16:
                return []
            frame = int(parts[0])
            int(parts[1], 16)
            int(parts[2], 16)
            if frame != last + 1:
                return []
            last = frame
            identifiers.append(frame)
        if len(identifiers) > 36000:
            return []
        found = []
        for frame in identifiers:
            candidate = folder / ('frame_%06d.ppm' % frame)
            if not candidate.is_file() or candidate.is_symlink():
                continue
            if candidate.stat().st_mtime < since - 1:
                continue
            if candidate.resolve().parent != folder:
                continue
            found.append((frame, candidate))
        return found[:max_images]
    except (ValueError, UnicodeError, OSError):
        return []
