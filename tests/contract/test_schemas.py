from packages.contracts_python.schemas import RetrievalPlan, EvaluationResult
def test_retrieval_schema():
    x=RetrievalPlan(queries=["q"]); assert x.context_k==6
def test_eval_pass():
    x=EvaluationResult(target_id="x",suite_ref="s",scores={},hard_constraints={"passed":True}); assert x.passed
