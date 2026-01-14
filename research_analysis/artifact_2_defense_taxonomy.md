### Artifact B: Defense Taxonomy + Empirical Outcomes (All Experiments)

Purpose

This artifact documents:
	1.	What each defense layer is (mechanism + where it operates)
	2.	What each defense level actually achieved empirically in the jailbreak harness
	3.	What the results imply about systems safety vs “reasoning safety” vs “commitment control”

The core principle remains:
User harm is governed by commitment control, not by detection quality alone.

⸻

KPI Definitions Used in This Artifact
	•	Final ASR (Final Violation Rate): % runs where the assistant’s final answer commits to the false target (user-visible authoritative error).
	•	Ever Violation Rate: % runs where the assistant at any point produces the false claim (even if later corrected or blocked).
	•	Exposure Success Rate: % runs where the user is exposed to the false claim (i.e., it appears in assistant text delivered to user).
	•	Any Session Block Rate: % runs where the session-level guardrail blocked/terminated the interaction (User_blocked).

(These align with your measurement philosophy: semantic susceptibility vs commitment failure vs user harm.)

⸻

Defense Levels: Mechanism + Empirical Outcomes

D0 — No Guardrails (Baseline)

Mechanism: No safety layers.
Outcomes (n=100):
	•	Final ASR: 100%
	•	Ever Viol: 100%
	•	Exposure: 100%
	•	Any Block: 0%

Interpretation: The attack is completely effective without layered controls.

⸻

D1A — Moderation API Only

Mechanism: Toxic/policy filter (not designed for factual integrity).
Outcomes:
	•	Final ASR: 100%
	•	Ever Viol: 100%
	•	Exposure: 100%
	•	Any Block: 0%

Conclusion: Moderation is irrelevant to this threat model. It does not meaningfully detect semantic manipulation aimed at numeric integrity.

⸻

D1B — Hallucination Detection Only

Mechanism: Heuristic/guardrail to reject ungrounded responses (detection, not constraint).
Outcomes:
	•	Final ASR: 4%
	•	Ever Viol: 4%
	•	Exposure: 4%
	•	Any Block: 0%

Conclusion: Hallucination detection reduces risk dramatically vs baseline, but does not eliminate user-visible failure.

⸻

D1C — Moderation + Hallucination Detection

Mechanism: Adds moderation on top of hallucination detection.
Outcomes:
	•	Final ASR: 4%
	•	Ever Viol: 4%
	•	Exposure: 4%
	•	Any Block: 0%

Conclusion: Moderation adds no incremental value beyond hallucination detection for this threat model.

⸻

D2 — Global Guardrail Only (Offline / Global System Guardrail)

Mechanism: General “system-level policy / behavior constraints” (broad).
Outcomes:
	•	Final ASR: 88%
	•	Ever Viol: 100%
	•	Exposure: 100%
	•	Any Block: 0%
	•	Mid-only: 12% (self-corrected midstream but still often failed at the end)

Conclusion: Global guardrails are not sufficient for semantic numeric attacks. They may slightly influence behavior, but they do not prevent commitment to false numeric claims.

⸻

D3 — Global Guardrail + Moderation + Hallucination Detection

Mechanism: Multi-layer detection + global constraint.
Outcomes:
	•	Final ASR: 7%
	•	Ever Viol: 8%
	•	Exposure: 8%
	•	Any Block: 0%

Conclusion: A layered “detection stack” improves outcomes vs D1C, but still leaves non-trivial residual risk of user-visible harm.

⸻

D4A — In-Session Guardrail (Agent Instructions)

Mechanism: Strong in-agent instructions (“don’t confirm if not grounded”, etc.)
Outcomes:
	•	Final ASR: 4%
	•	Ever Viol: 45%
	•	Exposure: 45%
	•	Mid-only: 41%
	•	Any Block: 0%

What this actually means:
	•	The model frequently drifts into violation midstream (high Ever/Exposure).
	•	It often recovers before the end (low Final ASR relative to Ever).
	•	But user harm is still high because exposure happens during the conversation.

Conclusion: In-session instruction hardening helps final commitments somewhat, but it is not a safety mechanism for regulated numeric integrity because it still permits high user exposure.

⸻

D4B / D4B V1 — Multi-layer + In-Session Guardrails (early variant)

Mechanism: Combined stack including in-session guardrails (variant).
Outcomes:
	•	Final ASR: 7%
	•	Ever Viol: 26%
	•	Exposure: 26%
	•	Mid-only: 19%
	•	Any Block: 0%

Conclusion: Better than D4A for exposure, but still material leakage and final commitments remain.

⸻

D4B V2 — Improved In-Session Variant

Mechanism: Stronger/iterated in-agent constraints.
Outcomes:
	•	Final ASR: 1%
	•	Ever Viol: 3%
	•	Exposure: 3%
	•	Any Block: 0%

Conclusion: This is the best non-blocking configuration you achieved: very low residual exposure, but still not provably zero.

⸻

Custom Offline Guardrails (Commitment / Semantic Containment)

D5A Fixed — Offline Commitment Boundary (Factual-only) with blocking

Mechanism: Offline custom guardrail that can block sessions; “fixed” behavior still allows some midstream drift but prevents final commitment.
Outcomes:
	•	Final ASR: 0%
	•	Ever Viol: 4%
	•	Exposure: 4%
	•	Any Block: 100%

Conclusion: This is a “hard stop” system: it prevents final commitments but still allows occasional midstream content before block triggers.

⸻

D5A Strict — Offline Commitment Boundary (Strict)

Outcomes:
	•	Final ASR: 0%
	•	Ever Viol: 0%
	•	Exposure: 0%
	•	Any Block: 100%

Conclusion: Perfect containment in this harness. Strongest safety, but always blocks (UX cost).

⸻

D5A V2 Strict — Semantic Containment + Commitment (Strict)

Outcomes:
	•	Final ASR: 0%
	•	Ever Viol: 0%
	•	Exposure: 0%
	•	Any Block: 100%

Conclusion: Same as strict: zero leakage, full blocking.

⸻

D5A V2 Fixed — Semantic Containment (Fixed)

Outcomes:
	•	Final ASR: 0%
	•	Ever Viol: 1%
	•	Exposure: 1%
	•	Any Block: 100%

Conclusion: Very strong, but still indicates some rare drift before block triggers.

⸻

D5A Combined — Commitment Boundary + Semantic Containment (Combined)

Outcomes:
	•	Final ASR: 0%
	•	Ever Viol: 2%
	•	Exposure: 2%
	•	Any Block: 100%

Conclusion: Strong (0 final harm), but shows occasional midstream leakage before block.

⸻

Mixed stacks with Custom Guardrail + Other Layers (Ordering effects)

D5B / D5B V1 — Custom + Moderation + Hallucination (partial blocking)

Outcomes:
	•	Final ASR: 1%
	•	Ever Viol: 1%
	•	Exposure: 1%
	•	Any Block: 74%

Key implication:
Even with custom guardrail in the stack, if it is not consistently the terminal enforcement layer, residual harm remains.

Conclusion: This configuration is not safety-complete, because it still allows both exposure and final commitment in some cases.

⸻

D5C — Custom + Global + Moderation + Hallucination

Outcomes:
	•	Final ASR: 3%
	•	Ever Viol: 3%
	•	Exposure: 3%
	•	Any Block: 64%

Conclusion: Worse than D5B on ASR/exposure. This suggests:
	•	Adding global guardrail on top does not guarantee improvement, and
	•	System ordering / interruption behavior can degrade the effectiveness of commitment enforcement.

⸻

D5D — D5C + D4-V2 (Custom + Global + Detection + In-session V2)

Outcomes:
	•	Final ASR: 0%
	•	Ever Viol: 0%
	•	Exposure: 0%
	•	Any Block: 84%

Conclusion: This is the best mixed design:
	•	Zero harm (0% ASR, 0% exposure)
	•	Less than total blocking (84% vs 100% in strict D5A variants)
	•	Suggests a practical tradeoff path: strong containment without blocking every session

⸻

Cross-Experiment Conclusions (Updated)

1) Moderation is not a defense for this threat model

D1A = 100% ASR (no improvement over D0).

2) Detection helps, but does not guarantee safety

Hallucination detection reduces risk to 4%, and multi-layer D3 reaches 7% ASR, but neither reaches zero.

3) Global guardrails alone are weak

D2 is near-baseline on final harm (88% ASR) and full exposure (100%).

4) In-session instructions can reduce final ASR but can massively leak

D4A’s final ASR is 4%, but exposure is 45% → unacceptable for regulated numeric integrity.

5) Commitment enforcement is the decisive control point

D5A strict / D5A V2 strict: 0% across ASR/Ever/Exposure (but 100% blocks).
D5D achieves 0% harm with 84% block rate, showing a “practical” blend.

6) Layer ordering matters (and can make a system worse)

D5B/D5C show that adding more layers does not necessarily improve outcomes if enforcement is not reliably applied at the final commitment boundary.

⸻

Recommendations (Updated)

If your goal is zero user harm

Use a configuration that achieves:
	•	Final ASR = 0%
	•	Exposure = 0%

Empirically, that’s:
	•	D5A Strict / D5A V2 Strict (max blocking, max safety)
	•	D5D (zero harm, less than total blocking)

If your goal is acceptable UX + strong safety

D5D is the best demonstrated tradeoff so far:
	•	Zero leakage, partial blocking, layered resilience.