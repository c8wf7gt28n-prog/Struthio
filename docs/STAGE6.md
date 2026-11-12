# Stage Six: paired exchange, signed releases and deployment

Candidate 5.0.0a6 completes the six implementation stages of the approved upgrade. Physical and owner acceptance remains pending. Open **View → Exchange & deployment**. The panel has Paired exchange, Offline updates and Computer & appliance pages. Paper/graphite styling, ordinary project files, Project Desk, Changes, Continuing work and the earlier engineering routes remain.

## Begin on one computer

Extract the complete ZIP into a NEW program directory. Keep the previous program. Close Ledger and its coordinator, then make and verify a complete workspace/profile backup before the first open. Use the installed runtime interpreter, normally `.venv/bin/python`; commands below use `python3` as a placeholder for it. Model weights are optional and are not distributed.

Stage Six adds versioned exchange and release tables to the existing Kernel database, plus a versioned SQLite counter/replay database in the existing pill identity folder. Existing sent.json and every retained seen.json exclusion are imported once. Replay history is never pruned. Existing records remain readable. The changed executor binding intentionally makes an old continuing-work grant stale: inspect it and create a new reviewed order rather than expecting automatic resumption. No source file can renew a grant.

The default mode is SINGLE. No new listener, model or service is started by opening the new panel. Existing manual Brain, engineering and locally reviewed developer-candidate update routes retain their previous boundaries; they are not retroactively covered by the new protected-worker or signed publisher-release profiles. External release bundles should use the Offline updates page described below.

## Identities and TLS pairing

The signed `arc.pill/1` archive/contract format is retained. USB transfer remains available. The previous custom encrypted network protocol has been replaced by Python/OpenSSL mutual TLS 1.3, using the existing Ed25519 pill identity. Historical source is inert text in docs/history/pill_link_4_9.py.txt. There is no old-wire fallback. Both network endpoints must upgrade and explicitly pair TLS cards, even if their ordinary pill keys were paired before.

1. On each computer, choose **Show my TLS card**, then **Save my TLS card**. Share only that public JSON file. Never share the private pill identity directory.
2. Enter the other computer's card path. Compare the full 64-character certificate SHA-256 over a separate trusted channel, then enter it and choose **Pair this verified card** on each computer.
3. The TLS certificate public key must match the signed pill card. Each connection requires a paired certificate, TLS 1.3 and the expected exact peer key/certificate pin before application bytes are sent. A name or IP address is not the peer identity. Certificate validity requires a correct host clock.
4. **Revoke selected computer** removes both the pill pairing and TLS pin. New connections, transfers, acceptance and application of a previously staged returned proposal require the sender still to be paired. Existing receipts and replay exclusions are retained. Re-pairing a legacy pill-only card does not reactivate a revoked TLS pin.
5. **Rotate my certificate** retains the signing identity but generates a new one-year leaf certificate. Explicitly exchange and verify the new public TLS card on the other computer. Old pins do not silently roll over. For a compromised signing key, revoke the old identity, create a new identity in a new private state directory, and explicitly re-pair. Keep the old receipts for provenance.

The local OS/account, private state and trusted clock are part of this boundary. This is not protection against an administrator replacing files or restoring stale security history. After deliberately restoring an old backup, reconcile sequence/replay history with the other computer or rotate/re-pair identities before resuming exchange; cloning a live identity and counter into two independent active machines is not supported.

## Request, result and master authority

Choose a profiled working copy and a paired computer. Enter a title and requested result, then **Preview request files**. Inspect the exact admitted files, hashes and exclusions. Existing pill/1 cannot represent hidden names such as .editorconfig or .gitignore; these exclusions are displayed explicitly. Retain configuration through Changes' ordinary working-copy ZIP export where needed. A pill export does not silently claim to contain the whole folder.

**Export reviewed request** rechecks the selected bytes, freezes the signed request and writes `Files/Exports/Pills/ID.pill`. It also queues it for an explicitly started listener when a TLS pin exists. This opens no socket. Exporting, transmitting, accepting and executing are separate actions. Task/operation names in the contract express the request; they grant no native command, work order or network authority.

Transport saves a completed signed pill under `Files/Received/Pills` in quarantine. **Choose & inspect pill** verifies sender, recipient, signature, member hashes and contract. **Accept request as working copy** requires the exact inspected archive SHA-256, reserves the replay claim durably and creates a profiled working copy. The optional Slate checkbox delegates access to that copy; a separate reviewed Continuing work order is still needed for continuing execution. Repeating the same completed acceptance returns its original receipt instead of creating a second copy. A received copy has no local master-publication route.

Edit that copy through Changes, inspect/apply its working proposal, and use **Export signed result** with findings. The result binds the exact request, task, source revision, before hashes and candidate bytes. It does not carry an original-owner grant.

Back on the owner computer, inspect the returned pill, then **Stage returned edits for review**. A mismatched request/sender or changed working base is refused. A valid result becomes a frozen WORKING proposal, with its diffs and paired-pill provenance. Staging applies nothing. Open Changes, review the whole proposal and apply it to the working copy. To change the OS-home master, separately preview the original update and explicitly publish it. Original undo remains a separate Changes history. A transport receipt, model finding or peer signature is never approval to publish originals.

## Explicit network operation and interruption

The appliance can fetch requests from a workstation and send results back without opening an appliance listener. A workstation listener is an explicit process, independent of the appliance coordinator. Stop that process with Ctrl-C or its separately reviewed service control. New exchange client calls observe the workspace's persistent work hold and stop epoch; interrupted client transfer retains resumable bytes. No received message automatically resumes work.

To run the workstation listener, use its existing identity state folder and explicit directories. For a workspace `/home/ledger/Concern/Office`, the normal identity state is `/home/ledger/Concern/Office/.ledger/pills`. Substitute actual paths; the command below does not infer another workspace's keys:

```sh
python3 -m pillkit.tls_link --state /home/ledger/Concern/Office/.ledger/pills serve \
  --listen 192.168.1.20:7717 --any-address \
  --outgoing /home/ledger/Concern/Office/Files/Exports/Pills \
  --into /home/ledger/Concern/Office/Files/Received/Pills
```

Without `--any-address`, only loopback binding is allowed. No OS firewall, router or public exposure is configured. The listener accepts only actively paired TLS identities. It can serve approved exports and receive signed pills for its own identity; receipt remains quarantine only. Opening a listener means allowing the paired computer to write retained incoming data, so keep its storage capacity under observation and remove/archive old receipts deliberately.

CLI `card`, `pair CARD --fingerprint HASH`, `rotate-certificate`, `revoke PEER`, `send PATH --address HOST:PORT --peer KEY`, and `fetch --address HOST:PORT --peer KEY --into DIRECTORY` are available under the same `--state DIRECTORY` prefix. The old `pillkit.link` Python send/fetch/serve entry points now require TLS pairing. Its old custom-wire CLI is intentionally not preserved; use `python3 -m pillkit.tls_link --help`.

Transfers bind peer, pill ID, full SHA-256, declared size and acknowledged offset. One-MiB chunks are fsynced before acknowledgment; interrupted tails beyond the last committed offset are resent. Retries must use the same identity, exact bytes and quarantine directory. Server/keyring restart is supported. A completed archive is admitted only after full digest and signed sender/recipient checks. Messages are limited to 256 MiB, with archive expansion and member limits; these are per-message limits, not a total retained-storage quota. Changed/missing retained files cause an explicit refusal for inspection rather than silently resetting history. A process interruption during final publication is reconciled from verified bytes. Physical power-loss behavior has not been qualified.

## Signed offline update profile

The new release path verifies a deliberately restricted TUF 1 metadata profile: Ed25519/SHA-256, root/timestamp/snapshot/targets roles, consistent snapshot names, threshold root signatures, sequential old-and-new-signed root rotation, expiry, and durable version/hash high-water marks. No delegations, mirrors, automatic online fetch or publisher trust is bundled. This is a limited implementation, not a full TUF client conformance or independent security-audit claim. The security design reference is [TUF specification 1.0.36](https://theupdateframework.github.io/specification/v1.0.36/); the transport uses the installed [Python ssl/OpenSSL interface](https://docs.python.org/3.12/library/ssl.html).

The delivered ZIP is a complete runtime candidate, not a production-publisher-signed update bundle. A real publisher identity, independent root fingerprint distribution, separated root custody, release review and a security review remain operational acceptance work. No placeholder publisher private key is shipped.

The Offline updates page requires the owner to check/confirm the real current UTC on this boot, renewed within 24 hours. A reboot, stale clock confirmation, backwards clock or expired metadata is refused. Offline operation never disables expiration. Offline freshness is only as sound as that checked clock; an offline computer cannot discover a withheld newer release merely from a still-valid older bundle.

Bootstrap a publisher root by file plus independently verified full SHA-256. Its self-threshold must verify. Thereafter root replacement requires a sequential dual-threshold-signed chain. Validated roots and role high-water marks are persisted even if later files are missing or corrupt. A previous metadata version, equal version with different bytes or a release counter at/below the installed counter is refused. Root rotation does not reset version history. Restoring an old backup can restore old high-water marks; this is not hardware-backed anti-rollback.

A release bundle's target is the complete manifested runtime ZIP. Hashes, sizes, product/version, Python range, kernel compatibility, safe member names/types, duplicates, expansion and every inner manifest member are checked as data. No downloaded script or test is executed by preview/install/recovery. A trusted signature authenticates a publisher's bytes; it does not establish software quality. This shared-runtime profile refuses a change to the current requirements pins: a dependency migration needs separate runtime installation and qualification.

After **Verify & preview update**, inspect the verified publisher/version/compatibility. Choose a new or owned release store outside both the program and Office. **Prepare closed-Ledger install command** supplies the exact preview ID/digest, workspace and profile. Close Ledger and stop its coordinator before running it. The command's form is:

```sh
python3 -m workbench.host_cli --root /home/ledger/Concern/Office stop
python3 -m workbench.release_cli --root /home/ledger/Concern/Office \
  --profile /home/ledger/.config/arc1-workbench install PREVIEW_ID \
  --digest PREVIEW_DIGEST --directory /home/ledger/Ledger-releases
```

Use the actual profile shown by your setup, not the example blindly. CLI-created previews should use `workbench.engineering_cli --identity desktop-owner --operator` to match the default local installation identity, or supply the same explicit `release_cli --identity`.

Installation creates and verifies a complete workspace/profile backup, stages the new program beside the old, journals PREPARED and PUBLISHED, and atomically changes the owned relative `current` pointer. `open-current.sh` uses the existing runtime interpreter and retained profile. The old program and data snapshot remain. No process, service or migration starts automatically. If you enabled a systemd user coordinator unit, review/regenerate its program path for the selected release before enabling or starting it again; installation does not rewrite that unit. Clients refuse a live coordinator whose edition digest differs. Open the new program deliberately only after reviewing the receipt. Stop updating if it needs a new runtime rather than reusing the old environment.

If interrupted, inspect `releases.status` and run `workbench.release_cli --root OFFICE --profile PROFILE recover JOURNAL_ID --action FINISH` after closing Ledger. Recovery checks the frozen signed target and retained program before activation. `--action REVERT_POINTER` can return to a known previous program pointer without lowering security high-water marks. It does **not** restore data. Before running an incompatible older program, restore the verified pre-update backup into NEW workspace/profile destinations. External masters and external model weights are outside that snapshot. True power-loss durability and release-store permission review remain real-host acceptance.

## Publisher tooling

Run publisher utilities in a private offline authoring environment. A local trial can create its own root; that does not make it the production publisher. Keep private keys outside all program/workspace/release ZIP inputs:

```sh
python3 -m workbench.release_publisher init /private/publisher-keys
python3 -m workbench.release_publisher build --keys /private/publisher-keys \
  --program Ledger_Slate_5_Stage6.zip --counter 1 --out ledger-release-1.zip
python3 -m workbench.release_publisher rotate-root /private/publisher-keys
```

The initializer creates a 2-of-3 root and one key for each online metadata role; all private keys are together for local setup. Separate custodians and signing procedures are a production responsibility. Build counters must strictly increase and remain monotonic across root rotation. Root rotation produces sequential public metadata signed by old and new thresholds. Public metadata and the exact program target are bundled; private keys are not. Timestamp expires after 30 days, snapshot after 90, targets after 180 and generated roots after 365. Reissue fresh monotonic metadata before expiry, even for a retained target.

## Computer, appliance and phone

**Prepare launch configuration** writes reviewable files into a NEW folder. SINGLE and WORKSTATION use the ordinary Qt launcher. APPLIANCE prepares a `cage -- python -m workbench.launch` route and a systemd user coordinator unit with explicit program, workspace and profile paths. No OS account is created, no unit enabled, no login/linger policy changed and no display/network settings are altered. Activate only after reviewing paths on the actual machine. The Wayland/Cage direction is deliberate; EGLFS qualification is not claimed. Fluxbox remains the ordinary ThinkPad route. Menus, dialogs, games and native tool windows require the actual appliance display walkthrough.

**Share my work summaries with paired view phones** is an explicit opt-in for the current owner's continuing work. The phone's Progress page requires an unexpired, still-present paired `view` session, and sharing can be stopped immediately. It exposes up to 30 task IDs, titles, states, reasons, attempt counts and reserved token counts. It carries no inputs, outputs, grants, approval or execution controls. Existing phone HTTPS/pairing setup is still separate and no phone listener is started by sharing a summary. Re-pair phones after the remote-policy inventory changes.

## Checks and acceptance

```sh
python3 tools/check_release.py --self-test --runtime
python3 -m unittest discover -s tests_stage_six -v
python3 -m workbench.deployment_checks --ui
python3 -m workbench.continuing_checks --workers
```

The first command runs all earlier stage walkthroughs, two independent workspaces using actual mutual TLS on this host, explicit request acceptance/result review/master publication and undo, new-process reopen, full backup/restore, and signed-update recovery after an actual child-process exit. The update fixture is an inert miniature program and is never executed. Stage Six adds sixteen focused boundary tests; the previous fifty-three remain. `STAGE6_RESULT.json` contains measured results; earlier results remain historical receipts.

The physical acceptance sequence is: back up a real workspace; import a small Clock folder without changing its master; complete one bounded assignment; pair the actual workstation/appliance; fetch a request; interrupt/restart transfer; accept and review a result; create a deliberate conflict; revoke/re-pair; separately publish/undo an original; trial a signed release with deliberately expired/tampered metadata; recover its program and restored data; then qualify display behavior and the real protected worker/model profiles. Use the optional phone only after read-only sharing is verified. Implementation is 6/6 stages; physical/owner acceptance, production trust custody, independent security review, actual power loss, protected-worker containment and chosen-GGUF quality remain separate evidence.
