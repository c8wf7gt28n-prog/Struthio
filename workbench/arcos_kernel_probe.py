"""Real pinned FreeRTOS POSIX scheduler test. This does not select an F133 kernel."""
import json,shutil,sys
from .arcos_tools import sha


def probe(root, cmd):
    upstream=root/"software/arcos/upstream"
    for record in json.loads((upstream/"provenance.json").read_text()):
        if record["name"]!="freertos":
            continue
        for name,digest in record["files"].items():
            if sha(upstream/"freertos"/name)!=digest:
                raise ValueError("Pinned FreeRTOS source changed: "+name)
    cc=shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    if not cc or sys.platform not in ("linux","darwin"):
        return {"status":"BLOCKED","reason":"POSIX C compiler required for scheduler probe"}
    src=upstream/"freertos"
    port=src/"portable/ThirdParty/GCC/Posix"
    cfg=root/"software/arcos/bsp/freertos_host"
    out=root/"build/arcos/freertos_probe"
    version=cmd([cc,"--version"])
    cmd([cc,"-std=c11","-D_GNU_SOURCE","-pthread","-O2",
         "-I"+str(src/"include"),"-I"+str(port),"-I"+str(cfg),
         cfg/"scheduler_probe.c",src/"tasks.c",src/"queue.c",src/"list.c",
         port/"port.c",port/"utils/wait_for_event.c",src/"portable/MemMang/heap_4.c",
         "-o",out])
    result=json.loads(cmd([out],timeout=15))
    if result.get("messages")!=3:
        raise ValueError("FreeRTOS task/queue probe failed")
    return {"status":"PASS","compiler_version":version,"scheduler":result,
            "binary_sha256":sha(out),"target_build":"BLOCKED",
            "target_reason":"F133 BSP not selected or ported; no qualified cross-toolchain or board execution",
            "memory":{"configured_host_heap_bytes":262144,"measured_binary_file_bytes":out.stat().st_size,
                      "target_kernel_ram_bytes":None,"target_game_stack_bytes":None}}
