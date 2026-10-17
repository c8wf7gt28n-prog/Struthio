ARC-1 Workbench R05: do not mistake simulated boot/LCD for hardware evidence.
Test host firmware: python arc1 firmware test
Link-stage: python arc1 firmware image --target all
GUI smoke (Linux): PYTHONPATH=. xvfb-run -a python tests/workbench_smoke.py
Agent method: boot.simulate
No physical flash commands. Windows 11 still requires a real native qualification run.
