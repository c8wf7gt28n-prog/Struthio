# Pills — two computers, one language of work

> Two independent computers. One shared language of work. Pills carry information and requests; local policy grants authority.

Ledger & Slate can run on its own machine (the **appliance**) beside your ordinary **workstation**, where your native
applications and the master copies of your projects live. The two never share a home folder, a shell, or a sync folder.
Work moves between them as **pills**.

A pill is one file (`.pill`) that describes itself: who sent it, who it is for, which task it belongs to, the exact
revision of the files it carries, what the recipient is asked to do, and what is expected back. It is signed by the
computer that made it. **It never carries authority.** The computer that receives it checks it, keeps it in quarantine,
and its own policy decides what may happen.

## The three boundaries

| Boundary | What it means |
|---|---|
| **Computer** | Each machine has its own system, storage, processes and permissions. |
| **Pill** | Information crosses only as identified, validated pills. |
| **Authority** | Receiving a pill authorizes nothing. Each machine enforces its own rules. |

**Approval to export from Ledger is not approval to overwrite on the workstation.** These are two decisions, made on
two computers.

## The cycle

1. **The workstation prepares a request.** `python3 -m pillkit.handler prepare ~/Projects/clock --to Ledger --task "Review the clock board"`
   captures the folder's ordinary files. Hidden files, links and machine folders such as `.git` are left out, and every
   file is listed with its SHA-256. The handler keeps a copy of exactly what was sent.
2. **Ledger checks the pill and accepts it.** Open the `.pill` from Files (or Tools › Pills and Paired Computers…).
   Ledger checks it in an order that trusts nothing early: size and shape, then the signature of a paired computer,
   then every member's hash, then the contract, then that it is meant for this Ledger and is not a replay. Accepting it
   makes a **working copy**, for you or assigned to Slate. Its files arrive inert, readable by you only and never
   executable, and nothing in them is run.
3. **Slate works on the copy.** He works on his assigned copy as on any working copy. The pill's original is on the
   other computer, so Ledger cannot change it: `copies.apply` refuses pill copies.
4. **Ledger packs a result pill.** In Files, right-click the working copy › Return as a pill…, and write your findings.
   The result holds the changes (create, replace, delete, each with the file's hash before and after), only the changed
   files, and the findings as a note. It is written to Files › Exports › Pills. Packing it is your approval to export,
   and only that.
5. **The workstation decides.**
   - `review result.pill` shows the findings, what happens to each file, and a text diff. It checks whether each file
     here is still exactly as it was sent.
   - `save-new result.pill ~/Projects/clock-reviewed` writes the proposal as a new folder. The original is not touched.
   - `apply result.pill` asks you to type **yes**. If any touched file has changed since it was sent, it refuses and
     nothing is applied.
   - `undo <pill id>` puts the original back.

## The pill format (`arc.pill/1`)

A ZIP file holding exactly these members:

| Member | What it is |
|---|---|
| `pill.json` | The contract (below). Unknown fields are refused, so a pill cannot smuggle in new meanings. |
| `files/<path>` | A request carries every file of the source revision. A result carries only the files it creates or replaces. |
| `notes/<name>` | Findings and evidence (`.md`, `.txt`, `.json` or `.csv`). |
| `manifest.json` | `arc.pill-members/1`: the SHA-256 and size of every other member. |
| `signature.json` | `arc.pill-signature/1`: the signer's key and an Ed25519 signature over the manifest bytes. |

The contract:

| Field | Request | Result |
|---|---|---|
| `id`, `sequence`, `created` | a fresh 32-hex id; the sender's next sequence number | same |
| `sender`, `recipient` | `{name, key}`; the key is the first 32 hex of SHA-256(public key) | same |
| `task` | `{id, title, purpose}` | the request's task |
| `source` | `{label, revision, files{path: {sha256, bytes}}}`; the revision is the hash of the file list | the request's source, unchanged |
| `requested` | some of `inspect`, `analyze`, `propose_revisions`, `test` | `[]` |
| `expected` | some of `findings`, `candidate_files`, `evidence`, `stac` | `[]` |
| `limits` | always `{changes_to_originals: false}`; any other value is refused | same |
| `in_reply_to` | `null` | the request's id |
| `result` | `null` | `{findings, changes[{op, path, before, after}], evidence[]}` |

## What a signature proves, and what it does not

A valid signature proves which paired computer made the pill and that not one byte has changed since. It does **not**
prove that the contents are harmless. A pill can still carry a compromised document, a malicious script, a dangerous
archive, or text written to manipulate Slate. So:

- **Files are source material, never instructions.** Nothing inside a pill can widen a scope or change policy. Slate can
  only propose; the Kernel enforces your scopes.
- **Reading is bounded and refuses rather than repairs:**
  - up to 256 MB per pill, 600 members, 64 MB per file and 1 MB per JSON member;
  - an expansion ratio of at most 200 (no zip bombs);
  - no folders, links, encrypted entries or unusual compression;
  - names safe on Linux, Windows and macOS: no `..`, nothing absolute or hidden, no backslashes or reserved device names,
    no two names differing only in capitals.
- **Replays are refused,** by pill id and by the sender's sequence number (each is used once). Out of order is fine.
- **Pairing is explicit.** Each side gives the other its card (name and public key). Both screens then show the same
  pairing code, and if they don't, nothing is kept. The private key never leaves its folder (`0600`), and a key readable
  by others is refused.

## Applying on the workstation: all of it, or put it back

Replacing several files cannot be made atomic with `rename()` alone, so `apply` works from a journal:

1. Every touched file must still be exactly as sent. Otherwise apply is refused and nothing changes.
2. You type yes.
3. Each replaced or removed file is kept. New contents are written beside each target and flushed, and a journal records
   every step.
4. Each file is swapped in by `rename`, and the journal is updated after each swap. An original path is never left
   missing.
5. If the computer stops part-way, `resume` finishes from the journal. `undo` restores what was kept and removes new
   files, but only if they have not been edited since.

## Transport

The format does not depend on how a pill travels.

| Connection | Use |
|---|---|
| **USB pills** | The first proof. No network between the machines. |
| **A dedicated wired link** | Built: `pillkit.link` (below). The same pills over a mutually authenticated, encrypted channel. Never a shell, a shared folder or generic remote execution. |
| **An existing private LAN** | Possible, with more isolation work. |

A direct cable is not an air gap, and SSH would authenticate and encrypt the link but would not enforce Ledger's own
permissions. The pill rules do that.

## Decisions for the appliance (recorded, not yet built)

- **Display: a kiosk Wayland compositor (such as `cage`), not EGLFS.** Ledger uses menus, submenus, popups, docks,
  drag and drop (the trash can), and a second process with its own window (the STRUTHIO game). EGLFS restricts several
  of these. A single-app compositor still gives a full-screen appliance with nothing else installed. Qualify on the real
  hardware.
- **Parsers run confined.** The appliance keeps a fixed Debian base, so the parsers that open untrusted formats
  (spreadsheets, PDFs, pictures, DXF, archives) collect known flaws over time. They should run in a confined worker with
  no network and read-only input. Tools › This Computer shows what the machine offers (Landlock, seccomp, namespaces,
  bubblewrap).
- **Updates come as pills too.** Signed offline update pills for a narrow list of parser packages are better than never
  updating.
- **Both directions are authenticated.** Ledger accepts only paired computers; the workstation accepts results only
  for requests it sent.

## Construction order

1. ✓ Pill specification (this file, `pillkit/pill.py`).
2. ✓ Offline exchange: produce, verify and return a pill without changing either machine's originals (`tests/test_ledger_pills.py`).
3. ✓ Workstation handler: review, conflict detection, save-new, apply with a journal, resume, undo (`pillkit/handler.py`).
4. ✓ Slate workspace integration: a pill becomes a task-scoped working copy, assignable to Slate.
5. Appliance qualification. Confinement is built and verified here (below). The display backend, inference
   performance and recovery need the real machine.
6. ✓ A private wired transport carrying the same pills (`pillkit/link.py`).

## The pill link (step 6)

The workstation serves pills; the appliance only connects out, so it has no listening service.

```
workstation:  python3 -m pillkit.link serve --listen 10.77.0.1:7717 --outbox ~/pills/out --inbox ~/pills/in
Ledger:       Tools › Pills and Paired Computers… › Fetch over the link… / Send over the link…
```

- **Who may connect.** Only paired computers. Each side proves its pill identity (an Ed25519 signature over a fresh
  X25519 exchange and both greetings), so a stranger cannot connect, and neither side can be impersonated by someone
  replaying an old session.
- **Encryption.** Session keys come from HKDF-SHA256, and every frame is sealed with ChaCha20-Poly1305 under a counting
  nonce. A frame that is changed, replayed or reordered ends the session.
- **What it carries.** Exactly three requests:
  - `list`: the outbox pills that were signed by the server and are addressed to the caller;
  - `get`: one of those, by its pill id;
  - `put`: a pill for the server. It must check as a pill signed by the caller and addressed to the server, and it is
    stored under its own id, never under a name the caller chose.

  There are no paths, commands, shells or sync.
- **Where pills land.** In quarantine (Files › Received › Pills on Ledger, the inbox on the workstation), still to be
  opened, checked and accepted like any other pill.
- **Where it listens.** The service refuses to listen on every network at once unless told to (`--any`). It is meant
  for the dedicated cable's own address.

## Confinement (built)

`workbench/confine.py`, `confine.status` / `confine.run` / `confine.inspect`:

- **Mechanism.** bubblewrap when it is installed. Otherwise Landlock, which is built into Linux 5.13 and later:
  - the system is read-only, the working folder is the only writable place, and nothing else can be read;
  - TCP bind and connect are refused (ABI 4+), and signals and abstract sockets stay inside (ABI 6+);
  - there is a private network namespace where the kernel allows it;
  - `no_new_privs` is set.

  With neither mechanism, runs are refused, never run unconfined.
- **Every run** also has limits on processor seconds, memory, file size and open files, no core dumps, its own session
  (so a timeout or Stop ends the whole group), and a minimal environment. Master Stop ends it too, because it is
  Ledger's descendant.
- **Untrusted files** (for example a pill's) can be read by Ledger's own readers inside confinement: right-click a
  folder working copy › Look inside, confined…. A reader that chokes on a file reports it and is never fatal.
- **Verified here.** Each of these was refused: reading or writing outside the folder, reading another home folder,
  opening a network connection, a runaway loop (killed at its time limit) and a 6 GB allocation (refused). Tools ›
  This Computer shows the row "Confined runs · verified here".
- **Not yet:** a seccomp filter of its own, and cgroup limits (the test machine delegates no cgroup controllers).

## The workstation handler

Copy the `pillkit` folder to the workstation. It needs Python 3 and the `cryptography` package, and nothing else from
Ledger. On Debian, install it with `sudo apt install python3-cryptography`; elsewhere use `pip install cryptography`.

```
python3 -m pillkit.handler init --name "Workstation"
python3 -m pillkit.handler card > workstation-card.json     # give this to Ledger: Tools › Pills › Pair with a computer's card
python3 -m pillkit.handler pair ledger-card.json            # Ledger: Tools › Pills › Save this Ledger's card
```
