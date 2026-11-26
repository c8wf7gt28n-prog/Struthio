# GRAPHITE: THE LIVING DESKTOP AND THE GHOST IN THE SHELL
### A discussion of Kasandra, intelligent computing, and the future of the personal computer

*Design vision and technical direction — November 2026*

---

## 1. The Computer Should Be the Workshop

Graphite began with a deceptively simple ambition: what if a personal computer were organized around the work its owner wanted to accomplish, rather than around the applications installed on it?

Conventional desktop environments are primarily concerned with programs, windows, directories, and processes. The user opens an application, locates a file, performs an operation, saves the result, and moves to the next application. The operating system provides the mechanisms, but the user is responsible for connecting them.

Artificial intelligence has introduced a second, equally imperfect arrangement. The user describes a problem to an assistant, receives instructions or generated material, and then carries those results back into conventional applications.

In both arrangements, the user frequently acts as the intermediary between tools.

Graphite proposes a different relationship.

**The computer is the workshop. Kasandra is the intelligence inhabiting it. The owner supplies intention, judgment, and authority.**

The workshop contains the files, applications, instruments, calculations, records, and physical resources required to accomplish work. Kasandra can examine those resources, reason about them, and operate the available machinery.

The user remains free to operate the computer manually.

Neither intelligence nor automation should be a prerequisite for ordinary computing.

The goal is not to conceal a complicated system behind a conversational interface. It is to make the system's complexity available without forcing the owner to manage every intermediate step.

A successful Graphite environment should feel like a complete personal computer and a capable working companion simultaneously.

This demands more than an attractive interface. It requires a coherent relationship between navigation, information, computation, execution, evidence, memory, and authority.

The Living Desktop addresses navigation and interaction.

The Ghost in the Shell describes Kasandra's role within that environment.

Together, they form the central design of Graphite.

## 2. Graphite Is the Desktop, Not an Application on the Desktop

Graphite is intended to replace the visible experience of conventional desktop environments such as GNOME or KDE.

It is not merely a fullscreen productivity application.

The planned foundation is Debian 13, using a minimal Linux installation and an underlying window manager. Fluxbox can remain hidden, supplying established window-management functions while Graphite supplies the complete visible desktop experience.

Graphite presents application launching, files, hardware controls, settings, project navigation, windows, notifications, and session commands.

The owner should not ordinarily need to interact with Fluxbox.

Opening Firefox, editing in LibreOffice, using Blender, connecting a USB drive, changing audio settings, or shutting down the machine should all feel like normal Graphite operations.

The existing distinction between compact application views and full native applications remains important.

Graphite can provide a simplified interface for common activities while retaining the ability to launch the complete specialist program when necessary.

This creates two complementary methods of operation.

The first is direct: the user chooses a file, opens an editor, changes something, and saves it.

The second is assisted: the user describes the intended result, and Kasandra determines which available operations can produce it.

Both methods work on the same underlying material.

Graphite must also remain useful when no language model is loaded. File handling, application launching, settings, native tools, and ordinary desktop operation cannot depend upon Kasandra's availability.

This principle gives the system its independence.

**Graphite is a complete computer environment first. Kasandra extends what that environment can accomplish.**

### The desktop as a real Linux session

A complete replacement desktop must also perform the unglamorous work that people expect from a computer. Its Apps launcher should discover installed applications; its running-window strip should identify real application windows; and its Machine and Settings trees should operate on actual system state. The owner needs access to removable storage, audio, displays, wireless connections, notifications, file associations, authentication prompts, and power management without leaving Graphite.

Keeping Fluxbox hidden is a practical architectural choice rather than a compromise in visual identity. Fluxbox can manage focus, window stacking, movement, and native dialogs while Graphite provides the visual shell. Those responsibilities should remain separate so restarting Graphite's interface need not automatically terminate external applications. The intended session should expose Lock, Suspend, Log out, Restart, Shut down, and Return to Debian as distinct actions, with a recoverable console route.

The acceptance test is ordinary use: start the machine without a model, open two unrelated native applications, exchange material between them, connect a USB drive, suspend and resume, then return to the console deliberately. Until that path is proven on the ThinkPad, a fullscreen demonstration is a milestone, not a complete desktop.

## 3. The Living Desktop: One Surface, Several Depths

The earlier interface separated Desktop, Field, and Workspace into distinct conceptual views.

Each had a reasonable purpose.

Desktop provided the general computing environment. Field displayed relationships between sources, calculations, findings, and outputs. Workspace provided an interface for reading or editing an individual item.

But requiring the user to switch between these categories introduces an artificial distinction.

Why should an individual file exist in one place for navigation, another for understanding its relationships, and a third for editing?

The Living Desktop eliminates that separation.

The middle of Graphite becomes one continuous working surface.

Selecting a file reveals that file and its relevant relationships.

Opening the file transitions into the appropriate working interface.

Closing the working interface returns to the relationship view.

The user moves deeper into the material rather than moving between unrelated operating modes.

A file can be examined, edited, compared, traced, and connected to other material without losing its identity or position in the project.

The same principle applies to folders, calculations, drawings, documents, questions, and completed outputs.

There is no need to force every object into the same visual representation. A spreadsheet should still look and behave like a spreadsheet. A drawing requires a different set of controls.

What remains consistent is the surrounding environment and its understanding of the selected object.

The Living Desktop is therefore not one giant universal application.

It is a unified way to navigate and operate the capabilities of the computer.

### A single navigation state, not three competing desktops

The center needs a clear internal vocabulary even though the owner should not have to learn it. At any moment it has a focused object, a presentation depth, a navigation history, and optionally one or more working tabs. A single click changes the focused object. A double-click asks the view resolver for a working representation. Closing the work view returns to the same focused object's board. This is a transition of state, not a launch into a different universe.

A breadcrumb near the top can show the current path and selected object's name. It should remain consistent as the owner moves by file tree, related tile, search result, or Kasandra suggestion. The center may display an empty desk, a relevance board, a reader, an editor, or a split view; these are expressions of one workspace rather than permanent top-level modes. Short, restrained transitions can preserve spatial continuity without slowing navigation.

## 4. The File Tree and the Bulletin Board

The Living Desktop has two synchronized methods of navigation.

The left column presents the conventional hierarchy: folders, projects, files, devices, and settings.

The center presents relationships.

These answer two different questions.

**The file tree answers: Where is it?**

**The bulletin board answers: What is connected to it, and why does it matter?**

When the owner selects a document in the left tree, the center displays the selected document as the focus of a relationship board.

Around that document appear other files, calculations, findings, questions, and outputs that have meaningful connections to it.

Suppose the selected item is an engineering worksheet.

Its surrounding material might include a specification that supplies electrical limits, a source PDF containing measured values, a calculation derived from those measurements, and a report that quotes the result.

The board visually describes those relationships.

If the user selects the report, the report becomes the new focus. Its sources and dependent material appear around it.

The left tree simultaneously locates and highlights the report.

Navigation also works in reverse. Selecting a different file in the tree immediately changes the central focus.

The two surfaces never maintain competing ideas of what is selected.

This synchronization should preserve expanded folders, recent locations, and navigation history. Moving between related items should not continually collapse or rearrange the left tree.

Back and Forward should allow the user to revisit the exact sequence of files examined.

The result resembles browsing a connected body of knowledge while retaining the familiarity and precision of an ordinary filesystem.

### Exact synchronization rules

The left tree and center should share a canonical object identifier, not infer their correspondence from whatever filename happens to be displayed. Two files may share a name, and a file may be renamed or moved while open. The relationship board should continue pointing to the intended object and update its visible path after the change.

When navigation originates in the tree, the center follows immediately. When it originates on the board, the tree reveals the target's parent directories and highlights that target without collapsing unrelated branches. Search results should behave the same way. In a two-pane layout, only the active pane owns the primary selection; the passive pane keeps its content and scroll position. A gentle secondary indicator can show that another open pane is displaying a different file without creating two conflicting selection highlights.

History must preserve more than a list of file names. It should remember the focused object, board zoom, relevant neighbors, active document position, and the route by which the owner arrived there. Back should restore context instead of merely reloading the previous file.

## 5. Relevance Should Determine Visual Importance

A connection alone does not establish importance.

A particular source might be connected to forty files, but only three may be important to the current assignment.

Showing all forty with equal prominence would produce a cluttered graph rather than useful information.

The Living Desktop should rank each relationship according to its relevance to the selected object and the current task.

The relevance of a connected file can depend on several independently recorded considerations.

An established dependency is stronger evidence of a relationship than a similarity between filenames. A document containing an unresolved contradiction may be especially important. A current governing specification may outrank an archived predecessor. An item explicitly prioritized by the owner should receive appropriate attention.

The current task also changes the ranking.

If the owner is investigating a power calculation, its source measurements and governing limits are likely to be important.

If the owner is preparing a historical explanation of that same project, correspondence and earlier decisions may become more relevant.

**Relevance belongs to the relationship between an object, a task, and a context. It is not a permanent intrinsic property of the file.**

The size of a bulletin-board tile should reflect that relevance.

The selected file occupies the central position. Highly relevant files receive larger tiles and clearer labels. Secondary files remain accessible but occupy less space. Weakly related material can be grouped into expandable collections.

A limited set of tile sizes would provide visual consistency without allowing the entire board to resize unpredictably.

The layout should remain reasonably stable while the owner works.

Relevance must also be distinguished from truth, confidence, and authority.

A false statement can be extremely relevant to an investigation. A contradictory source might deserve more attention than a supporting one.

Likewise, a highly reliable document may have little relevance to the current question.

Graphite should record these properties separately instead of combining them into an ambiguous score.

The owner should be able to ask why a file is being shown, inspect the relationship, pin an important item, or reduce the visual priority of an unhelpful connection.

The bulletin board is not intended to dictate the owner's attention.

It should make the available evidence easier to explore.

### Designing a relevance system that can be trusted

A relevance value should explain prominence, not masquerade as a probability of correctness. For every candidate relationship, Graphite can consider its recorded dependency, the owner's active objective, source currency, change impact, unresolved questions, explicit priority, and whether the relationship was inferred or verified. The exact weighting can remain an implementation choice, but the interface must expose understandable reasons: “supplies the selected calculation,” “quoted in the current report,” or “possible match based on terminology.”

The visual system could use four predictable levels. The focus file remains dominant. A few high-priority neighbors receive medium-large tiles with previews or meaningful metadata. Useful supporting objects receive smaller tiles. Peripheral material becomes a compact grouped count that can expand on demand. Size changes should be stable enough to preserve the user's mental map; small fluctuations in score must not cause every card to jump between positions.

A source can be relevant for uncomfortable reasons. A contradictory revision, failed test, or missing authorization may deserve more prominence than a dozen supporting documents. Relevance, confidence, and authority therefore require separate indicators. The owner can pin an object, inspect its scoring rationale, or suppress it from this board without deleting a genuine dependency. These interventions should be visible and reversible.

## 6. Relationships Must Be Explainable

There is an important difference between a recorded dependency and an inferred association.

A calculation might have an established connection to the worksheet cells from which it was computed.

A report might explicitly cite that calculation.

Those are recorded relationships.

Another document might discuss similar terminology without having an established evidentiary connection.

That is a possible relationship.

Graphite should visually distinguish them.

Solid connections can represent established dependencies or explicit references. More tentative connections can represent suggestions that require inspection.

Selecting a connection should reveal its basis.

For example, Graphite might explain that a report cites a calculation produced from particular source values, or that two documents appear related because they refer to the same component.

Kasandra can contribute to discovering associations, but an inferred relationship should not silently become a verified dependency.

This is essential if the bulletin board is to function as an instrument of understanding rather than a decorative graph.

A relationship must remain open to inspection, correction, and removal.

The owner should never have to trust a glowing line merely because the computer drew it.

### What a relationship record needs to remember

A useful connection is more than a line between two rectangles. It should identify the source and destination objects, the relationship type, the relevant revisions, and the reason for its creation. For a calculated result, the link may name an input cell or declared parameter. For a report, it may identify a quoted passage. For a suggested association, it should record that the connection is provisional and what prompted it.

Selecting a link could open a compact inspector: “Used value 300 mA from Bench Readings, revision B, to calculate settled power.” If that input changes, Graphite can mark the dependency for checking and tell the owner which later outputs are affected. If the link was only inferred from document similarity, the inspector says so plainly. This preserves a critical distinction between discovering a potentially helpful neighbor and asserting an evidentiary chain.

## 7. Opening a File Should Be a Natural Transition

The Living Desktop uses a simple interaction rule.

A single click selects an item and shows its relationships.

A double-click opens its working interface.

The central surface transitions from the bulletin board into the appropriate file view.

For a PDF, this could be a reader with page navigation, search, extraction, and provenance controls.

For a spreadsheet, it could be an editable grid with formulas, calculation controls, and a route to the full spreadsheet application.

For a drawing, the center could provide inspection, zoom, and the basic operations supported by its integration.

For a document, the center becomes a writing environment.

The underlying bulletin board does not disappear from Graphite's state.

It remains associated with the opened file.

Ordinary Save should save the current work without closing the editor.

Closing the working view should return to the board, after appropriate handling of unsaved changes.

A deliberate Save and Return action could also provide that transition.

The important requirement is continuity.

The document, board selection, position, zoom, working revision, and navigation history should remain coherent.

Opening and closing a file should never feel like abandoning one program and starting another.

It should feel like changing the depth at which the same material is being examined.

### The working view as a reversible doorway

The opened file should occupy the space needed for serious work. At that depth, related tiles recede rather than crowd the editor. A small breadcrumb or Board control provides the route back; closing the working tab restores the board's previous composition. Save only writes the current edit. Save and Return both saves and closes the working view. Closing with unsaved changes presents a clear choice instead of silently discarding them.

The same logic should apply when the target is a calculation, an image, or a question rather than a conventional file. The selected object determines which operations appear; unrelated commands stay out of the way. An Open full application action is available when the compact editor does not support a necessary feature, but the file identity and revision must remain recognizable when returning from the native program. Detecting an external save should refresh or flag the compact view, not silently display a stale copy.

## 8. Multitasking Without Reintroducing Complexity

A unified center still needs to support several simultaneous activities.

The solution should not be to recreate separate permanent modes under different names.

Instead, Graphite should maintain a work stack.

The bulletin board remains the home of the currently focused material.

Double-clicking an item opens a named working tab.

Several files may remain open simultaneously, each retaining its own selection, edit state, and position.

Returning to a previously opened tab restores that working context.

For comparison, Graphite should support an optional two-pane split.

One pane might display a source PDF while the other shows its dependent worksheet.

Another arrangement might place the relationship board beside a report being written.

Each pane can hold its own content, but only one has primary keyboard focus and selection at a time.

That active selection determines the highlighted file in the left tree and Kasandra's immediate context.

The other pane remains visible and available.

Full native applications are handled differently.

Firefox, Blender, LibreOffice, and other programs operate as ordinary windows managed by the underlying window manager.

A slim running-applications strip allows the owner to switch between them.

Graphite's internal working tabs and the system's native application windows serve related but distinct purposes.

The former organize Graphite's views of files. The latter organize complete programs.

Both should be integrated into one understandable desktop.

### Two panes, several jobs, one point of attention

Multitasking should distinguish visible working panes from background jobs. A split view is for deliberately comparing two objects, such as a specification and a worksheet, or the bulletin board and the report that depends on it. Each pane remembers its selected object, scroll position, and local undo state. Only the pane with keyboard focus drives the left-tree highlight and Kasandra's immediate interpretation of “this.” The other pane remains stable until explicitly selected.

A slender tab strip manages Graphite-owned views, while a separate, equally restrained window strip represents external applications. The same document should not be opened again as a duplicate tab unless the owner explicitly asks for another view. Dragging a file from the board into an empty half could create a split; collapsing the split should preserve both tabs. On the ThinkPad's available screen space, a default limit of two visible panes is a reasonable starting design, with additional items retained in tabs instead of becoming unreadably narrow panels.

Kasandra's long-running operations should not steal focus or rearrange windows. She can prepare work in managed contexts and offer to open a result. The computer remains the owner's workspace even while the ghost is busy elsewhere.

## 9. Kasandra Is the Ghost in the Shell

Kasandra is not simply a chatbot placed beside the work.

She is intended to be the resident intelligence capable of using the computer's available machinery to accomplish an objective.

The term *ghost in the shell* expresses the desired relationship between intelligence and the physical system.

Graphite is the shell: the computer, tools, applications, records, processes, and interfaces.

Kasandra is the intelligence that can interpret a task, examine those resources, devise a method, operate permitted tools, and assess the outcome.

The distinction is more than aesthetic.

A chatbot primarily responds with language.

An operating assistant must work with the actual state of the computer.

It must know whether a file exists, whether an operation completed, whether a calculation is current, whether an application is responding, and whether a result was saved.

It must distinguish intending to do something from having done it.

Kasandra's role is therefore organized around an ongoing cycle:

**Observe. Understand. Plan. Act. Inspect. Revise. Complete.**

A task may pass through this cycle repeatedly.

Kasandra might discover that the requested operation cannot be completed using the first method she selected. She should examine the failure, consider other available tools, and continue within her authority.

The purpose is not unrestricted autonomy.

It is competent, bounded initiative directed toward the owner's objective.

## 10. Perception Means Access to Real Computer State

For Kasandra to help reliably, she needs appropriate ways to observe Graphite and its connected applications.

A description of the screen alone is not enough.

The strongest observations come from structured interfaces.

Graphite can expose the selected file, its revision, recorded relationships, available operations, active window, and relevant machine state through defined interfaces.

Applications may expose documents, commands, accessibility information, or other integration points.

Kasandra should prefer those methods when they provide more precise information than visually interpreting a window.

Where no suitable structured method exists, more general application interaction may be necessary.

That introduces additional complexity: focus, timing, window geometry, unexpected dialogs, application errors, and ambiguous feedback.

The system must therefore distinguish observation from inference.

Reading the actual value of a spreadsheet cell is an observation.

Inferring that a visible button probably performs a particular action is a hypothesis until its behavior is established.

Kasandra should also be able to observe the results of her own operations.

A command returning successfully does not always mean the user's broader goal was achieved.

A report-generation process might complete while producing an incomplete document. A spreadsheet might save successfully but retain an outdated conclusion.

Perception must extend far enough to notice those differences.

### Observation receipts and tool awareness

An observation should include enough context to be checked later: which tool supplied it, which file or window it described, which revision was read, and whether the result was complete. An extracted number from a PDF may carry a page reference. A value read through a spreadsheet interface may carry a sheet and cell address. A screenshot-derived observation may carry an uncertainty notice when exact text or coordinates cannot be established.

Kasandra should discover capabilities through explicit interfaces whenever possible. A file reader, calculator, application bridge, and window controller can each describe supported operations and report failures in a consistent way. When she must use the visible interface, she needs confirmation that the intended window received the action. “Clicked Save” and “the expected revision exists on disk” are different observations; reliable completion requires the latter. The desktop should make it possible to inspect the evidence for the claimed result.

## 11. Reasoning Without Making Everything an LLM Problem

One of Graphite's important architectural strengths is that not every task requires a language model.

The existing mathematical and evidence-handling machinery can perform substantial work deterministically.

Arithmetic, unit checking, dependency evaluation, source revision comparison, explicit constraints, and certain forms of logical reasoning can be implemented as ordinary computation.

A language model can help interpret an unfamiliar request, identify relevant material, propose an approach, or explain an outcome.

But it should not need to invent the arithmetic.

Suppose a worksheet records a current of 300 milliamps at 12 volts.

The corresponding power is 3.6 watts.

A governing limit may be four watts.

Kasandra can use Graphite's mathematical machinery to establish the relationship and calculate the margin.

If the report still states three watts, the dependency records and source checks can identify a discrepancy.

The model may help explain the change in natural language or propose a suitable report revision.

The underlying calculation remains independently inspectable.

Graphite's mathematical direction includes exact arithmetic where applicable, dimension-aware quantities, uncertainty ranges, constraint evaluation, dependency tracing, and revision-sensitive checking.

These capabilities need not be exposed as proprietary algorithms to describe their practical value.

The central advantage is that **results can remain connected to their assumptions, inputs, methods, and revisions.**

A result is not merely a number.

It is a number with a reason for existing.

### A calculation is a claim with conditions

The mathematics subsystem should distinguish exact transformations from uncertain inputs. It can preserve units, show a derived expression, represent stated tolerances, and compare a result against a declared goal. A limit check should name the revision supplying the limit and the operating condition to which it applies. If two alternative source revisions govern different scenarios, their outcomes should remain distinct rather than being averaged into a fictitious answer.

Consider a document reporting 3.0 W while a revised current produces 3.6 W. Graphite can establish that the arithmetic changed and that the old text is inconsistent with the recorded calculation. It cannot automatically conclude that every design consideration is satisfied. Startup load, thermal limits, and measurement uncertainty might still matter. The right panel should therefore say exactly what was recalculated, what remains within a stated limit, and what still needs evidence.

This is the value of the proprietary mathematical work at the product level: not a promise of mysterious numerical superiority, but an inspectable process that can connect quantities, constraints, uncertainty, and revisions without inventing confidence.

## 12. Kasandra Must Be Able to Use the Tools She Needs

Kasandra should not be limited to a handful of predefined buttons.

The owner should be able to describe an outcome without needing to specify the application, command, or algorithm required to produce it.

For example:

“Examine this design, determine why the power budget is exceeded, correct the appropriate files, and prepare a report.”

Kasandra might need to inspect engineering documents, extract values, operate a spreadsheet, calculate power, examine a KiCad project, update a document, and preserve a record of the changes.

The requested result determines the tools.

When a reliable structured operation exists, Kasandra should use it.

When the task requires functionality available only through a full application, she should be able to use that application through an appropriate integration.

When an operation is missing, she may investigate alternatives or propose a new utility.

Creating and testing a utility should happen within a controlled environment, with suitable permission before it changes the owner's real working files or system.

This approach makes the available capability set extensible.

It also avoids turning Kasandra into a brittle collection of hard-coded workflows.

The existing DO, DOUBT, TRACE, BRIEF, and LINE operations remain useful, but they should not define the limits of Kasandra's intelligence.

They become convenient ways of directing her attention and behavior.

The owner may invoke them explicitly.

Kasandra may also determine that tracing evidence, checking assumptions, or preparing a brief is part of a larger requested assignment.

### From an objective to an operation sequence

A serious assignment benefits from a durable plan containing expected inputs, available tools, intermediate outputs, permissions, and verification conditions. Each step should have a status such as proposed, authorized, running, completed, blocked, or needs review. If Kasandra asks Python to calculate a value, the returned number belongs to that step; if she asks Writer to update a report, the saved document revision is the relevant output of another step. Neither should be called finished merely because a command was dispatched.

When an operation fails, Kasandra can inspect the failure and select an alternative that remains inside the approved scope. A new script should first be tested on a working copy or controlled environment. Sensitive changes should require an explicit new grant. The objective determines the route through tools, but tool selection is still constrained by real capabilities and authority. This is a path toward generality without pretending that every unfamiliar application is already controllable.

## 13. The Owner Retains Authority

An assistant that can operate applications must have a clear boundary between initiative and authority.

Kasandra can reason about what might help. That does not automatically give her permission to perform every conceivable action.

The system should distinguish routine permitted work from consequential changes.

Reading a project document may fall within an already established authorization.

Replacing an important file, changing system security settings, sending private information externally, or running a newly created executable may require additional approval.

These boundaries should be enforced by Graphite's operation machinery rather than relying solely on instructions given to the language model.

A proposed action and an executed action must have different statuses.

A task should also be stoppable.

The Master Kill Switch must stop Kasandra's managed activity without disabling the owner's desktop or unrelated applications.

Individual tasks need their own cancellation controls.

An interrupted task should retain enough evidence for the owner to understand what completed, what remains uncertain, and whether restarting is safe.

Undo must be similarly precise. Some file changes can be reversed through saved revisions. Other operations cannot be undone automatically.

Kasandra should represent those differences accurately.

The goal is a capable assistant whose initiative is useful because the owner can understand and control its consequences.

### Authority that survives interruptions

Permission should attach to a specific operation, target, and scope. Granting Kasandra authority to reorganize a working-copy folder does not imply permission to delete the original or publish the result to the internet. A permission may also be time-bound or limited to a particular assignment. The owner should be able to inspect pending changes in ordinary language before approval.

A task interrupted by a crash, suspend, or stop request needs a durable journal identifying which effects occurred and which were only prepared. On resume, Kasandra should inspect existing outputs before repeating any operation that could duplicate a file or change external state. Master Kill Switch stops managed agent work; it should not kill the desktop, terminate arbitrary personal applications, or conceal completed side effects. Precise controls make initiative safer because they make the limits of that initiative legible.

## 14. Kasandra's Interface Should Explain, Not Compete

The right column is Kasandra's operating area.

It should not become an endless conversation transcript.

Its primary purpose is to make her current work understandable.

At any moment, the owner should be able to determine what she is examining, what she found, what she intends to do next, and whether a decision is required.

The panel should normally present one primary suggestion.

Open questions appear beneath it, arranged by importance, with restrained indicators distinguishing urgent risks, matters requiring verification, and ordinary information.

The detailed reasoning history remains available when requested.

The old fixed command row can move into Kasandra's area because those commands concern investigation, reasoning, explanation, and action.

The center should retain the controls directly associated with the selected file: Open, Save, Compare, Search, Split, and other relevant operations.

This creates a useful division.

**The center is where the owner manipulates material. Kasandra's panel is where the intelligence interprets and works with it.**

Kasandra's portrait should support that relationship rather than dominate it.

For ordinary use, a compact recognizable portrait with subtle state changes is sufficient.

The elaborate full-body illustration and smoke effects can be reserved for more significant moments.

The desktop remains a scientific instrument, not a stage demanding constant attention.

### Six controls as an optional vocabulary

The six familiar controls can live together inside Kasandra's panel: DO, DOUBT, TRACE, BRIEF, LINE, and CHECK ALL. They are shortcuts into capabilities, not requirements for the owner to select a mode before asking a natural question. DO directs an authorized action. DOUBT investigates assumptions and conflicting evidence. TRACE follows recorded provenance. BRIEF prepares a concise, sourced account. LINE exposes the applicable precise operation or line-level context according to the existing command semantics. CHECK ALL requests the available checks and shows which actually ran.

The panel should offer one clearly justified next action, with the other controls compact and accessible. A suggested correction might read: “The power calculation now says 3.6 W; the rail summary still says 3.0 W. Review the report revision?” The owner can inspect the supporting link, approve a proposed change, or dismiss it. Successful operations update the same material visible in the center. Kasandra's panel should never become a competing copy of the file editor.

## 15. Memory Must Belong to the Project, Not Only the Model

Kasandra's continuity should not depend on a particular language model remaining loaded.

The project records must preserve files, identities, revisions, source relationships, decisions, calculations, outputs, and completed actions independently of model weights.

When a model is replaced, that project history remains.

A new model can read the relevant records and continue the work.

The model's own temporary conversational context is not a substitute for durable project memory.

Graphite should distinguish several kinds of remembered information.

A source fact is different from a calculation.

A calculation is different from a hypothesis.

A user instruction is different from an inferred preference.

An approved decision is different from a model suggestion.

Those distinctions preserve the authority and meaning of stored information.

The same principle applies to learning from corrections.

If the owner repeatedly explains how to interpret a supplier workbook, Kasandra should be able to retain the correction as an inspectable rule or mapping.

The correction can then inform future work without silently altering unrelated assumptions.

Over time, the computer becomes increasingly familiar with the owner's projects and methods.

That familiarity is valuable because it is retained in records the owner can inspect and change.

## 16. Offline Computing Is Part of the Architecture

Graphite is intended to operate as a local-first system.

The ThinkPad's Linux installation, storage, programs, and locally available models should remain useful without internet access.

The planned machine has 64 GB of system memory, a Ryzen 7 processor, integrated Radeon graphics, and a one-terabyte SSD.

Those resources provide a practical foundation for local development tools, persistent workspaces, and quantized language models.

Different models may be selected according to the assignment and available resources.

A larger mixture-of-experts model and a dense alternative are possible future configurations, not guarantees of performance or completed integration.

The system should measure actual memory usage, response speed, context limits, and desktop responsiveness before declaring a model suitable.

Kasandra should also know when the network is unavailable.

A task requiring external information must not be represented as completed if the necessary source could not be accessed.

Network access, when enabled, should be visible and governed by appropriate permissions.

Offline operation also benefits durability.

Projects should remain available on the user's own machine. The application should not require a remote account or continuous cloud connection merely to open existing work.

The important objective is independence without unnecessary isolation from useful optional services.

## 17. What Graphite 0.8.6 Already Contributes

The Living Desktop and Ghost in the Shell are a future-facing design direction, but they are not starting from an empty codebase.

The 0.8.6 source review identified several relevant foundations.

Graphite has an existing Qt interface and a dedicated Debian graphical-session path using hidden Fluxbox.

Its project machinery records revisions, identities, content relationships, and evidence.

The Field represents different kinds of working objects and their dependencies.

The mathematical system supports typed calculation and reasoning operations.

There are mechanisms for examining how changed inputs affect subsequent work.

The application also contains registered operations, bounded authority, continuing assignments, specific working procedures, and an adaptive execution mechanism.

Native application handoffs and several compact program integrations already exist.

Those mechanisms make the proposed design more plausible.

However, they do not establish that the complete Living Desktop or unrestricted application automation is already functional.

The unified navigation controller, relevance-weighted bulletin board, general native-window inventory, reliable session recovery, broader system controls, and complete cross-application execution still require implementation and validation.

This distinction is essential.

Graphite's future should be built on what the existing code demonstrably supports rather than on what the interface merely suggests.

The next development effort should connect these foundations into complete workflows, not replace them with a second competing system.

### From inspected code to demonstrated computer

The roadmap should distinguish existing mechanisms from finished behavior. The available source establishes a set of record models, reasoners, operations, and selected native application bridges. The Living Desktop adds a synchronized selection controller, relationship-ranking and layout system, persistent working tabs, split-view management, native-window inventory, and more complete machine and session integration.

Acceptance testing should proceed through actual tasks on the target hardware. Verify that a file selected in either navigation surface remains the same object after rename or move. Verify that edited source values mark dependents for review. Verify that closing an editor restores the board. Verify that native application dialogs remain reachable and that the Graphite shell can recover without destroying unrelated open work. Finally, compare Kasandra's stated completion against saved artifacts and operation records. An attractive demonstration can guide implementation; it is not itself proof of those outcomes.

## 18. A Day Working With the Living Desktop

Imagine beginning a project involving an unfamiliar electronic assembly.

You open Graphite.

The left tree shows your files and projects. The center is quiet. Kasandra is available in the right column.

You select the project.

The Living Desktop displays its relevant material.

A specification, electrical worksheet, circuit drawing, previous report, and several findings appear around the current focus. Their visual prominence reflects their relevance to the active project.

You select the specification.

The left tree identifies its location. The board changes to show its relationships.

You double-click it.

The center transitions into a readable document view.

Kasandra can inspect the same source, but she does not need to obstruct your reading.

You ask:

“Kas, review this assembly and tell me whether the proposed power supply is sufficient.”

Kasandra begins by examining the specification, available circuit information, and existing calculations.

She identifies the relevant voltage and current requirements.

The mathematical machinery evaluates the declared values, their units, and any documented operating conditions.

Suppose the settled power is within the stated limit but startup demand remains unresolved.

Kasandra should not collapse those observations into an unconditional approval.

She reports that the settled condition is supported and that startup requires further evaluation.

She may examine the circuit drawing or a second data sheet to locate the missing information.

If she finds a suitable source, she binds the result to that material.

If she cannot establish the required fact, she records an open question.

You can inspect the evidence trail.

The bulletin board highlights the specification, the calculation and the finding. Less relevant material remains nearby but visually subdued.

You decide to examine the worksheet yourself.

A double-click opens its working interface.

You split the center, keeping the specification visible beside the sheet.

Kasandra continues assisting without taking control of your keyboard.

You change a current value.

The worksheet updates. Graphite recognizes the changed revision and identifies calculations or reports that may depend on it.

Kasandra notices that the previously written summary still contains an older value.

She proposes reviewing the report.

You approve the operation.

Kasandra opens the relevant document through an appropriate supported interface, identifies the affected passage, and prepares a revision.

If the operation is permitted, she applies the change and verifies the resulting document.

She records what changed and which source values support the new statement.

The report becomes a visible output on the bulletin board.

You can open it in Graphite's compact view or in the full word processor.

Kasandra's panel shows that the report revision was completed, while the startup question remains unresolved.

The two states are not confused.

You close the working document.

The center returns to the bulletin board with the same file selected and its relationships preserved.

You then close Graphite for the evening.

When you return, the project still contains its sources, revisions, calculations, decisions, outputs, and unresolved questions.

Kasandra can resume from those records rather than reconstructing the entire history from a conversation.

That is the intended experience.

It is not a promise that every step is implemented in 0.8.6 today. It is the end-to-end behavior that future development should demonstrate.

### The transition the owner should actually experience

During this sequence, the interface should communicate changes quietly. When the current value is revised, only the affected calculation path becomes prominent. The dependent report tile grows or gains a review mark because it now matters to the task, not because every connection became equally urgent. Kasandra's suggestion identifies the precise inconsistency and offers a route to the report. A split view keeps the revised source visible beside the report without losing the board history.

The critical moment is after the correction: the saved report should become the current artifact, its revision and evidence should be inspectable, and the remaining startup question should still be open. Finishing one part of an assignment must not manufacture an all-clear verdict for the entire project. This is the kind of small, believable sequence a future hero demonstration ought to show.

## 19. What Makes This Different

The defining feature of Graphite is not simply that a language model can issue commands.

It is the integration of four capabilities that usually remain separate.

First, ordinary computing remains directly accessible. The owner can navigate files, use applications, and operate the machine without an assistant.

Second, the Living Desktop makes relationships between files and results visible. Information is encountered through its relevance and dependencies, not only its directory location.

Third, Kasandra can use the same machinery that the owner uses. Her purpose is to complete assignments, not merely explain how someone else could complete them.

Fourth, the resulting work retains an inspectable history. Sources, calculations, revisions, decisions, and outcomes remain connected.

These capabilities reinforce each other.

Better relationships improve Kasandra's context.

Better tool integration improves her ability to act.

Better evidence improves the reliability of her conclusions.

Better continuity reduces the work required to resume an assignment.

And a coherent desktop makes those benefits directly available to the owner.

The system should never confuse visual sophistication with correctness. A beautifully rendered relationship is still wrong if the connection is unsupported. An animated assistant is not useful merely because it appears busy.

Graphite should prioritize meaningful progress and make that progress legible.

### How success can be measured

The quality bar should include outcomes rather than interface novelty. Can the owner reach a related source from a finding in one or two intentional actions? Can Kasandra explain why a file received high relevance? Can a corrected value propagate through supported calculations while unchanged conclusions are left alone? Can the program distinguish an executed edit from a prepared suggestion? Can a session be resumed without losing the evidence trail?

The broader advantage is that the computer becomes less dependent on the owner remembering every application, path, command, and intermediate result. Yet that delegation must remain transparent. A system that completes more work while making its behavior impossible to inspect would miss the point of the Living Desktop.

## 20. The Final Vision

The finished Graphite should feel calm when nothing is happening and capable when much is happening.

The left tree shows where the owner's material lives.

The center reveals what matters around the selected object.

Opening a file moves naturally from understanding it to working on it.

Tabs and split views allow several pieces of work to remain present.

Native applications extend the available capabilities without breaking the desktop.

Kasandra watches over the active assignment, interprets its requirements, investigates evidence, selects appropriate tools, carries out authorized work, and reports what actually happened.

Her knowledge survives model changes through the project's durable records.

Her calculations remain inspectable.

Her uncertainty remains visible.

Her actions remain accountable to the owner.

The owner can take control at any moment.

That combination gives meaning to both concepts.

**The Living Desktop is a computer organized around the relationships and intentions of its owner.**

**The Ghost in the Shell is the intelligence capable of working within that computer, using its tools to transform intentions into results.**

Graphite does not need to imitate another desktop or another assistant.

It needs to make the computer itself a more coherent instrument for understanding and accomplishing work.

### A product standard, not a visual promise

The final release should be judged by an ordinary sustained working session: files discovered and opened naturally, relevance expressed without clutter, editing and split viewing that preserve context, Kasandra using appropriate tools under permission, native applications coexisting with Graphite, and recorded results that survive reopening the project. The desktop must remain useful with Kasandra switched off.

The essential experience is modest to describe and demanding to deliver: select something; understand its neighborhood; work on it; let Kasandra help; verify what changed; return to where you were. If those transitions become dependable, the Living Desktop and the Ghost in the Shell cease to be separate metaphors. They become one coherent way of using a computer.

The workshop is the computer.

Kasandra is the ghost.

And the owner remains the authority.

**GRAPHITE — Work to Solution.**
