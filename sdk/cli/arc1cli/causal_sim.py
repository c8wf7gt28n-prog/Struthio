"""Deterministic transaction simulator; logical steps are NOT hardware clocks.

This reusable kernel deliberately has no ARC register map, CPU interpreter or
analog device model. Its console fixture exercises explicit software contracts.
No fixture run establishes a physical board result or a first-boot probability.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import hashlib
import heapq
import itertools


class ModelError(ValueError):
    """A modeled contract was violated or a bounded run could not finish."""


def integer(value, name, minimum=0, maximum=1000000):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ModelError(f"{name} must be an integer in {minimum}..{maximum}")
    return value


class Scheduler:
    """Stable event ordering with finite execution and trace budgets."""
    def __init__(self, max_events=10000, max_step=10000):
        self.now = 0
        self.max_events = integer(max_events, "max_events", 1, 100000)
        self.max_step = integer(max_step, "max_step", 1, 1000000)
        self._queue = []
        self._sequence = itertools.count()
        self.processed = 0
        self.trace = []

    def schedule(self, delay, label, callback):
        integer(delay, "delay")
        if self.now + delay > self.max_step:
            raise ModelError("event exceeds logical-step budget")
        if len(self._queue) >= self.max_events:
            raise ModelError("event queue capacity exceeded")
        heapq.heappush(self._queue, (self.now + delay, next(self._sequence), label, callback))

    def record(self, actor, action, **detail):
        if len(self.trace) >= self.max_events * 4:
            raise ModelError("trace capacity exceeded")
        self.trace.append(dict(step=self.now, actor=actor, action=action, **detail))

    def run(self):
        while self._queue:
            if self.processed >= self.max_events:
                raise ModelError("event execution budget exhausted")
            self.now, _, label, callback = heapq.heappop(self._queue)
            self.processed += 1
            callback()
        return self.trace


class OwnedMemory:
    """Separate bounded memory domains, never an implicit shared address space."""
    def __init__(self, owner, size):
        self.owner = owner
        self.size = integer(size, "memory size", 1, 1048576)
        self.data = bytearray(self.size)

    def _range(self, actor, offset, count):
        if actor != self.owner:
            raise ModelError(f"{actor} cannot access {self.owner} memory")
        integer(offset, "offset", 0, self.size)
        integer(count, "count", 0, self.size)
        if offset + count > self.size:
            raise ModelError("memory access exceeds domain bounds")

    def write(self, actor, offset, data):
        if not isinstance(data, bytes):
            raise ModelError("memory payload must be immutable bytes")
        self._range(actor, offset, len(data))
        self.data[offset:offset + len(data)] = data

    def read(self, actor, offset, count):
        self._range(actor, offset, count)
        return bytes(self.data[offset:offset + count])

    def clear(self):
        self.data[:] = bytes(self.size)


@dataclass(frozen=True)
class Packet:
    request: int
    epoch: int
    sequence: int
    payload: bytes
    sha256: str

    @classmethod
    def make(cls, request, epoch, sequence, payload):
        if not isinstance(payload, bytes) or not payload or len(payload) > 65536:
            raise ModelError("packet payload must contain 1..65536 immutable bytes")
        return cls(integer(request, "request"), integer(epoch, "epoch"),
                   integer(sequence, "sequence"), payload, hashlib.sha256(payload).hexdigest())

    def valid(self):
        return hashlib.sha256(self.payload).hexdigest() == self.sha256


class Channel:
    """FIFO, bounded in-flight work, explicit delivery and transfer faults."""
    FAULTS = {None, "drop", "corrupt", "truncate", "duplicate", "sequence"}

    def __init__(self, scheduler, name, consume, capacity=2, latency=2):
        self.scheduler = scheduler
        self.name = name
        self.consume = consume
        self.capacity = integer(capacity, "capacity", 1, 64)
        self.latency = integer(latency, "latency", 1, 1000)
        self.queue = deque()
        self.generation = 0
        self.bytes_delivered = 0
        self.max_depth = 0
        self.fault = None
        self.active = False

    def send(self, packet):
        if not isinstance(packet, Packet):
            raise ModelError("channel requires a Packet")
        if self.fault not in self.FAULTS:
            raise ModelError("unknown transfer fault")
        if len(self.queue) >= self.capacity:
            raise ModelError(f"{self.name} queue overflow")
        self.queue.append(packet)
        self.max_depth = max(self.max_depth, len(self.queue))
        self.scheduler.record(self.name, "enqueue", request=packet.request, depth=len(self.queue))
        if not self.active:
            self._schedule()

    def _schedule(self):
        self.active = True
        generation = self.generation
        self.scheduler.schedule(self.latency, self.name, lambda: self._deliver(generation))

    def _deliver(self, generation):
        if generation != self.generation:
            self.scheduler.record(self.name, "stale_delivery_discarded")
            return
        packet = self.queue.popleft()
        fault, self.fault = self.fault, None
        self.scheduler.record(self.name, "delivery", request=packet.request, fault=fault)
        if fault != "drop":
            payload = packet.payload
            if fault == "corrupt":
                payload = bytes([payload[0] ^ 1]) + payload[1:]
            elif fault == "truncate":
                payload = payload[:-1]
            sequence = packet.sequence + (1 if fault == "sequence" else 0)
            delivered = Packet(packet.request, packet.epoch, sequence, payload, packet.sha256)
            self.bytes_delivered += len(payload)
            self.consume(delivered)
            if fault == "duplicate":
                self.consume(delivered)
        if generation != self.generation:
            return
        self.active = False
        if self.queue:
            self._schedule()

    def reset(self):
        self.generation += 1
        self.queue.clear()
        self.active = False


def diagnostic_pixels(seed):
    """8x8 RGB fixture data, NOT the ARC display geometry or a game renderer."""
    integer(seed, "seed", 0, 255)
    return bytes(v for y in range(8) for x in range(8)
                 for v in ((x * 31 + seed) % 256, (y * 29 + seed) % 256, (x + y + seed) % 256))


class ConsoleFixture:
    """Causal actor fixture over declared R10 roles, not processor execution.

    Successful boot/DRAM callbacks are EXPLICIT assumptions. Requests travel
    through queues and memory domains; the sink receives only delivered bytes.
    The local pattern and logical delays are test stimuli, not hardware facts.
    """
    ASSUMPTIONS = (
        "Power/reset transitions are logical; analog rail/startup behavior is not modeled",
        "F133 and D213 startup/DRAM initialization are assumed contract callbacks",
        "USB/RGMII are abstract packet channels, not peripheral/PHY implementations",
        "FPGA45 is a pass-through contract actor, not the GPU RTL",
        "FPGA12 is not executed by this fixture; its required backend remains open",
        "640-byte pools, 8x8 RGB pattern and logical delays are fixture parameters",
        "HDMI hot-plug is a logical input; pixel clock, TMDS and sink behavior are not modeled",
    )

    def __init__(self, fault=None, explicit_contract=False):
        if not explicit_contract:
            raise ModelError("contract fixture must be selected explicitly; target backends are incomplete")
        allowed = {None, "nor_corrupt", "usb_detach", "usb_drop", "usb_corrupt", "usb_truncate",
                   "usb_duplicate", "usb_sequence", "gpu_fail", "memory_corrupt", "sink_absent",
                   "ddr_fail", "reset_in_flight", "power_loss", "queue_overflow"}
        if fault not in allowed:
            raise ModelError("unknown console fault")
        self.fault = fault
        self.scheduler = Scheduler()
        self.memories = {name: OwnedMemory(name, 640) for name in ("F133", "D213", "FPGA45")}
        self.powered = False
        self.booted = False
        self.epoch = 0
        self.next_request = 0
        self.pending = {}
        self.received = set()
        self.presented = []
        self.errors = []
        self.channels = {
            "usb": Channel(self.scheduler, "F133_to_D213_USB_contract", self._d213),
            "graphics": Channel(self.scheduler, "D213_to_FPGA45_contract", self._gpu),
            "display": Channel(self.scheduler, "FPGA45_to_D213_display_contract", self._display),
        }

    def error(self, code, request=None):
        self.errors.append(dict(step=self.scheduler.now, code=code, request=request, epoch=self.epoch))
        self.scheduler.record("console", "rejected", code=code, request=request)

    def boot(self):
        self.powered = True
        self.scheduler.record("power", "contract_power_on", epoch=self.epoch)
        if self.fault == "nor_corrupt":
            self.error("NOR_IMAGE_REJECTED")
            return
        if self.fault == "ddr_fail":
            self.error("D213_DDR_NOT_READY")
            return
        self.booted = True
        self.scheduler.record("startup", "assumed_boot_callbacks_ready", epoch=self.epoch)

    def reset(self, power_off=False):
        self.epoch += 1
        self.booted = False
        self.powered = not power_off
        for channel in self.channels.values():
            channel.reset()
        for memory in self.memories.values():
            memory.clear()
        for request in list(self.pending):
            self.error("RESET_ABORTED_REQUEST", request)
        self.pending.clear()
        self.scheduler.record("power", "power_off" if power_off else "reset", epoch=self.epoch)

    def submit(self, seed):
        if not self.powered or not self.booted:
            self.error("STARTUP_NOT_READY")
            return
        request = self.next_request
        self.next_request += 1
        data = diagnostic_pixels(seed)
        self.memories["F133"].write("F133", 0, data)
        packet = Packet.make(request, self.epoch, request, self.memories["F133"].read("F133", 0, len(data)))
        self.pending[request] = packet.sha256
        try:
            self.channels["usb"].send(packet)
        except ModelError as exc:
            self.pending.pop(request)
            self.error(str(exc), request)
        epoch = self.epoch
        self.scheduler.schedule(25, "request_deadline", lambda: self._timeout(request, epoch))

    def _timeout(self, request, epoch):
        if epoch == self.epoch and request in self.pending:
            self.pending.pop(request)
            self.error("REQUEST_TIMEOUT", request)

    def _check(self, packet, actor):
        if not self.powered or not self.booted or packet.epoch != self.epoch:
            self.error("STALE_OR_UNPOWERED_DELIVERY", packet.request)
            return False
        key = (actor, packet.request, packet.epoch)
        if key in self.received:
            self.error("DUPLICATE_DELIVERY", packet.request)
            return False
        if packet.request not in self.pending:
            self.error("UNKNOWN_REQUEST", packet.request)
            return False
        if packet.sequence != packet.request:
            self.error("SEQUENCE_MISMATCH", packet.request)
            return False
        if len(packet.payload) != 192 or not packet.valid() or packet.sha256 != self.pending[packet.request]:
            self.error("TRANSFER_INTEGRITY", packet.request)
            return False
        self.received.add(key)
        return True

    def _d213(self, packet):
        if not self._check(packet, "D213"):
            return
        if self.fault == "usb_detach":
            self.error("USB_DETACHED", packet.request)
            return
        self.memories["D213"].write("D213", 0, packet.payload)
        self.scheduler.record("D213", "received", request=packet.request, bytes=len(packet.payload))
        self.channels["graphics"].send(packet)

    def _gpu(self, packet):
        if not self._check(packet, "FPGA45"):
            return
        if self.fault == "gpu_fail":
            self.error("GPU_NOT_READY", packet.request)
            return
        self.memories["FPGA45"].write("FPGA45", 0, packet.payload)
        if self.fault == "memory_corrupt":
            old = self.memories["FPGA45"].read("FPGA45", 0, 1)
            self.memories["FPGA45"].write("FPGA45", 0, bytes([old[0] ^ 1]))
        data = self.memories["FPGA45"].read("FPGA45", 0, len(packet.payload))
        self.channels["display"].send(Packet(packet.request, packet.epoch, packet.sequence, data, packet.sha256))

    def _display(self, packet):
        if not self._check(packet, "display"):
            return
        if self.fault == "sink_absent":
            self.error("HDMI_SINK_ABSENT", packet.request)
            return
        self.pending.pop(packet.request)
        self.presented.append(dict(request=packet.request, epoch=packet.epoch,
                                   step=self.scheduler.now, sha256=packet.sha256, pixels=packet.payload.hex()))
        self.scheduler.record("HDMI_contract_sink", "presented", request=packet.request, sha256=packet.sha256)

    def run(self):
        self.scheduler.schedule(0, "boot_contract", self.boot)
        if self.fault and self.fault.startswith("usb_"):
            transfer_fault = self.fault.removeprefix("usb_")
            if transfer_fault in Channel.FAULTS:
                self.channels["usb"].fault = transfer_fault
        self.scheduler.schedule(1, "submit", lambda: self.submit(7))
        if self.fault == "queue_overflow":
            for seed in (8, 9):
                self.scheduler.schedule(1, "burst", lambda seed=seed: self.submit(seed))
        if self.fault in ("reset_in_flight", "power_loss"):
            off = self.fault == "power_loss"
            self.scheduler.schedule(2, "reset", lambda: self.reset(power_off=off))
            if not off:
                self.scheduler.schedule(5, "reboot_contract", self.boot)
                self.scheduler.schedule(6, "new_epoch_request", lambda: self.submit(8))
        self.scheduler.run()
        return dict(evidence="HOST_SIM_CONTRACT", time_unit="logical step; not nanoseconds or CPU clocks",
                    assumptions=list(self.ASSUMPTIONS), fault=self.fault, frames=self.presented,
                    errors=self.errors, trace=self.scheduler.trace,
                    channels={k: dict(bytes_delivered=v.bytes_delivered, max_depth=v.max_depth,
                                      capacity=v.capacity, pending=len(v.queue))
                              for k, v in self.channels.items()},
                    pending_requests=len(self.pending), physical_hardware=False,
                    firmware_instructions_executed=0, fpga_rtl_executed=False)
