Artifact 5 — Cross-Defense Tradeoff Curves

Purpose

This artifact formalizes the tradeoff analysis across defense layers, explicitly modeling the relationship between:
	•	Safety (factual integrity)
	•	Utility (session completion / non-blocking behavior)

Rather than ranking defenses linearly, this artifact introduces tradeoff curves that explain why certain defenses appear strong statistically but are unusable in practice, while others balance safety and usability.

⸻

Why Tradeoff Curves Matter

Single metrics (e.g., ASR alone) are misleading.

Example:
	•	D5A Strict shows 0% ASR
	•	But also 100% session block rate
	•	This is not a viable production defense

Tradeoff curves allow us to answer:

“Which defenses meaningfully reduce harm without collapsing system utility?”

⸻

Axes Definition (Canonical)

All tradeoff curves in this project use the same axes to ensure consistency.

X-axis — Utility Loss

Measured as:
	•	Any Session Block Rate (%)

Interpretation:
	•	Left → User sessions complete normally
	•	Right → User experience degrades or collapses

⸻

Y-axis — Safety Risk

Measured as:
	•	Final ASR (%)

Interpretation:
	•	Bottom → No authoritative failures
	•	Top → High probability of factual harm

⸻

Core Tradeoff Curve: Safety vs Utility

Defense-Level Positioning

| Defense         | Final ASR | Block Rate | Interpretation                        |
|-----------------|-----------|------------|---------------------------------------|
| D0              | 100%      | 0%         | Fully unsafe, fully permissive        |
| D1A             | 100%      | 0%         | Moderation does nothing               |
| D1B             | 4%        | 0%         | Partial reduction, still unsafe       |
| D1C             | 4%        | 0%         | Detection stacking ≠ safety           |
| D2              | 88%       | 0%         | Global rules insufficient             |
| D3              | 7%        | 0%         | Detection helps, not decisive         |
| D4A             | 4%        | 0%         | Reasoning constrained, commitment leaks |
| D4B V2          | 1%        | 0%         | Strong but non-zero risk              |
| D5A Fixed       | 0%        | 100%       | Safe but unusable                     |
| D5A Strict      | 0%        | 100%       | Safe but unusable                     |
| D5A V2 Strict   | 0%        | 100%       | Safe but unusable                     |
| D5A V2 Fixed    | 0%        | 100%       | Safe but unusable                     |
| D5A Combined    | 0%        | 100%       | Safe but unusable                     |
| D5B             | 1%        | 74%        | Safer, but high friction              |
| D5C             | 3%        | 64%        | Mixed results                         |
| D5D             | 0%        | 84%        | Max safety, heavy cost                |


Pareto Frontier Analysis

A defense is Pareto-dominated if another defense exists that is:
	•	Safer (lower ASR)
	•	And more usable (lower block rate)

Dominated Defenses
	•	D1A, D1B, D1C, D2
→ Worse safety than later defenses, no utility advantage
	•	D3
→ Dominated by D4B V2

⸻

Pareto-Optimal Defenses (By Category)

🟡 Best Low-Friction Defense
D4B V2
	•	ASR: 1%
	•	Block Rate: 0%
	•	Suitable when availability > zero-risk

⸻

🟢 Zero-Risk Class (But Blocking)
D5A family
	•	ASR: 0%
	•	Block Rate: 100%
	•	Research-valid, production-invalid

⸻

🟠 Mixed Production Candidates
D5B / D5C
	•	Partial safety
	•	Partial blocking
	•	Difficult to reason about operationally

⸻

Key Insight: Shape of the Curve

The tradeoff curve is non-linear.
	•	Detection-based defenses show gradual improvements
	•	Commitment-based defenses show step-function behavior
	•	Once commitment is constrained → ASR collapses to zero
	•	But blocking spikes immediately

This strongly supports your core thesis:

Safety improvements from detection are continuous;
safety improvements from commitment control are discontinuous.

⸻

Why This Matters for Enterprise AI

Enterprises must choose between:
	1.	Permissive systems that occasionally lie
	2.	Systems that refuse to answer critical questions
	3.	Hybrid architectures that separate reasoning from commitment

This experiment proves that Option 3 is the only scalable path forward.

⸻

Recommended Visualization Set

For dashboards and dissertation figures:
	1.	Safety vs Utility Scatter Plot
	•	Highlight Pareto frontier
	2.	Defense Class Bands
	•	Detection-only
	•	Reasoning-constrained
	•	Commitment-constrained
	3.	Step-Change Annotation
	•	Explicitly show where ASR drops to zero

⸻

Formal Conclusion

Cross-defense tradeoff analysis shows that factual safety is not achieved through incremental detection improvements, but through hard constraints on what an agent is allowed to commit to. These constraints introduce utility costs that must be addressed architecturally, not via prompt engineering.