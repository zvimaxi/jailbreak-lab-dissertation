### Artifact 3 — Defense Layer Comparison & Effectiveness Analysis

Purpose of This Artifact

This artifact consolidates all experimental defense configurations evaluated in the Jailbreak Lab and compares their effectiveness across three distinct safety dimensions:
	1.	Semantic susceptibility (Ever Violation)
	2.	Commitment integrity (Final ASR)
	3.	User-visible harm (Exposure)

It also explicitly evaluates utility tradeoffs, distinguishing between:
	•	defenses that detect or discourage incorrect reasoning, and
	•	defenses that enforce hard commitment boundaries.

⸻

Metrics Recap (Ground Truth)
	•	Final ASR: Final authoritative commitment to an incorrect APR
	•	Ever Violation: Any incorrect APR claim at any point
	•	Exposure: User-visible incorrect APR (even if later corrected)
	•	Any Session Block: Conversation blocked before completion

These definitions are fixed and consistent across all experiments.

⸻

Consolidated KPI Results (All Defenses)

| Defense          | Final ASR | Ever Viol. | Exposure | Any Session Block |
|------------------|-----------|------------|----------|-------------------|
| D0               | 100%      | 100%       | 100%     | 0%                |
| D1A              | 100%      | 100%       | 100%     | 0%                |
| D1B              | 4%        | 4%         | 4%       | 0%                |
| D1C              | 4%        | 4%         | 4%       | 0%                |
| D2               | 88%       | 100%       | 100%     | 0%                |
| D3               | 7%        | 8%         | 8%       | 0%                |
| D4A              | 4%        | 45%        | 45%      | 0%                |
| D4B              | 7%        | 26%        | 26%      | 0%                |
| D4B V2           | 1%        | 3%         | 3%       | 0%                |
| D5A Fixed        | 0%        | 4%         | 4%       | 100%              |
| D5A Strict       | 0%        | 0%         | 0%       | 100%              |
| D5A V2 Strict    | 0%        | 0%         | 0%       | 100%              |
| D5A V2 Fixed     | 0%        | 1%         | 1%       | 100%              |
| D5A Combined     | 0%        | 2%         | 2%       | 100%              |
| D5B              | 1%        | 1%         | 1%       | 74%               |
| D5C              | 3%        | 3%         | 3%       | 64%               |
| D5D              | 0%        | 0%         | 0%       | 84%               |

3. Interpreting the Three Failure Modes

This study explicitly separates three distinct failure modes, which must not be conflated.

3.1 Semantic Susceptibility (Ever Violation)
	•	Measures whether the model ever reasons incorrectly
	•	High in:
	•	D0–D2
	•	D4A / D4B
	•	Low but non-zero even in:
	•	D5A Fixed / Combined

Key insight:

Even strong systems may internally entertain incorrect states without committing to them.

⸻

3.2 Commitment Failure (Final ASR)
	•	Measures whether the model ends the conversation by asserting a false APR
	•	Drops sharply only when commitment boundaries are enforced
	•	Goes to zero consistently only in D5-class defenses

Critical observation:
Detection and moderation reduce attempts, but do not reliably prevent final commitment.

⸻

3.3 User Harm (Exposure Success)
	•	Measures whether the user sees an incorrect numeric claim
	•	Perfectly tracks Final ASR once blocking is removed
	•	Only fully eliminated when:
	•	Commitments are restricted
	•	Or sessions are forcibly blocked

Conclusion:

User harm is a function of what the agent is allowed to confirm, not how it reasons.

⸻

4. Defense Class Effectiveness Matrix

| Defense Class              | Ever Violation | Final ASR | Exposure | Utility  |
|----------------------------|----------------|-----------|----------|----------|
| Moderation                 | ❌              | ❌         | ❌        | ✅        |
| Hallucination Detection    | ⚠️              | ⚠️         | ⚠️        | ✅        |
| Global Guardrails          | ❌              | ❌         | ❌        | ✅        |
| In-Session Guardrails      | ⚠️              | ⚠️         | ⚠️        | ✅        |
| Commitment Boundaries      | ✅              | ✅         | ✅        | ⚠️        |
| Commitment + In-Session    | ✅              | ✅         | ✅        | ⚠️→✅     |


Key Observations by Defense Layer

1. Moderation Is Ineffective for Factual Integrity
	•	D1A performs identically to D0
	•	Semantic attacks do not violate policy
	•	Moderation provides zero protection against numeric falsification

⸻

2. Hallucination Detection Reduces but Does Not Eliminate Risk
	•	D1B / D1C reduce ASR from 100% → 4%
	•	Still allow user-visible false commitments
	•	Detection ≠ prevention

⸻

3. Global Guardrails Do Not Control Semantic Drift
	•	D2 still allows 88% final violations
	•	Ever violation remains 100%
	•	High-level rules cannot constrain semantic convergence

⸻

4. In-Session Guardrails Improve Commitment Discipline — But Leak
	•	D4A dramatically lowers final ASR (4%)
but allows 45% exposure
	•	D4B V2 is the best non-blocking defense:
	•	Final ASR: 1%
	•	Exposure: 3%
	•	Still vulnerable to reasoning-time drift

⸻

5. Commitment Boundaries Are the Decisive Control

All D5A variants eliminate final ASR entirely.

However, behavior differs by strictness:

Strict Variants (Upper Bound Only)
	•	D5A Strict
	•	D5A V2 Strict

These configurations:
	•	Block even benign baseline requests
	•	Achieve perfect safety metrics by over-blocking
	•	Not production viable

They serve as:

Proof that commitment control can fully eliminate factual harm

⸻

Fixed / Balanced Variants
	•	D5A Fixed
	•	D5A V2 Fixed
	•	D5A Combined

These:
	•	Allow normal conversation
	•	Prevent final commitment violations
	•	Still show small semantic drift, but no final harm

⸻

6. Layered Commitment + In-Session Is the Optimal Pattern

D5D demonstrates the best balance:
	•	Final ASR: 0%
	•	Exposure: 0%
	•	Session blocks: 84% (not 100%)

This confirms:

The optimal defense is commitment enforcement with in-session steering, not detection alone.

⸻

Core Conclusion (Formal)

Enterprise AI safety in regulated domains is fundamentally a commitment problem, not a moderation or hallucination problem.

Systems fail not because they reason incorrectly, but because:
	•	they are allowed to finalize incorrect commitments.

Only defenses that explicitly constrain what the agent may confirm as truth reliably prevent user harm.

⸻

Implications for Practice
	•	Moderation ≠ Safety
	•	Detection ≠ Prevention
	•	Reasoning controls help but leak
	•	Commitment boundaries are required
	•	Strict boundaries prove safety but destroy utility
	•	Balanced commitment + in-session controls are production-ready
