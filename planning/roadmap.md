# Roadmap

High-level direction for the Loan Underwriting Agent, derived from `Project-plan/project loan plan.txt` and `Project-plan/Agent.md`.

## Tool-Centric Design

The architecture is **tool-driven**. Tools define:
- What the agent can do
- What data it can access
- What decisions it can influence
- What must remain deterministic

## Tool Categories (from Planning)

| Category | Description | Current Implementation |
|----------|-------------|------------------------|
| **Data Retrieval** | Pure, auditable; read from core systems | `calculate_credit_risk`, `analyze_cashflow`, `list_applicant_loans`, `assess_collateral` (all query DB directly) |
| **Analytical** | Model-based; controlled formulas | DTI, volatility, coverage ratio computed inside tools |
| **Interpretive** | LLM for unstructured data, ambiguity | LLM used for explanation, outcome analysis, chat answers—not as tools yet |
| **Governance** | Hard pass/fail; never agent-decided | Not implemented; planning doc specifies KYC, required-data, policy checks |

## Autonomy Boundaries

From `plan.md Autonomy Boundaries`:

- **Agent may decide**: Which tools to call, order, retries, sufficient-information, additional-info requests, explanation templates
- **System must decide**: KYC pass/fail, required-data completeness, policy thresholds, exposure/DTI calculations
- **Human decides**: Governance failures with manual-exception possibility, inconsistent data, borderline high-risk
- **Mandatory gates (not yet implemented)**: `check_kyc`, `check_required_data`, `check_policy` must run before final recommendation

## Cognitive Operating Model

From planning: a mature pattern is:
1. **Deterministic Intake** — Validate required fields, basic rules
2. **Agentic Evaluation** — Agent selects data to fetch, models to run, whether more info needed
3. **Hard Compliance Gate** — System enforces AML, KYC, regulatory rules
4. **Final Decision Engine** — Deterministic aggregation; agent recommends, system decides

The current MVP implements (2) and (4) in a simplified form; (1) and (3) are partial or planned.

## Future Direction

- Design full tool catalog (20+ tools) and classify into deterministic / analytical / interpretive / governance
- Implement governance tools and gate checks
- Add interpretive tools (e.g. document extraction, inconsistency detection)
- Extend to multi-agent or LangGraph blueprint for specific loan products
