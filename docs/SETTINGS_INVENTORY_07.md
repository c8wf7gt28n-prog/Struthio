# Settings inventory 07

The one current settings inventory of Graphite 0.1 (November 6, 2026). It was first written for HATCH DESKTOP-01 and
extended in AGENT-02; Graphite 0.1 folds in the classification of every preference outside the registry (from the earlier
inventories 01 to 06, which left the tree) and brings the words to Graphite. The file keeps its name because the program
names it: `ledger_control.settings()` reports its coverage as "43 genuine settings; remaining coverage is recorded in
docs/SETTINGS_INVENTORY_07.md".

There are 43 genuine connected settings, `workbench/settings_registry.SPECS`; the live count is always `len(SPECS)`. The
settings page shows two roots, **Workspace** and **Assistant** (`settings_registry.ROOT_NAMES` over the unchanged root keys
`Ledger` and `Slate`). Since Graphite 0.1 the definitions themselves carry Graphite's words (labels, descriptions and
effects); keys, defaults, kinds, scopes, stores and root keys are unchanged, as the owner's rename asked. The release check
records every definition's digest and the settings digest in `docs/GRAPHITE_0.1_REGISTRY.json` (written by
`tools/record_registry.py`) and lists any added, removed, changed or moved definition in words.

## Complete current inventory

| Canonical key | Visible control (Settings → root → group → label) | Default | Actual scope | Backing store |
| --- | --- | --- | --- | --- |
| agent.continue_when_closed | Assistant → Assignments → Continue assignments while Graphite is closed | true | Project private (owner only) | Kernel settings: ledger.agent.continue_when_closed |
| appearance.cursive | Workspace → Appearance → Script for incidental text | true | Connected session profile | Session cursive |
| appearance.writing_marker | Workspace → Appearance → Writing marker | true | Connected session profile | Session writing_marker |
| brain.context | Assistant → Local model → Model context tokens | 2048 | Owner-controlled launch defaults in this workspace (owner only) | Kernel settings: ledger.brain.context |
| brain.memory_mb | Assistant → Local model → Model memory cap (MiB) | 0 | Owner-controlled launch defaults in this workspace (owner only) | Kernel settings: ledger.brain.memory_mb |
| brain.threads | Assistant → Local model → Model CPU threads | 4 | Owner-controlled launch defaults in this workspace (owner only) | Kernel settings: ledger.brain.threads |
| cabinet.sort | Workspace → Cabinet → Cabinet sibling order | "natural" | Workspace private | Kernel settings: ledger.cabinet.sort |
| catalog.view | Workspace → Cabinet → Existing catalogue view | "works" | Connected personal catalogue profile | Existing Concern catalogue preferences.view |
| favorites.edit | Workspace → Favorites → Revise favorites | ["undo", "redo", "find"] | Connected session profile | Session toolbar_favorites.Edit |
| favorites.file | Workspace → Favorites → Work favorites | ["open", "save", "save_all"] | Connected session profile | Session toolbar_favorites.File |
| favorites.help | Workspace → Favorites → Guide favorites | ["orange_book", "genesis", "database_rom"] | Connected session profile | Session toolbar_favorites.Help |
| favorites.options | Workspace → Favorites → Tools favorites | ["build", "run", "tests"] | Connected session profile | Session toolbar_favorites.Options |
| favorites.view | Workspace → Favorites → Arrange favorites | ["focus_layout", "split_editor", "inspector"] | Connected session profile | Session toolbar_favorites.View |
| gemini.include_file | Assistant → Providers → Include the current file with Gemini | false | Personal Gemini preferences (owner only) | Existing clip.json include_file field; credential bytes preserved |
| gemini.model | Assistant → Providers → Gemini model preference | "" | Personal Gemini preferences (owner only) | Existing clip.json model field; credential bytes preserved |
| hardware.category_views | Workspace → Hardware → Hardware category views | {} | Connected session profile | Session category_views |
| layout.navigator_width | Workspace → Layout → Left column width | 285 | Connected session profile | Session layout.navigator_width |
| layout.output_height | Workspace → Layout → Output panel height | 170 | Connected session profile | Session layout.output_height |
| layout.output_tab | Workspace → Layout → Selected output page | "Output" | Connected session profile | Session layout.output_tab |
| layout.output_visible | Workspace → Layout → Show output panel | false | Connected session profile | Session layout.output_visible |
| memory.profile.enabled | Assistant → Memory → Use personality reference | true | Owner private memory in this workspace (owner only) | Existing owner memory profile: stacy_memory/current |
| memory.soft_half_life_days | Assistant → Memory → Soft feedback half-life (days) | 90 | Owner private memory in this workspace (owner only) | Existing owner memory profile: stacy_memory/current |
| memory.weight.owner_confirmed_choice | Assistant → Memory → Confirmed choice weight | 0.5 | Owner private memory in this workspace (owner only) | Existing owner memory profile: stacy_memory/current |
| memory.weight.owner_correction | Assistant → Memory → Owner correction weight | 4.0 | Owner private memory in this workspace (owner only) | Existing owner memory profile: stacy_memory/current |
| memory.weight.owner_statement | Assistant → Memory → Owner statement weight | 2.0 | Owner private memory in this workspace (owner only) | Existing owner memory profile: stacy_memory/current |
| operations.priority | Workspace → Operations → Work CPU priority | "normal" | Project private | .ledger/master-stop/priority.json |
| operations.services_enabled | Workspace → Operations → Graphite services admission | true | Project private (owner only) | Kernel settings: ledger.operations.services_enabled |
| reading.code_family | Workspace → Appearance → Code font | "IBM Plex Mono" | Connected session profile | Session reading_profile |
| reading.code_pt | Workspace → Appearance → Code text (pt) | 14.0 | Connected session profile | Session reading_profile |
| reading.family | Workspace → Appearance → Interface font | "IBM Plex Sans" | Connected session profile | Session reading_profile |
| reading.line_height | Workspace → Appearance → Document line spacing | 1.4 | Connected session profile | Session reading_profile |
| reading.navigation_pt | Workspace → Appearance → Tree text (pt) | 15.0 | Connected session profile | Session reading_profile |
| reading.prose_family | Workspace → Appearance → Prose font | "IBM Plex Sans" | Connected session profile | Session reading_profile |
| reading.prose_pt | Workspace → Appearance → Prose text (pt) | 16.0 | Connected session profile | Session reading_profile |
| reading.reduce_motion | Workspace → Appearance → Reduce motion | false | Connected session profile | Session reading_profile |
| reading.ui_pt | Workspace → Appearance → Interface text (pt) | 14.0 | Connected session profile | Session reading_profile |
| stacy.actions | Assistant → Tools → Enable Graphite action proposals | false | Project private | Kernel settings: ledger.stacy.actions |
| stacy.enabled | Assistant → Behavior → Allow new Graphite AI activity | true | Project private (owner only) | Kernel settings: ledger.stacy.enabled |
| stacy.provider | Assistant → Providers → Graphite chat provider | "local" | Project private (owner only) | Kernel settings: ledger.stacy.provider |
| stacy.reactions | Assistant → Behavior → Graphite reactions | true | Connected session profile | Session layout.stacy_reactions |
| stacy.share_activity | Assistant → Tools → Share activity context | false | Project private | Kernel settings: ledger.stacy.share_activity |
| workspace.mode | Workspace → Workspace → Workspace arrangement | "engineering" | Connected session profile | Session view_preferences |
| workspace.startup | Workspace → Workspace → Startup | "last" | Connected session profile | Session view_preferences |

## The two newest settings

**appearance.writing_marker** (DESKTOP-01; Workspace → Appearance → Writing marker; Off / On). It is the reversible,
quiet-motion-aware form of the owner's decorative X that the Interface Companion asked to keep (specification VS03). The value is a boolean, default true. The consumer is the window's one marker controller (`workbench/writing_marker.py`): while an opted-in yellow writing passage has keyboard focus, a small graphite X (1.25 × the passage font's x-height, so 12 px on 14 pt code and 10 px on 14 pt prose) is drawn in the page's own margin on the caret's line and blinks with a 2 s period, half the caret's rate. The passages that opt in are the cabinet's title line and writing passage, the memory direction correction (the same cabinet writing), the New Idea sheet (Home and the Jot it down dialog), the Settings string value and the return thread; the source editor is refused, and no search or console field carries it. The X is painted from the page's own paint event, so the passage, its document, undo, selection, caret and click areas are untouched and the accessible tree gains no object. `reading.reduce_motion` wins over this setting: the X stands still and no timer runs. Application is immediate: a Set, Undo or Default from Slate, the CLI or the Settings page reaches the controller on the next desktop tick through `sync_profile`. Readback is a controller receipt (`requested` the saved choice, `effective` what focused passages show, `motion` blinking / static / off, `passages` the number opted in): `APPLIED` when the saved choice is what the desktop shows (a static X under Reduce motion is applied, not pending), `PENDING_DESKTOP` otherwise, `NO_LIVE_DESKTOP_READBACK` without a connected desktop. New keys use single-key Set/Default/Undo; the existing batch schema remains exactly 17 keys. A profile without the field, or with a foreign value, reads as the default and is never rewritten by reading. The `Session.load` loader for the field belongs to WI-1 (workbench/session.py); until it is present a saved false is on disk but a fresh Session reads the default, which `test_paper.py` reports as skipped rather than passed.

**agent.continue_when_closed** (AGENT-02; Assistant → Assignments → Continue assignments while Graphite is closed; Off / On).
The value is a boolean, default true, project private, owner only, single-key Set (the public batch enum stays 17 keys). Two consumers read the same Kernel settings row: the desktop's close (with the Graphite service, internally the Ledger service, live and the value on, a running assignment is released to the service instead of paused) and the service's 5 s tick (`agent_loop.pump` steps released assignments only while the value is on, and rechecks it before every step). A stored value that is not a boolean reads as off. See docs/CONTINUE_01.md and decision D29.

## Classification and remaining audit

The per-category audit enumerated every persisted preference and state outside the registry: the connected Session
profile, the Kernel `settings` table, project-private files under `.ledger/`, personal profile files and environment-driven
options. `QSettings` is not used anywhere.

| Existing field or control | Classification and treatment |
| --- | --- |
| Session `writing_marker` (new in DESKTOP-01) | Genuine boolean presentation preference, adapted as `appearance.writing_marker` (above). It is the reversible, quiet-motion-aware form of the owner's decorative X; it never changes editing behaviour, so it is public presentation state in `ledger.context` and a cloud proposal may Set it like favorites. |
| Hardware category_views: Auto view, Details, Thumbnails | Adapted in INTEGRATION-01 as `hardware.category_views`; the editor now sizes its frame to its rows up to a cap that scales with the interface size, runs its Tab order pane by pane into Apply, and names each combo for assistive technology (DESKTOP-01, V-08 / ACC-06 / ACC-07 / ACC-10). |
| Orange Book `auto_refresh` (`.ledger/orange_book_enabled.json`, checkbox "Automatic updates", default from `docs/orange_book/bindings.json`, env override `ARC_LEDGER_DISABLE_BOOK_WATCHER`) | Genuine boolean preference, previously absent from this table. Retained in its original control (Orange Book panel checkbox); not adapted in INTEGRATION-01, reason: project-private boolean with an env override and a watcher consumer; candidate for a later slice. |
| Window geometry, dock state and engineering split state | Saved workspace arrangement, retained by the original restore paths. No scalar setting invented. |
| last_surface, selected_nav and current record | Runtime workspace/navigation state, retained without changing record identity. |
| Per-view tree expansion, selected tree node, scrolling, settings/cabinet navigation and Library section folds | Navigation state; preserve existing projection and persistence behavior. |
| clip_position and clip_collapsed | Workspace arrangement state of the live companion overlay (`ClipAssistant.retired` is False; the overlay is shown in workspaces and hidden at Home, and these fields are read and written by its own drag and collapse controls). An earlier inventory called them retired compatibility fields; that wording was wrong. No scalar setting is advertised; the original controls stay. |
| library_open, type_target, console.mode, console.history, pill_link (Session) | Written on every save but never restored before INTEGRATION-01 (dead persistence). INTEGRATION-01 adds bounded loaders in `Session.load`: `library_open` (≤ 50 section → bool), `type_target` (one of slate, stac, kernel, find, shell), `console.mode` (one of the five console pages), `console.history` (≤ 50 typed lines per page on load and on save; the live console still keeps 200 in memory), `pill_link` (host:port or [ipv6]:port). Navigation state and a deployment input; none is a registry value. |
| Journal `ledger.change.*`, receipts `ledger.settings_runtime.*`, desktop intents `ledger.ui.*`, `ledger.session_path`, desktop catalog/context, work gate, service cycle, brain selection/worker/handover, model registrations, dialogues, `remote_enabled`, `deployment.profile` | Journal, observations, stateful actions, working records, binding and deployment inputs with their existing routes. `history()` now tolerates journal rows of retired keys (`orphaned`, never undone); receipts of desktops whose lease is gone are pruned on the next publish; a corrupt `operations.priority` file or a tampered Kernel-table value is one `STORE_UNAVAILABLE` row (`repairable`: Default replaces it) instead of a failed `ledger.settings` read. |
| Model identity, registration, load, qualification, restore and stop | Existing stateful actions. Three launch defaults remain shared settings with separate requested/running readback. |
| Memory import/archive/delete, owner correction and source review | Existing owner-scoped actions; five existing memory preferences remain shared and private. |
| Credentials, environment/deployment inputs (`ARC1_WORKBENCH_CONFIG_HOME`, `ARC_LEDGER_*`, `GEMINI_API_KEY`, `LEDGER_PYTHON`, remote-config.json, pill link) and runtime pins | Existing controlled configuration and deployment routes; no arbitrary path/value editor. |
| Legacy Tk `workspace.json`, catalogue `expanded`, object glass history, activity, caches and locks | Compatibility data, navigation state, working records and caches; not preferences. |
| CPU/RAM observations, jobs, queues, records and qualification results | Observed runtime state and working records, not preferences. |

Source sharing, rights, model qualification and engineering acceptance retain their original boundaries. The five shared
memory preferences and three local-model defaults keep their privacy checks (owner only). Forty-three connected settings
describes this audited registry; it does not close every settings, menu, launcher or owner-host review item. Evidence:
`tests_integrated/test_settings_registry.py`, `test_settings_advanced.py`, `test_hardware_settings.py`, `test_paper.py`, the
settings section of the release check, and `tools/check_hardware_settings_ui.py` and `tools/check_paper_ui.py`. How each
slice of settings came to be is in docs/HATCH_SETTINGS_01.md to _03.md, HATCH_MODEL_01.md, HATCH_PRESENTATION_01.md and
HATCH_INTEGRATION_01.md.
