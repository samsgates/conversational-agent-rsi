from __future__ import annotations
from packages.policy_dsl.core import sign, verify, content_hash

class ArtifactRegistry:
    def __init__(self, signing_key: str):
        self.signing_key=signing_key
    def package_policy(self, document: dict) -> dict:
        return {"content_hash":content_hash(document),"signature":sign(document,self.signing_key),"document":document}
    def verify_policy(self, bundle: dict) -> bool:
        doc=bundle["document"]
        return content_hash(doc)==bundle["content_hash"] and verify(doc,bundle["signature"],self.signing_key)
