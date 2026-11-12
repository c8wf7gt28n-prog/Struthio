# ARC Ledger

ARC Ledger is the local workshop for ARC-1: explore the hardware, edit source, build a native host game, run the console model and read the Orange Book.

The command bar combines File, Edit, View, Tools and Help with fifteen customizable icon shortcuts. Hover or focus an icon for its name and keyboard shortcut. Search commands with Ctrl+Shift+P or find a file with Ctrl+P.

Home preserves your current work. Use the five activity tabs to move between Home, Brain Link, Source, Simulator and the Orange Book. Pin up to five workspaces. The View menu controls Focus, the editor split and the Inspector. Tools follows the active target.

The editable Orange Book chapters are in docs/orange_book/chapters.json. Its live engineering section reads the current register; it does not infer physical acceptance from a host result.

Stacy uses the same Engineering Kernel as the desktop and command line. Provider access, candidate execution and source acceptance keep their existing explicit gates. Credentials are configured locally.

For a first session, open the native C starter, create a new project, edit game.c, build and boot it. Arrow keys move, Z selects, X returns, and Enter leaves a game. A C compiler and Icarus Verilog are needed for the complete host model. These are trusted local host modules, not board executables.

See HARDWARE_STATUS.md for physical scope and DATABASE_ROM.md for reference volumes.
