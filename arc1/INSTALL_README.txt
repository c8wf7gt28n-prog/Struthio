ARC-1 WORKBENCH - INSTALLING ON WINDOWS 11

1. Right-click the ZIP and choose "Extract All...".
2. In the extracted folder, double-click INSTALL_ARC1.cmd.
3. Answer the few questions (Enter accepts the suggested answer).

The installer:
  - finds Python 3.11 or newer, or offers to install Python 3.12 for you (winget);
  - copies Workbench to %LOCALAPPDATA%\Programs\ARC-1 Workbench (no admin rights);
  - installs Qt (PySide6) into a private Python environment, so nothing else on
    your PC is affected;
  - checks for a C compiler and offers to install LLVM (clang), which Build and
    Run need (Windows asks for permission for this one step);
  - creates Start menu and (optionally) desktop shortcuts with the ARC-1 icon,
    and an entry in Settings > Apps > Installed apps for uninstalling;
  - runs the SDK's own system check and offers to start Workbench.

Upgrading: run the new version's INSTALL_ARC1.cmd. If you changed or added files
inside the installed Workbench, the old copy is first backed up to
Documents\ARC-1 Workbench backups\<date> (before upgrade to ...).

Uninstalling: Settings > Apps > Installed apps > ARC-1 Workbench > Uninstall,
or run "Uninstall ARC-1 Workbench.cmd" in the install folder. Changed files are
backed up the same way first. Your Workbench settings stay in %APPDATA%\ARC-1.

Offline install: put the PySide6-Essentials and shiboken6 wheels for your Python
in a "wheels" folder next to INSTALL_ARC1.cmd; the installer uses them instead
of downloading.

Without installing: double-click START_ARC1_QT.cmd (needs PySide6) or
START_ARC1.cmd (classic Tk window) in the extracted folder.

No ARC-1 board is needed or used. Builds, tests and the game simulator run on
this PC; nothing is flashed. This installer has not yet been run on a real
Windows 11 PC; please report anything that looks wrong.

If Windows says "Windows protected your PC": click "More info", then
"Run anyway". The installer is not signed.
Use Python from python.org or winget, not the Microsoft Store version.
Close ARC-1 Workbench before upgrading or uninstalling.
