# Fixture stand-in for a reusable SDK tool (the content is not executed).
def compare(a, b, tolerance=0):
    return sum(1 for x, y in zip(a, b) if abs(x - y) > tolerance) == 0
