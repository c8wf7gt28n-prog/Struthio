# L6b progress (builder notes)
- start: read brief, plan (1-4, L6, L6b, A1, L4, K2..K9), L6's notes.
- DONE (unrun): workbench/home_trash.py (freedesktop Trash: put/entries/restore, .trashinfo first with O_EXCL, one rename,
  other drive refused); files_service: files.trash of a Home path -> home Trash (row kept in files_trash as '~trash:<name>'),
  files.trash_list gives 'home', files.restore restores Home Trash entries; living_nav.in_delete knows the home Trash;
  depths._place allows Files and Home (REVISIONS_OUTSIDE otherwise); A1 app_files (her_change for her work, watched keys by
  place_of), app_files_qt (in_files = Files or Home; session_of by place_of); depths_qt.record for Home; K5 _file her_change on
  edit + place_of; K9 _resolve her_change; K6 inputs place_of.
- DONE (unrun): workbench/home_files_qt.py (menu provider for 'home-file'/'home-folder' targets, rename/move/new folder/delete
  with Undo line, drag-move in the tree, focused Home file watcher recording revisions, Trash rows in DELETE, count);
  context_menu (find_cabinet target, REST, TARGET_GLYPH, PROVIDERS), computer_tree_qt.install, files_qt TrashTab, cabinet_qt +
  shell2 count, trash_can_qt drop of Home rows.
- 11:45 backend smoke 29/29 PASS (run.sh backend on the copy; stand-in Writer entry re-saves the letter through real soffice
  headless). Fixed: files.trash refuses your home / a folder holding Graphite's workspace (home_trash.holds_graphite); the tree
  offers no change for those either.
- 11:55 window smoke 13/13 in day 1920x1200 and kasandra 1366x768 (pair.sh). Words: on screen the place is always DELETE
  (test_delete_words: no "Trash" string constant in workbench/*.py); the menu row is "Delete"; spec words are bytes.
  Menu provider order: home before apps, so "Open in LibreOffice Writer" is first.
- 12:00 frames read (day 1920, kasandra 1366, graphite 1920): Undo line laid out words-over-buttons; DELETE room's Files lead
  says "Nothing from Files is in DELETE." when only home things are there. Final runs (final.sh): backend 29/29, window 13/13
  in day 1920x1200, kasandra 1366x768, graphite 1920x1200. Patch applies to clean HEAD; record_registry --check: no differences.
- DONE: result file L6b.build.result.json written; throwaway copy deleted; frames kept in b100/L6b/frames.
- (old) NEXT: copy + smoke (backend: trash/restore/rename/move/mkdir + A1 open of ~/Documents letter with stand-in LibreOffice +
  grant ~/Documents note step + /etc stop), then window smoke + frames (day 1920x1200, kasandra 1366x768).
