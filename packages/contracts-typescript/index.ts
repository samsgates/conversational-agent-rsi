export type SourceKind="observed"|"simulated"|"counterfactual"|"imported"|"human_authored";
export interface Usage{input_tokens:number;output_tokens:number;cached_tokens:number;reasoning_tokens:number;model_cost_usd:number;tool_cost_usd:number;compute_cost_usd:number;latency_ms:number}
export interface Citation{chunk_id:string;source_id:string;title:string;locator:string;quote:string;score:number}
export interface ConversationAction{family:string;name:string;confidence:number;rationale:string;requires_evidence:boolean;requires_tool:boolean}
export interface EvaluationResult{target_id:string;suite_ref:string;scores:Record<string,number>;hard_constraints:Record<string,unknown>;violations:Record<string,unknown>[];uncertainty:Record<string,number>}
