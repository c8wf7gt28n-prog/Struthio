# Left-column logic and structure — review 01

The owner asked us to revisit the logic used to build the left column while continuing HATCH. This review is part of DISCOVERY-01. It establishes a small shared shortcut catalogue and a concrete next design step; it does not claim that the entire navigator has been unified.

## What the current code builds

| Provider | Current responsibility | Consequence for the owner |
| --- | --- | --- |
| `control_qt.add_navigation` | Adds legacy workspace/tool links beneath the Ledger area | New features can land deep inside an older tools branch |
| `shell2.build_library` | Adds Today and the ARRIVE / FILES / LIBRARY / KEEP / SLATE / PROJECTS shortcut groups | Storage locations, type filters and work views appear together |
| `ConcernController.rebuild` and `concern_catalog.tree` | Render real Concern catalogue relationships and preserve legacy workspace access | This is a different ancestry model from the shortcut groups above it |
| `shell2.fit_library` | Automatically folds groups when vertical space runs out, while respecting stored open choices | PROJECTS is early in the folding order, which can hide useful work views |
| `menus2.rebuild`, the command catalogue and route adapters | Provide commands and workspace navigation | A menu destination need not become another tree root |

The Paper CONCERN heading and the Concern catalogue root are also assembled separately. Their labels should not be treated as proof of one shared parent/child relationship. The existing refresh path reconstructs the original tree before the Concern projection; this review has not established a duplicate-growth bug.

The ambiguity is structural: a row might be a real project object, a filesystem location, a filtered collection, an operational view or a command. Those roles need to be explicit. A Library type filter is an alternate way to find an existing record, not a new owner or a second copy of that record.

## Small changes in this checkpoint

- `workbench/navigator_catalog.py` now owns the Paper shortcut sections, the legacy workspace-link inventory, presentation roles and the existing fold order.
- Paper rows receive stable shortcut IDs and role metadata. Existing Qt destination fields, captions, counts and handlers remain intact.
- Inquiries appears as a saved-work shortcut in KEEP. Algorithm & Theory Atlas and Tool Atlas stay in Tools rather than becoming new Paper tree roots.
- Concern catalogue data, its IDs, relationships and view preferences remain under the existing provider. No project, file, notebook or original source is moved.
- Settings and Trash retain their fixed footer placement. No new Hatch commands are added.

This is a foundation for reviewing placement, not a finished new information architecture. The legacy list and Paper projection remain distinct views. Inquiries and the older Investigations workspace still overlap conceptually; the next design should provide a clear shared work entry and linked views without deleting old records or hiding existing functionality.

## Recommended organizing rule

The main structural view should answer **where the work belongs**. Type filters and file locations should be identifiable alternate views. Menus and context actions should answer **what can be done**.

| Kind of thing | Recommended home or view | Rule |
| --- | --- | --- |
| Concern / project / assignment | Main work hierarchy | Parentage represents actual responsibility or membership |
| Idea / inquiry / hypothesis / finding | The relevant project or an explicit Unassigned collection | A saved record has one identity; other views link to it |
| Source document / working copy / result | References under that work, with its provenance | A project link does not move or overwrite a master file |
| Files and folders | Files view | Show actual locations and explicit copy boundaries |
| Documents / code / boards by type | Library view | These are filters over records/files, not another storage hierarchy |
| Agenda / jobs / model state / instruction matrix | Slate operational view | Process state is distinct from knowledge or project ancestry |
| Atlases, calculators and tools | Tools menu and relevant context actions | Installing a capability does not automatically add a root node |
| Settings / Trash | Fixed footer | Configuration and recovery controls remain easy to find |

I recommend a project-centered work view with an explicit current-project scope, alongside Files and Library views. Concern remains the umbrella. Unassigned work stays visible until the owner chooses a project. Existing Properties & works / Offices / Work & ideas / Archive projections can remain alternate catalogue views, with the selection and scope stated clearly.

## Next navigator implementation step

Use one typed node description for rendering and routing: stable ID, parent ID, role, canonical target, scope, provider and allowed presentation actions. Keep an alias/reference distinct from an owning parent relationship. Rendering order and indentation must not silently define ownership.

Then adapt the existing providers into that description without replacing their stores. Preserve all existing destinations and expand/selection preferences through stable IDs. Make an active project and the selected item's ancestor path resistant to automatic folding. Explain why a node appears in the current view, and keep project-scoped collections distinct from workspace-wide or Unassigned collections.

Before changing the default arrangement, produce a concrete populated tree from the actual application: one project, a second project, unassigned ideas, an inquiry with stale evidence, a working copy and a running/waiting job. Review whether each item has a clear home and whether switching views preserves its identity. Use this as the next navigator pass rather than continuing to add independent root groups.

No new mathematical or model capability should be blocked by a cosmetic tree change. The current Discovery implementation remains intact, and the next method-composition work can consume its IDs independently of how the navigator presents them.
