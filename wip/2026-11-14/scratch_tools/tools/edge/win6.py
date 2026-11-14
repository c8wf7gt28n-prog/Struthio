from winbase import *
note = root / 'probe_note.txt'; note.write_text('one line of ordinary text\n')
ed = w.open_document(note); settle(); where('a text file is open')
print('   focus:', type(app.focusWidget()).__name__)
before = snap(); print('   before:', {k2: before[k2] for k2 in ('context_bar', 'doc_info', 'workspace_status', 'title', 'focus')})
v = field(); where('Field over the text file')
QTest.keyClick(v, Qt.Key_Escape); settle(); where('Esc'); after = snap()
print('   after: ', {k2: after[k2] for k2 in ('context_bar', 'doc_info', 'workspace_status', 'title', 'focus')})
diff(before, after, 'text file -> Field -> Esc')
# the same through a room opener instead of Esc
v = field(); w.a_files.trigger(); settle(); where('Files opened from the Field'); 
w.tabs.setCurrentWidget(ed); settle(); mid = snap(); diff(before, mid, 'text file -> Field -> Files -> back to the file tab')
# Home path for comparison
w.show_start(); settle(); w._close_start(); settle(); diff(before, snap(), 'text file -> Home -> leave Home (the program as delivered)')
finish()
