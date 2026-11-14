{
 "summary": "Neither side bundle is one of the 51 transfer ZIPs, and neither Records part has been uploaded (0 of 2 by hash at 01:57 UTC). After_Hours_07 is a fictional demo case packaged with a restorable Graphite workspace backup (schema arc.workspace-backup/1, created 2026-11-09T11:17:41Z). Its START_HERE says to open it with \"Graphite 0.2a11 or a compatible later build\"; there is no version marker in BACKUP.json or either database. The backup is fully self-consistent: all 50 inventoried files match size and sha256, all 42 listed directories exist, nothing is unlisted, and both SQLite files pass integrity_check. Still_Stacy is the patch that makes the portrait still, with two JSON receipts and two screenshots. All 24 hunks across its 6 files are present in post-image form in the merged tree, and the two blink images are absent from MANIFEST.json, so the tree really is \"0.2a13 with Still Stacy applied\". The two bundles plausibly are the \"sealed After Hours checkpoint\" and the \"Still Stacy patch and its receipts\" that Records carries, but that cannot be proven without Records. Together they are only 65 files and about 2.1 MB against Records' 233 files and 18.5 MB, so at least 168 files and about 16.4 MB (the \"design documents\" and other evidence) are still not on hand. No file list for Records exists in anything uploaded, and no script in the tree assembles it. Neither bundle holds real personal data; everything is labelled fictional and the only paths are the packaging sandbox's. Separately, the uploads folder now holds all 9 App parts with matching hashes (02, 03 and 04 arrived at 01:39\u201301:50 UTC), so the supplied context that these are missing is out of date. Nothing from the untrusted trees was executed; my scripts and per-file hash lists for a later Records comparison are in /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/sidebundles/.",
 "findings": [
  {
   "title": "Records is still entirely missing, and only its envelope is known",
   "claim": "Neither Graphite_Records_part_01.zip nor part_02.zip is among the uploads. The metadata gives sizes and hashes only, with no file list: 2 parts, a source archive of 18,473,946 bytes, 234 entries (233 record files plus MANIFEST.json), and no split files. No script in the restored tree assembles a Records set.",
   "evidence": "Graphite_Transfer/Records/SHA256SUMS: part_01 673bc8e2..., part_02 88d99ece.... Records/RELEASE_PARTS.json: checkpoint 'Graphite project records', source_archive_bytes 18473946, source_archive_sha256 9b19a666..., payload_manifest_sha256 18e10883..., payload_entries 234, parts 14926094 + 3547874 bytes, file_chunks {}. Verification/SUMMARY.json 'records': 'Restored all 233 record files'. sha256 of every upload ZIP compared with the four SHA256SUMS files at 01:57 UTC: App 9/9, Records 0/2, System 0/21, Wheels 0/18. restored/tools/package_release_parts.py:72-77 is the generic splitter that writes this JSON; restored/tools/package_graphite.py builds only the App archive.",
   "importance": "critical",
   "confidence": "verified"
  },
  {
   "title": "The two bundles can account for only a small part of Records",
   "claim": "Even if both bundles are inside Records in full, they are 65 files and 2,089,918 compressed bytes. Records is 233 files and 18,473,946 bytes, so at least 168 files and about 16.4 MB of Records is material the user does not have through these bundles. Records cannot contain a complete earlier App release, since the App archive alone is 129.9 MB.",
   "evidence": "Upload sizes: Graphite_After_Hours_07.zip 1,104,399 bytes with 59 files; Graphite_0.2a13_Still_Stacy_2.zip 985,519 bytes with 6 files. Records/RELEASE_PARTS.json source_archive_bytes 18473946; App/RELEASE_PARTS.json source_archive_bytes 129921765. Transfer START_HERE.md:8 says Records carries 'the sealed After Hours checkpoint, the original Still Stacy patch and its receipts, and the design documents'; line 55 says 'The Records set carries the development evidence in separate folders' and that earlier complete release archives are in a separate November 9 project backup.",
   "importance": "high",
   "confidence": "verified"
  },
  {
   "title": "Whether the bundles are the Records items is plausible but unproven",
   "claim": "The Still Stacy bundle matches the description 'original Still Stacy patch and its receipts' closely (one patch, two receipt JSONs). After_Hours_07 is a hash-inventoried backup that fits 'sealed After Hours checkpoint', but the word 'sealed' appears nowhere in the bundle and 'After Hours' is also the name of release 0.2a12, so that identification is weaker.",
   "evidence": "Still_Stacy/ contains Still_Stacy.patch, Release_Check.json, Qt_and_Regression_Checks.json; its START_HERE.md:27 says 'The included receipt records the exact tests'. restored/workbench/version.py:15 '0.2a12: After Hours first-boot candidate'. grep for 'sealed' across both bundles and the transfer folder hits only Graphite_Transfer/START_HERE.md:8.",
   "importance": "high",
   "confidence": "likely"
  },
  {
   "title": "Records can be byte-compared with the bundles when it arrives",
   "claim": "Once restored, Records' MANIFEST.json (which must hash to 18e10883...) will list a sha256 per file, so each of the 65 bundle files can be matched by hash. I saved the per-file hash lists for that comparison.",
   "evidence": "Graphite_Transfer/INSTALL_LS.py:173-179 checks MANIFEST.json against payload_manifest_sha256 and then verifies every file in its 'files' dict. Hash lists: /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/sidebundles/bundle_hashes_after_hours_07.txt and /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/tools/sidebundles/bundle_hashes_still_stacy.txt. Key fingerprints: Still_Stacy.patch 33cdd958dd6b..., BACKUP.json 703a56fc0c07..., Source_Volume.zip 10f763f42bef....",
   "importance": "medium",
   "confidence": "verified"
  },
  {
   "title": "After_Hours_07 is a fictional demo case with a restorable workspace backup",
   "claim": "The bundle holds three fictional source PDFs, three Markdown readouts, a reference export (Source_Volume.zip) and Graphite_Backup/, a workspace-plus-profile backup of the finished case. It is not the user's own workspace.",
   "evidence": "After_Hours_07/START_HERE.md:5 'The bench readings, current Rev B, and archived Rev A are all fictional'; line 37 describes Source_Volume.zip as 'a verified reference export' and Graphite_Backup as the editable restore. BACKUP.json: schema 'arc.workspace-backup/1', created '2026-11-09T11:17:41.828005+00:00', models_included false, scope 'Workspace and selected profile; external originals and external model files are excluded.' PDF Info fields: Author 'Struthio Workshop | fictional fixture', Subject 'Synthetic Graphite workshop exercise', Creator 'anonymous'.",
   "importance": "high",
   "confidence": "verified"
  },
  {
   "title": "After_Hours_07 backup is fully self-consistent",
   "claim": "All 50 files in BACKUP.json match on size and sha256, all 42 listed directories exist, and no file is present but unlisted. The source PDFs, the stored objects, and the export ZIP all agree with each other and with the job results recorded in the workspace.",
   "evidence": "My script verify_backup.py: files listed 50, ok 50, mismatch 0, absent 0, 1,968,316 bytes; present-but-unlisted 0; dirs listed 42, absent 0, unlisted 0; the 3 quarantine objects are named by their own sha256. Sources/*.pdf hashes (2c60377d..., 6b8cf598..., 0c5baae6...) equal the quarantine objects and the Source_Volume.zip members. Source_Volume.zip sha256 10f763f4... (215,439 bytes) equals the 'sha256' in build/references/runs/1ae5eefc.../result.json (EXPORTED) and bb71d70a.../result.json (VERIFIED). The zip's inner MANIFEST.json matches all 7 other members. The three .md files equal the three 'document' rows in desk_records by title and text. One skipped path is declared: .ledger/service ('transient worker or coordinator state').",
   "importance": "high",
   "confidence": "verified"
  },
  {
   "title": "The two SQLite databases hold only the scripted demo run",
   "claim": "Both databases pass integrity_check and contain about 22 seconds of activity on 2026-11-09, all by one generic owner label. profile/concern/catalog.sqlite3 is a small navigation catalog; workspace/.ledger/engineering.sqlite3 is the workspace store with one investigation.",
   "evidence": "catalog.sqlite3: 135,168 bytes, user_version 1, 18 tables; objects 13 (10 built-in plus working copies '07 Bench readings', '07 Limits Rev A ARCHIVED', '07 Limits Rev B CURRENT'), office_documents 3, events 4, relations 15; times 11:17:19Z to 11:17:36Z. engineering.sqlite3: 1,159,168 bytes, user_version 0, 103 tables, most empty; activity_journal 181, audit 60 (actor 'desktop-owner', all OK), ledger_trail 44, jobs 9 all Completed (3 intake.scan, 3 references.page, references.index, .export, .verify), evidence 9, desk_records 3, intake_items 3 ACCEPTED, ref_pdf_annotations 1; inv_investigations 1 ('After Hours 07', state WAITING) with 4 FINDING claims, 1 QUESTION and 1 PASSED check; seven *_migrations tables at version 1; times 11:17:19Z to 11:17:41Z.",
   "importance": "medium",
   "confidence": "verified"
  },
  {
   "title": "Which build made After_Hours_07: stated as 0.2a11-compatible, with no marker in the data",
   "claim": "The only version statement in the bundle is the START_HERE line naming 0.2a11 or later. BACKUP.json and both databases carry no app version. The recorded interpreter path points to a build tree named after the 'volley' release, which the lineage ties to 0.2a11.",
   "evidence": "After_Hours_07/START_HERE.md:9 'Open it with Graphite 0.2a11 or a compatible later build'. A byte scan of all 59 files plus the inner zip finds exactly one 0.2-style version string, in that line. evidence rows in engineering.sqlite3 record argv starting '/workspace/scratch/<id>/graphite_volley2/final_release/clean-app/.venv/bin/python -m workbench.intake_service', platform 'linux', python 3.13.5, physical_hardware False. restored/workbench/version.py:16 '0.2a11: four-volley ThinkPad release'. Zip member times: After Hours 2026-11-09 04:14-04:17, Still Stacy 2026-11-09 09:03, transfer set 2026-11-10 16:14-16:21 (archive-local time).",
   "importance": "medium",
   "confidence": "likely"
  },
  {
   "title": "The 0.2a13 source on hand can read this backup format",
   "claim": "By static reading, the 0.2a13 tree writes BACKUP.json with exactly the keys and scope string found in the bundle, defines the CLI commands the bundle's instructions use, and has a CREATE TABLE for every table in both databases. The instructions assume a different install folder than the transfer set creates.",
   "evidence": "restored/workbench/workspace_backup.py:190-192 writes schema, created, models_included, files, directories, skipped, scope with the identical scope sentence. restored/workbench/baseline.py:99-103 defines 'open --root --profile', 'backup verify <backup>' and 'backup restore <backup> --to --profile'. My schema_cmp.py: 12 of 12 and 92 of 92 non-FTS tables are found in source CREATE statements. After_Hours_07/START_HERE.md:12 uses \"$HOME/Applications/Graphite\" while Graphite_Transfer/START_HERE.md:46 installs to \"$HOME/Applications/Graphite-0.2a13\" (line 19 of the bundle says to set graphite_app if it differs). workspace_backup.py:142-145 makes verify fail if any listed directory is missing, so the empty folders in the zip must be kept.",
   "importance": "medium",
   "confidence": "verified"
  },
  {
   "title": "No sign that '07' is one of a series",
   "claim": "No After Hours 01 to 06, or any other number, is referenced in the restored tree, RECORD_OF_DIRECTIONS.md, the transfer folder or either bundle. '07' also appears as a fixed decorative label in the screensaver, so it may be a motif and not a sequence number.",
   "evidence": "grep for 'After Hours' variants: in restored/ only workbench/version.py:15, workbench/idle_display_art.py:100 ('STRUTHIO WORKSHOP  /  AFTER HOURS') and a lower-case phrase in docs/BOSS_VISUAL_PASS_01_REVISION.md:3; zero hits in RECORD_OF_DIRECTIONS.md. The only numbered forms anywhere are 'After Hours 07' and 'After_Hours_07', all inside the bundle. restored/workbench/idle_display_art.py:104 'FIELD DISPLAY 07' and :214 'PLATE 07 / AFTER MIDNIGHT'.",
   "importance": "medium",
   "confidence": "likely"
  },
  {
   "title": "Still Stacy patch touches six files",
   "claim": "The patch modifies docs/THINKPAD_FIRST_INSTALL.md, workbench/boss_qt.py, workbench/idle_display_art.py, workbench/idle_display_qt.py, workbench/reading_preferences.py and workbench/session.py. It has 24 hunks, adding 46 lines and removing 165. It contains no binary changes, so it does not itself delete the blink images.",
   "evidence": "Still_Stacy/Still_Stacy.patch (412 lines, sha256 33cdd958...): file headers at lines 1, 12, 308, 361, 392, 403; hunk counts 1, 13, 5, 3, 1, 1 from my patch_check.py.",
   "importance": "medium",
   "confidence": "verified"
  },
  {
   "title": "The merged tree is the patch's post-image",
   "claim": "For all 24 hunks the post-image (context plus added lines) sits at the exact line numbers the patch states in the restored file, and the pre-image is absent. The six files' hashes equal their MANIFEST.json entries, and no identifier removed by the patch survives anywhere in the tree.",
   "evidence": "patch_check.py against /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/restored: 'TOTAL files=6 hunks=24 hunks fully consistent with post-image=24', added-missing=0 for every hunk; same result against restored2. The few removed lines that still occur are generic ('return', 'else:', '@lru_cache(maxsize=4)'). Example manifest match: workbench/boss_qt.py 12,628 bytes sha256 df5bd9fe.... Grep of restored/ for animate_portrait, sync_portrait_motion, midnight_frames, workshop_frames, _PortraitPanel, BLINK_PLATE, MIDNIGHT_BLINK, 'Animate portrait': no matches.",
   "importance": "high",
   "confidence": "verified"
  },
  {
   "title": "The two removed blink images, named",
   "claim": "The two unused blink images are branding/boss/plates/Workshop blink.webp and branding/boss/plates/Stacy after midnight blink.webp. Both are absent from MANIFEST.json and from every upload. The file-count difference between the bundle's receipt and the transfer's check is exactly these two.",
   "evidence": "Still_Stacy.patch line 29 \"-BLINK_PLATE = 'Workshop blink.webp'\" and line 33 \"-MIDNIGHT_BLINK = 'Stacy after midnight blink.webp'\", loaded via folder / 'plates' with folder = branding/boss (patch lines 48, 70, 109). restored/MANIFEST.json: 1191 files, 0 names containing 'blink', exactly 8 entries under branding/boss/plates/. No '*blink*' file in x/, restored/, restored2/ or /home/user/Struthio, and no such member in any upload ZIP. Still_Stacy/Release_Check.json 'files': 1193 versus Graphite_Transfer/Verification/restored-app-checks.json 'files': 1191; diff shows those two lines as the only differences. SUMMARY.json cleanup: 'Removed two unused blink images'.",
   "importance": "medium",
   "confidence": "verified"
  },
  {
   "title": "What the receipts say failed",
   "claim": "The same nine assertions failed before and after the patch: three GrainTests and three PaneWidthTests in test_desk, two MarkAndTileTests and one RenameGuardTests in test_graphite. The unpatched build also had one error, in TodayWorkspaceWordsTests, which went away. The receipt covers only 3 of 52 test modules.",
   "evidence": "Still_Stacy/Qt_and_Regression_Checks.json integrated_tests: command runs tests_integrated.test_desk, test_presentation_settings, test_graphite; baseline 'Ran 75 tests ... FAILED (failures=9, errors=1)'; patched 'FAILED (failures=9)' with the same nine names (test_the_band_colours_are_the_palettes, test_the_grain_is_deterministic_quiet_and_centred_on_the_band_tone, test_the_lettering_reads_on_the_band, test_the_default_follows_the_interface_size_under_the_ceiling, test_the_owners_width_is_one_width_for_both, test_the_workspace_keeps_the_floor_the_old_rules_protected, test_palette_is_graphite_paper_eraser_and_pencil_only, test_the_band_places_the_cat_by_its_pale_coat, test_public_name_and_internal_identities). All ten named tests exist in restored/tests_integrated. Static count by ast: 28 + 16 + 31 = 75 test methods in those three modules, 767 across all 52 test_*.py files.",
   "importance": "medium",
   "confidence": "verified"
  },
  {
   "title": "One of the nine failures is a stale version assertion visible in the source",
   "claim": "test_public_name_and_internal_identities expects the version short name to be '0.1', while the tree states '0.2a13', so that test must fail on this release regardless of the patch.",
   "evidence": "restored/tests_integrated/test_graphite.py:329 asserts (version.NAME, version.SHORT, version.title()) == ('Graphite','0.1','Graphite 0.1'); restored/workbench/version.py:13 SHORT = '0.2a13'.",
   "importance": "low",
   "confidence": "verified"
  },
  {
   "title": "The receipt's release check passed and matches the tree's artwork",
   "claim": "Release_Check.json reports state PASSED for 0.2a13 and is identical to the transfer's own restored-app check apart from the file count. The artwork hashes and plate names in the Qt receipt match MANIFEST.json.",
   "evidence": "Still_Stacy/Release_Check.json 'state': 'PASSED', 'failed_sections': []; diff against Verification/restored-app-checks.json differs only at lines 18 and 61 (1193 vs 1191). Qt_and_Regression_Checks.json artwork sha256 8ae73e1d... and 09f68c1a... equal MANIFEST entries for branding/boss/plates/Stacy after midnight.webp and Workshop after midnight.webp; its 8 art_plates equal the 8 plate files in MANIFEST; worksheet original_sha256 ad68d927... is examples/thinkpad_first_run/Workshop_stock.ods. Captures' recorded sha256 values equal the two PNGs in the bundle.",
   "importance": "low",
   "confidence": "verified"
  },
  {
   "title": "The patch's baseline archive is not on hand",
   "claim": "Graphite_After_Midnight_0.2a13_App.zip (sha256 7e3d188d...), the unpatched 0.2a13 archive the patch was cut against, is not among the uploads and is not part of the 51-ZIP set. The App set is the already-patched, cleaned tree with a different archive hash.",
   "evidence": "Still_Stacy/START_HERE.md:9 names the archive and hash. The name and hash occur nowhere else in x/, restored/ or out/; none of the 12 distinct upload ZIP hashes equals it. App/RELEASE_PARTS.json: checkpoint 'Graphite 0.2a13 clean with Still Stacy', source_archive_sha256 4503abf7.... Graphite_Transfer/START_HERE.md:55 says earlier complete release archives are in a 'November 9 project backup' at a chatgpt.com library link.",
   "importance": "medium",
   "confidence": "verified"
  },
  {
   "title": "No real personal data in either bundle",
   "claim": "Neither bundle contains user home paths, emails, URLs, IP addresses, tokens, keys or credential fields. What is present by category: content explicitly labelled fictional; a generic owner label; build-sandbox absolute paths; sandbox process and memory telemetry; UI layout state; and one upstream CI runner path quoted in a receipt.",
   "evidence": "My scan.py over every file (and the inner zip) with patterns for home paths, emails, URLs, IPv4, token formats, credential keywords and hostname fields. After_Hours_07: zero hits except 8 distinct paths under /workspace/scratch/<id>/graphite_spin/ and graphite_volley2/ in session.json and engineering.sqlite3. Still_Stacy: only '/home/runner' in Release_Check.json's accepted list for the pinned WASI runtime. audit.actor and all owner columns are 'desktop-owner'. PNGs have no text metadata chunks. Viewed Worksheet.png and Screensaver.png: a temp-folder sample sheet (Bracket A, Arm, Pivot ring, Shade) and a screen marked 'SIMULATION' and 'FIXTURE DATA ONLY'. session.json layout blobs decode to dock names only.",
   "importance": "medium",
   "confidence": "verified"
  },
  {
   "title": "Things the bundles and transfer notes reference that are not among the uploads",
   "claim": "Beyond Records: the unpatched baseline archive; the two blink images; an online 'November 9 project backup' said to hold earlier complete release archives; and the user's own ThinkPad workspace, profile and GGUF model weights, which the transfer notes say are backed up separately. After_Hours_07 also assumes an installed Graphite, which requires the App set to be installed first.",
   "evidence": "Still_Stacy/START_HERE.md:9 (baseline archive). Graphite_Transfer/START_HERE.md:55 (link to chatgpt.com/library, file id not reproduced here) and :57 'Your ThinkPad's personal workspace, profile, and GGUF weights have their own backup scope'. After_Hours_07/START_HERE.md:12-16 calls \"$graphite_app/LEDGER.sh\"; LEDGER.sh and START_MINIMAL_DEBIAN.sh exist in restored/. BACKUP.json models_included false and START_HERE.md:37 'with the model slot empty', so the case needs no model.",
   "importance": "medium",
   "confidence": "verified"
  },
  {
   "title": "Some design notes exist only inside the seed catalog, and the in-tree narrative stops at 0.2a6",
   "claim": "41 historical notes (40 under docs/ plus AGENTS.md, for example docs/STACY_PASS_2..12.md, docs/SLATE_PASS_13..20.md, docs/LEDGER_SLATE_CAMPAIGN.md, docs/MILESTONES.md) are not shipped as files in the App payload; their only copy is text inside project/stacy_seed/current/catalog.json. RECORD_OF_DIRECTIONS.md's current direction is the 0.2a6 visual pass and it does not mention After Hours, After Midnight or Still Stacy. Whether Records' 'design documents' are these notes or something else cannot be determined.",
   "evidence": "restored/workbench/stacy_foundation.py:183-199 CARRIED_NOTES with the comment 'Their only working copy is the text in the seed's verified catalog: they left the tree before Graphite 0.1'. My seed2.py on project/stacy_seed/current/manifest.json: 485 inputs, 444 shipped in MANIFEST with equal sha256, 41 not shipped. restored/RECORD_OF_DIRECTIONS.md:3 '## Current direction \u00b7 BOSS P10 Visual Pass 1 revision' and :9 'Graphite 0.2a6'; grep for 'After Hours', 'Still Stacy', 'After Midnight' and 'checkpoint' in that file returns nothing. catalog.json (1,878,242 bytes) is in App part 02.",
   "importance": "medium",
   "confidence": "verified"
  },
  {
   "title": "The supplied context is out of date: all nine App parts are now uploaded",
   "claim": "The uploads folder now contains App parts 02, 03 and 04, and their sha256 values match the official list, so all 9 App parts are on hand. They arrived after the context given to me was written. This is outside my assigned area but changes the answer to what is missing.",
   "evidence": "/root/.claude/uploads/62270cd8-8155-590e-b29e-91307882a142/: 3962ca81-Graphite_0.2a13_part_02.zip (modified 01:50:43 UTC) sha256 e75ff60c...; 6d646f53-Graphite_0.2a13_part_03.zip (01:39:51) 1ce6c77b...; 2d5804bd-Graphite_0.2a13_part_04.zip (01:39:51) 21c6b930.... All equal Graphite_Transfer/App/SHA256SUMS. Hash comparison at 01:57 UTC: App 9 of 9. A restored2/ tree and restored2_MISSING.txt (3 files left, all expected in part 02) also exist in the scratchpad.",
   "importance": "high",
   "confidence": "verified"
  },
  {
   "title": "Records is part of the declared project backup but not needed to install the app",
   "claim": "The download page tells the user to keep both Records parts for the project backup, but the App installer and offline media checks do not reference Records, which restores into its own separate folder.",
   "evidence": "Graphite_Transfer/DOWNLOADS.html line 15 'For the project backup, save Start Here, all 9 App parts, and both Records parts.' Graphite_Transfer/START_HERE.md:16-17 restores App to Graphite-Clean and Records to Graphite-Records. grep -c -i 'record' is 0 in App/INSTALL_GRAPHITE.sh, App/PREPARE_DEBIAN.sh, App/DEBIAN_USB.sha256 and App/OFFLINE_FILES.json.",
   "importance": "medium",
   "confidence": "verified"
  }
 ],
 "could_not_check": [
  "The contents of Records: neither part is uploaded and no file list exists in RELEASE_PARTS.json, Verification/*.json, DOWNLOADS.html or the restored tree, so the names and nature of its 233 files are unknown.",
  "Whether the 'sealed After Hours checkpoint' in Records is this After_Hours_07 bundle, and whether Records holds byte-identical copies of either bundle; this needs Records' MANIFEST.json.",
  "What the 'design documents' in Records actually are; the tree does not define that term or list them.",
  "Whether 'LEDGER.sh backup verify' and 'backup restore' actually succeed on After_Hours_07: nothing from the untrusted trees was executed. My check reproduces the same conditions verify() tests (sizes, hashes, directories, SQLite integrity) by static means only.",
  "Whether the restored case opens cleanly given that profile/session.json and a settings row still hold absolute paths from the packaging sandbox; the bundle's START_HERE claims a fresh process restored and opened it.",
  "The exact Graphite build that wrote the backup: BACKUP.json and both databases carry no app version, and the migration digests are computed at run time so they could not be matched to source without running code.",
  "Whether the patch's pre-image equals the real baseline, and the receipt's claim that a separate copy 'rebuilt the same manifest and seed bytes': the baseline archive Graphite_After_Midnight_0.2a13_App.zip is not on hand.",
  "Why eight of the nine legacy tests fail (only the version assertion is evident from source); the tests were not run, and the other 49 test modules are not covered by any receipt in the bundle.",
  "The receipt's visual claims (portrait pixel-identical after 7.1 seconds, no animation timer, screensaver behaviour): only the two static screenshots could be viewed.",
  "The online 'November 9 project backup' referenced in the transfer START_HERE.md: no network access, so its existence and contents are unverified.",
  "The 'roaming sprite standalone preview' mentioned in Still_Stacy/START_HERE.md: it is not in the bundle and I could not tie it to a specific file in the tree.",
  "The merged tree built from all nine App parts: I confirmed the three late-arriving part ZIPs by hash but did not re-derive or re-verify a complete restored tree; that belongs to the orchestrator."
 ]
}