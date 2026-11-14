from winbase import *
from workbench.document_qt import show as show_document
def two():
    show_document(w); settle(); w.a_files.trigger(); settle()
two(); w.show_start(); settle(); where('Home over two tabs')
w.close_tab(w.tabs.currentIndex()); settle(); where('current tab closed under Home (as delivered)')
two(); v = field(); where('Field over two tabs')
w.close_tab(w.tabs.currentIndex()); settle(); where('current tab closed under the Field')
w.tabs.setCurrentIndex(0); settle(); two(); v = field()
w.tabs.setCurrentIndex(0); settle(); where('another tab made current under the Field')
finish()
