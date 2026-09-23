from services.rsi_orchestrator.core import exact_replay
def test_exact_replay_zero_model_calls():
    r=exact_replay([{"source_kind":"observed","x":1},{"source_kind":"counterfactual","x":2}])
    assert r["model_calls"]==0 and r["cost_usd"]==0 and len(r["events"])==1
