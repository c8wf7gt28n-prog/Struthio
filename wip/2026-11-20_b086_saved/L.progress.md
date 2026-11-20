# L (head and footer layout, Struthio icon, equalizer D, meters H) — progress

Patch: work/b086/L.patch (made WITH --binary: it carries branding/struthio/struthio.png; applies cleanly to HEAD).
Scripts: work/b086/L/scripts/ (save_patch.sh, run_frames.sh, frames.py, apply_check.sh).

Done:
- tools/cut_struthio.py + branding/struthio/struthio.png (373x512, SHA 2179...de45b) + README; RIGHTS.md note.
- workbench/struthio_mark.py; kp_logo.AppsButton paints the Struthio (mark 'struthio'); shell2.apps_mark both looks.
- shell2.TopBar.place: equalizer over the left column; menus from d.left + desk_qt.EDGE (8 px scaled); Struthio Apps.
- typebar_qt.place: box from d.left+EDGE, room button, send ends d.right-EDGE; send CUE_EDGE (cyan K / orange G), dark arrow.
- desktop_header_qt.DesktopMonitors: neon_meters.RingMeter (style H), centred evenly under the right column.
- equalizer_qt: style D with sprites; MOST 16; trace 2 min; near-limit words on the card; reduce motion holds still.
- tests changed to new truth: test_faces_find_light (MOST 16), test_kasandra_column + kasandra_window_probe (Struthio Apps).
- docs/DAILY_GUIDE.md updated.
- Frames in L/frames/ (both looks, 1920x1200 and 1366x768); measures: rest 0.78-0.84 % of a core, moving 1.34-1.61 %,
  paint 0.59-0.66 ms in place, 0.33-0.47 ms alone.

Next: final frames run after the card fix, result JSON.

FINISHED: final frames run done (L/frames/, 10 frames), patch saved and checked (applies cleanly), result written to
work/b086/L.build.result.json. The copy was deleted.
