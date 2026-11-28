# Graphite 1.1.1: the system door

*28 November 2026, the same morning as 1.1. One addition: Kas can now change the system itself, through Debian's own
permission prompt, with you present. Install it over 1.1 the same way: `bash JOIN.sh`, then `bash install.sh` as root.
Everything in `RELEASE_NOTES_1.1.md` still holds.*

## What is new

**The system door.** Ask Kas in plain words, in her line or the bar's line, for one of fifteen fixed actions:

- **Software:** install, remove or update a package, refresh the list, and see what has updates.
- **Services:** start, stop, restart, enable or disable one.
- **The clock:** the time zone, network time on or off, or setting the time.
- **The computer's name.**
- **Accounts:** add a standard account, or set an account's full name. She never touches another person's password.

Every one follows the same steps:

1. **She shows it first.** "Install GIMP": what the system will do, what it pulls in and how large it is. Nothing has
   changed yet.
2. **Your press starts it,** "Install (the system asks)", or Not now.
3. **The system's own prompt asks for your password.** It is Debian's polkit, not Graphite. Kas never sees the
   password.
4. **She reads the result back** before she says "Done and verified". She checks that the package is installed at that
   version, the service is running, or the zone is set.
5. **Undo,** where the system allows one, asks again.

It is never her own step, never under a standing grant, and never while HALT holds. It is one action per prompt, one at
a time. It talks only to Debian's own services (PackageKit, systemd, timedated, hostnamed, accountsservice), each of
which asks polkit itself. There is no shell, no `sudo` and no root helper of Graphite's. The password prompt comes from
lxpolkit, which the Graphite session has started since 1.0.

You'll find it in her talk and NEXT STEPS, in the bar's line ("install gimp" → "Install GIMP, asks for your password"),
and on a new page, Settings ▸ This computer ▸ System changes.

Her command tool now points to it. A command needing root ("run: sudo apt install gimp") is refused, and she tells you
to say it in words so it can go through the system door.

**New packages:** `packagekit` and `accountsservice`, which the door needs. They are Recommends of graphite-session, and
the kit's repository now carries them and what they need.

## What was tested, and what was not

- **Its own tests:** 13 tests of the door, against stand-in services on a private message bus.
- **Its neighbours:** 92 tests of the door, the command tool, her voice, the line, the recipes, Kas on the bar and the
  packages pass on a copy of the merged tree.
- **The release check** passes on the exact commit the kit was cut from.

Not exercised: a real polkit prompt, real PackageKit, systemd or accountsservice. The build machine has none of them
running. So it has never installed anything for real. **Your ThinkPad is its first real test.** Try a small, harmless
package first (`install cowsay`), then remove it with Undo.

## Still not done

- A real terminal in the drop-down (vim, top, sudo prompts).
- Grounding in your manual pages, and "teach me".
- A quieter bar.

All three are designed and saved for next week.
