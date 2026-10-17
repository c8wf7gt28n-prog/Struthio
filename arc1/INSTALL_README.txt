ARC-1 WORKBENCH R06 - PORTABLE OR DRAG-TO-INSTALL (WINDOWS 11)

Portable, Finder-like workflow:
  1. In File Explorer, right-click the ZIP and choose Extract All.
  2. Drag the extracted ARC-1 Workbench folder into Documents, Desktop,
     or another folder you own. You do NOT need to install into Program Files.
  3. Double-click START_ARC1.cmd in the extracted folder.

Optional per-user 'My Apps' installer:
  1. Extract the ZIP first. Do not start the installer inside the ZIP viewer.
  2. Double-click INSTALL_ARC1.cmd.
  3. Drag the ARC-1 icon into My Apps, or choose Install to My Apps.
  4. Confirm copying into %LOCALAPPDATA%\Programs\ARC-1 Workbench.
  5. The installer creates a Start Menu shortcut; no admin rights required.

Prerequisite: Python 3.11+ with tkinter. C compiler and RISC-V LLVM tools
are additionally needed for corresponding SDK/firmware builds. Windows 11
has not been validated on a real host yet. Linux Xvfb test is not proof of it.

Drag-and-drop in the file browser:
  - Drag a file onto an existing folder INSIDE Workbench to copy (not move).
  - External Explorer .arc1cart drag/drop is available only when optional
    'tkinterdnd2' / TkDND has been installed in your Python environment.
  - Without that optional dependency, use Cartridge > Import instead.
  - Files are verified before import; existing cartridge filenames require approval.

This release does not support hardware flashing, live USB cartridge reads,
or bootable ARC-1 firmware images.
