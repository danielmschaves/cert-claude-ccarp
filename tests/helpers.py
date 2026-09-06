"""Item factory for tests. Real bank files are never used as test inputs."""


def make_item(qid="d1-001", obj="1.1", **over):
    item = {
        "qid": qid,
        "obj": obj,
        "rev": 1,
        "format": "multiple_choice",
        "select_n": 1,
        "stem": "A team ships a support agent. Latency is fine but answers drift. What best helps?",
        "principle": "grounding",
        "options": [
            {"key": "A", "text": "opt a", "correct": True, "rationale": "best here"},
            {"key": "B", "text": "opt b", "correct": False, "rationale": "real but inferior"},
            {"key": "C", "text": "opt c", "correct": False, "rationale": "real but inferior"},
        ],
    }
    item.update(over)
    return item
