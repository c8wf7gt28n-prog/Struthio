# ARC-1 Workbench R07 — Agent Launcher API

The **R07** JSON-lines stdio endpoint remains `python arc1 agent`. Send one JSON request per line. Methods use the same `workbench.launcher.HostLauncher` engine as the human interface, but in a separate process (the GUI and agent process do not share in-memory running sessions).

Requests and example responses:

```json
{"id":1,"method":"launcher.list"}
{"id":2,"method":"launcher.launch_sim","params":{"path":"cartridges/hello_arc1.arc1cart","frames":120}}
{"id":3,"method":"launcher.status"}
{"id":4,"method":"launcher.stop_sim"}
```

- `launcher.list`: finds up to 200 cartridges on the local shelf and verifies their manifest+asset archive integrity; never runs code.
- `launcher.launch_sim`: requires a verified cartridge, exact trusted local manifest match, fresh local executable/binary digest, and `frames` in 1..36000. Starts an asynchronous host process and returns the current state. It does **not** execute binary content from the cartridge.
- `launcher.status`: reports `IDLE`, `RUNNING`, `COMPLETED`, `STOPPED`, etc. Completed runs include trace and output frame paths and SHA-256 identifiers.
- `launcher.stop_sim`: requests termination of the active **host** process. Reports `stopped: false` when no process is running.

The agent API provides **no arbitrary shell command**, no remote network listener, no direct device writes, and no hardware flash command. Normal source editing still requires `--allow-writes` and matching SHA-256.

`BOARD_OBSERVED` is never returned by R07 host launcher. This process cannot establish USB throughput, native display output, or target boot.
