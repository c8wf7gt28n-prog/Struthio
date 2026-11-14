"""Read-only probe: what Graphite's own code says about a synthetic 27B-class GGUF header.
Writes only under the scratch folder given as argv[1]."""
import struct, sys, json, subprocess
from pathlib import Path

out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, '/home/user/Struthio')


def s(text):
    raw = text.encode(); return struct.pack('<Q', len(raw)) + raw


def gguf(path, arch, layers, embd, heads, kv_heads, ctx=262144, template='{{ messages }}', tensor_type=0):
    kv = [('general.architecture', 8, s(arch)), ('general.name', 8, s('Synthetic header only')),
          (arch + '.context_length', 4, struct.pack('<I', ctx)), (arch + '.block_count', 4, struct.pack('<I', layers)),
          (arch + '.embedding_length', 4, struct.pack('<I', embd)), (arch + '.attention.head_count', 4, struct.pack('<I', heads)),
          (arch + '.attention.head_count_kv', 4, struct.pack('<I', kv_heads))]
    if template is not None: kv.append(('tokenizer.chat_template', 8, s(template)))
    body = b'GGUF' + struct.pack('<I', 3) + struct.pack('<Q', 1) + struct.pack('<Q', len(kv))
    for key, kind, value in kv: body += s(key) + struct.pack('<I', kind) + value
    body += s('token_embd.weight') + struct.pack('<I', 2) + struct.pack('<QQ', 32, 4) + struct.pack('<I', tensor_type) + struct.pack('<Q', 0)
    body += b'\0' * ((-len(body)) % 32) + b'\0' * 512
    path.write_bytes(body); return path


from sdk.cli.arc1cli import gguf_inspect
from workbench import local_brain, brain_runtime

GIB = 1024 ** 3
host = {'total_ram_bytes': 61 * GIB, 'available_ram_bytes': 58 * GIB, 'logical_cpus': 16, 'hardware_profile': {'graphics': []}}
brain_runtime.host = lambda: dict(host)

print('== 1. architecture gate ==')
for arch in ('qwen4', 'qwen4exp', 'qwen35moe', 'qwen3next', 'qwen35', 'qwen3'):
    value = gguf_inspect.inspect_set(gguf(out / (arch + '.gguf'), arch, 64, 5120, 64, 8))
    value['total_bytes'] = 17_000_000_000
    try:
        local_brain.configuration(value, {'context': 8192}); verdict = 'configuration accepted'
    except ValueError as exc: verdict = 'REFUSED: ' + str(exc)
    print(f"{arch:10s} profile={value['inspection']['architecture_profile']:24s} {verdict}")

print('== 2. template / quantisation gates ==')
value = gguf_inspect.inspect_set(gguf(out / 'notemplate.gguf', 'qwen35', 64, 5120, 64, 8, template=None)); value['total_bytes'] = 17_000_000_000
try: local_brain.configuration(value, {})
except ValueError as exc: print('no chat template ->', exc)
value = gguf_inspect.inspect_set(gguf(out / 'iq.gguf', 'qwen35', 64, 5120, 64, 8, tensor_type=22)); value['total_bytes'] = 17_000_000_000
print('tensor type 22 (an IQ type) ->', value['inspection']['quantization'], end=' ')
try: local_brain.configuration(value, {})
except ValueError as exc: print(exc)

print('== 3. memory arithmetic on a 61 GiB host, 58 GiB available (real configuration()) ==')
shapes = {'Qwen3-32B-like (64 layers, 5120, 64 heads, 8 kv)': (64, 5120, 64, 8),
          'Gemma3-27B-like (62 layers, 5376, 32 heads, 16 kv)': (62, 5376, 32, 16)}
for label, (layers, embd, heads, kvh) in shapes.items():
    value = gguf_inspect.inspect_set(gguf(out / 'shape.gguf', 'qwen35', layers, embd, heads, kvh))
    for size in (16_500_000_000, 17_000_000_000, 18_000_000_000, 22_000_000_000, 26_000_000_000):
        value['total_bytes'] = size
        for options in ({}, {'context': 8192}, {'context': 8192, 'memory_mb': 40960}):
            try:
                c = local_brain.configuration(value, options)
                text = 'ok  budget %d MiB, estimated peak %.1f GiB, KV %.2f GiB, threads %d' % (
                    c['memory_mb'], c['estimated_peak_bytes'] / GIB, c['estimated_kv_bytes'] / GIB, c['threads'])
            except ValueError as exc: text = 'REFUSED ' + str(exc)
            print(f"{label[:16]} file {size/1e9:4.1f} GB options {json.dumps(options):40s} {text}")
try:
    local_brain.configuration(value, {'context': 16384})
except ValueError as exc: print('context 16384 through configuration():', exc)
from workbench.agent_operations import validate
try: validate({'context': 16384}, local_brain.OPTIONS); print('schema accepts 16384')
except ValueError as exc: print('schema for context 16384 ->', str(exc)[:160])
from workbench import model_settings
print('model_settings.config with context 16384 ->', model_settings.config({'context': 16384, 'threads': 8, 'memory_mb': 32768}))

if len(sys.argv) > 2:
    print('== 4. bundled llama-server on an architecture it does not know ==')
    exe = Path(sys.argv[2])
    for arch in ('qwen4',):
        argv = [str(exe), '--model', str(out / (arch + '.gguf')), '--host', '127.0.0.1', '--port', '18099', '--ctx-size', '2048',
                '--threads', '4', '-ngl', '0', '--parallel', '1', '--load-mode', 'none', '--no-webui', '--no-warmup', '--device', 'none', '--fit', 'off']
        r = subprocess.run(argv, capture_output=True, text=True, timeout=60, env={'LD_LIBRARY_PATH': str(exe.parent), 'PATH': '/usr/bin:/bin'})
        tail = [line for line in (r.stdout + r.stderr).splitlines() if line.strip()][-6:]
        print(arch, 'exit', r.returncode); print('\n'.join('   ' + line[:200] for line in tail))
