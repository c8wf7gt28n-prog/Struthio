"""Clock Lab experiment stub. Fill in an explicit model before running."""
def investigate(inputs, lifetimes=None):
    if lifetimes is None:
        return {"state": "NEEDS_INPUT", "question": "When is each allocation live?"}
    raise NotImplementedError("Define and check the lifetime model in the execution pass")
