import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.rsi_orchestrator.core import exact_replay, promotion_gate
def main():
    events=[{"source_kind":"observed","event_type":"message.received"},{"source_kind":"observed","event_type":"message.sent"}]
    replay=exact_replay(events)
    assert replay["model_calls"]==0 and replay["cost_usd"]==0
    gate=promotion_gate({"composite":.70},{"composite":.75,"grounding":.96},{"passed":True,"grounding_minimum":.9},.9)
    print({"exact_replay":replay,"promotion_gate":gate})
if __name__=="__main__": main()
