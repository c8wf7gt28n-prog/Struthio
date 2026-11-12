"""Bounded presentation admission. No I/O, execution, inference, or replay queue."""
from collections import deque


class CueGate:
    def __init__(self, cooldown=8.0, input_pause=2.0):
        self.cooldown = cooldown
        self.input_pause = input_pause
        self.last_input = float('-inf')
        self.last_cue = float('-inf')
        self.seen = deque(maxlen=64)

    def input(self, now):
        self.last_input = now

    def admit(self, key, now, *, visible=True, enabled=True, reduced=False):
        if key in self.seen:
            return False
        self.seen.append(key)  # Suppressed events are consumed, never queued.
        if (not visible or not enabled or reduced or
                now - self.last_input < self.input_pause or
                now - self.last_cue < self.cooldown):
            return False
        self.last_cue = now
        return True
