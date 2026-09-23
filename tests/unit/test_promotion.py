from services.rsi_orchestrator.core import promotion_gate
def test_rejects_hard_failure():
    g=promotion_gate({"composite":.5},{"composite":.9,"grounding":1},{"passed":False,"grounding_minimum":.9},1)
    assert not g["passed"]
def test_requires_gain():
    g=promotion_gate({"composite":.8},{"composite":.81,"grounding":1},{"passed":True,"grounding_minimum":.9},1)
    assert not g["passed"]
