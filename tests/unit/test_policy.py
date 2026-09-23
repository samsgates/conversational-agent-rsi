from packages.policy_dsl.core import content_hash, sign, verify, validate_mutation, apply_mutation
BASE={"id":"p","version":"1","safety_policy_ref":"s","evaluator_suite_ref":"e","action_policy":{}}
def test_signing():
    sig=sign(BASE,"k"); assert verify(BASE,sig,"k")
def test_protected_fields():
    c=dict(BASE); c["safety_policy_ref"]="x"; assert validate_mutation(BASE,c)
def test_allowed_mutation():
    c=apply_mutation(BASE,"action_policy",{"default_action":"clarify"}); assert not validate_mutation(BASE,c)
def test_hash_stable():
    assert content_hash(BASE)==content_hash(dict(reversed(list(BASE.items()))))
