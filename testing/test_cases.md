# Test Cases

Documentation of test scenarios for the Loan Agent MVP. No automated tests exist; these describe expected behavior for manual or future automated validation.

## Seed Data Personas

From `DB/seed_test_cases.sql`:

| Persona | Purpose |
|---------|---------|
| **Alice Minimal** | Early stopping; high income (150k), high score (820), single salary transaction; no loans → no collateral step |
| **Bob Collateral** | Full tool chain; income 80k, score 700, salary + EMI; one personal loan (60k outstanding) with property collateral (150k) → adequate coverage |
| **Carol Decline** | Policy override; income 70k, score 680, multiple EMI debits, loan 65k outstanding, collateral 30k → insufficient coverage, decline/conditional |

## Tool-Level Tests

### calculate_credit_risk

| Case | applicant_id | Expected |
|------|--------------|----------|
| Valid UUID | Bob’s applicant_id | risk_level, recommendation, dti, credit_score |
| Invalid UUID | "foo" | 400 / ValueError |
| Not found | random UUID | 400 / Applicant not found |

### analyze_cashflow

| Case | applicant_id | months | Expected |
|------|--------------|--------|----------|
| Valid | Bob’s applicant_id | 6 | recommendation, signals, net_cashflow |
| Out of range | any | 0 or 25 | 400 / months must be 1–24 |

### list_applicant_loans

| Case | applicant_id | include_closed | Expected |
|------|--------------|---------------|----------|
| Has loans | Bob’s applicant_id | false | loan_choices with 1 loan |
| No loans | Alice’s applicant_id | false | loan_choices [], loan_count 0 |

### assess_collateral

| Case | loan_id | threshold_ratio | Expected |
|------|---------|-----------------|----------|
| Adequate | Bob’s loan_id | 1.0 | collateral_status: adequate |
| Insufficient | Carol’s loan_id | 1.0 | collateral_status: insufficient |
| Invalid | "bad" | 1.0 | 400 / loan_id must be UUID |

## Agent Flow Tests

### Deterministic Mode (ENABLE_AUTONOMY=false)

| Case | applicant_id | loan_id | Expected |
|------|--------------|---------|----------|
| Alice | Alice’s UUID | — | Early stop; no collateral; approve or conditional |
| Bob | Bob’s UUID | — | Full chain; collateral adequate; approve/conditional |
| Carol | Carol’s UUID | — | Full chain; collateral insufficient; decline or conditional |
| Missing applicant | — | — | 400 / applicant_id required |

### Autonomous Mode (ENABLE_AUTONOMY=true)

| Case | applicant_id | Expected |
|------|--------------|----------|
| With applicant | Bob’s UUID | ReAct loop; tool_call_sequence; agent_mode: autonomous |
| Without applicant | "" | clarification_needed; session_id; clarification_question |

### Clarification Resume

| Case | session_id | user_reply | Expected |
|------|------------|------------|----------|
| UUID reply | valid session | Bob’s applicant_id UUID | Resume from Planning; return underwriting result |
| Name reply (unique) | valid session | "Bob Collateral" | Resolve; resume; return result |
| Name reply (ambiguous) | valid session | "Alice" | clarification_needed with options |
| Invalid session | bogus | any | status: error, error: session_expired |

### Customer Chat

| Case | applicant_id | message | session_id | Expected |
|------|--------------|---------|------------|----------|
| New chat | Bob’s UUID | "What is my credit risk?" | — | answer with session_id |
| Continue chat | Bob’s UUID | "And collateral?" | from prior response | answer, same session_id |
| Missing applicant | — | "hello" | — | status: error, missing_applicant_id |

## API Endpoint Tests

| Endpoint | Method | Expected |
|----------|--------|----------|
| /health | GET | 200, { "status": "ok" } |
| /data/applicants | GET | 200, array of ApplicantSummary |
| /tools/calculate_credit_risk | POST | 200 with tool result or 400 |
| /agent/run | POST | 200 with underwriting result or clarification_needed |
| /agent/continue | POST (autonomy only) | 200 or session_expired |
| /agent/chat | POST (autonomy only) | 200 with answer |

## UI Manual Flows

1. **Applicant list**: Load UI; verify applicants appear.
2. **Analyze (deterministic)**: Select applicant, click Analyze; verify Overview shows risk, recommendation, tool sequence.
3. **Analyze (autonomous)**: With ENABLE_AUTONOMY=true, run without pre-selecting applicant; verify clarification; reply with name; verify result.
4. **Chat**: Select applicant; open chat; send message; verify answer and session persistence across messages.
5. **Tab切换**: Overview / Agent Sequence / Raw JSON tabs show correct data.
