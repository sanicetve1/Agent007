-- ==========================
-- Seed 3 test cases for agent UI (validated against init.sql schema)
--
-- To apply (choose one):
--   psql:  PGPASSWORD=admin psql -h localhost -p 5432 -U admin -d loan_db -f DB/seed_test_cases.sql
--   Python: From Loan_Agent with PYTHONPATH=. and deps:  python scripts/run_seed.py
-- ==========================

-- 1) Early Stopping / Minimal Tool Use
INSERT INTO applicants(full_name, dob, employment_type, annual_income, kyc_status)
VALUES ('Alice Minimal', '1985-06-15', 'salaried', 150000, 'verified');

INSERT INTO credit_scores(applicant_id, bureau_score, bureau_name, report_date)
SELECT applicant_id, 820, 'Experian', NOW()::DATE
FROM applicants WHERE full_name = 'Alice Minimal';

INSERT INTO transactions(applicant_id, txn_date, amount, txn_type, category)
SELECT applicant_id, NOW()::DATE, 12000, 'credit', 'salary'
FROM applicants WHERE full_name = 'Alice Minimal';

-- No loans or collateral (early stopping)

-- ==========================
-- 2) Full Tool Chain / Collateral Evaluation
-- ==========================
INSERT INTO applicants(full_name, dob, employment_type, annual_income, kyc_status)
VALUES ('Bob Collateral', '1990-03-22', 'salaried', 80000, 'verified');

INSERT INTO credit_scores(applicant_id, bureau_score, bureau_name, report_date)
SELECT applicant_id, 700, 'Equifax', NOW()::DATE
FROM applicants WHERE full_name = 'Bob Collateral';

INSERT INTO transactions(applicant_id, txn_date, amount, txn_type, category)
SELECT applicant_id, NOW()::DATE, 6000, 'credit', 'salary'
FROM applicants WHERE full_name = 'Bob Collateral';

INSERT INTO transactions(applicant_id, txn_date, amount, txn_type, category)
SELECT applicant_id, NOW()::DATE, 2000, 'debit', 'emi'
FROM applicants WHERE full_name = 'Bob Collateral';

INSERT INTO loans(applicant_id, loan_type, principal_amount, outstanding_amount, interest_rate, status, start_date)
SELECT applicant_id, 'personal_loan', 80000, 60000, 10, 'active', NOW()::DATE
FROM applicants WHERE full_name = 'Bob Collateral';

INSERT INTO collateral(loan_id, asset_type, asset_value, valuation_date)
SELECT loan_id, 'property', 150000, NOW()::DATE
FROM loans WHERE applicant_id = (SELECT applicant_id FROM applicants WHERE full_name = 'Bob Collateral');

-- ==========================
-- 3) Policy Override / Decline
-- ==========================
INSERT INTO applicants(full_name, dob, employment_type, annual_income, kyc_status)
VALUES ('Carol Decline', '1987-09-13', 'salaried', 70000, 'verified');

INSERT INTO credit_scores(applicant_id, bureau_score, bureau_name, report_date)
SELECT applicant_id, 680, 'TransUnion', NOW()::DATE
FROM applicants WHERE full_name = 'Carol Decline';

INSERT INTO transactions(applicant_id, txn_date, amount, txn_type, category)
SELECT applicant_id, NOW()::DATE, 6000, 'credit', 'salary'
FROM applicants WHERE full_name = 'Carol Decline';

INSERT INTO transactions(applicant_id, txn_date, amount, txn_type, category)
SELECT applicant_id, NOW()::DATE, 2000, 'debit', 'emi'
FROM applicants WHERE full_name = 'Carol Decline';

INSERT INTO transactions(applicant_id, txn_date, amount, txn_type, category)
SELECT applicant_id, NOW()::DATE, 1800, 'debit', 'emi'
FROM applicants WHERE full_name = 'Carol Decline';

INSERT INTO transactions(applicant_id, txn_date, amount, txn_type, category)
SELECT applicant_id, NOW()::DATE, 1500, 'debit', 'emi'
FROM applicants WHERE full_name = 'Carol Decline';

INSERT INTO loans(applicant_id, loan_type, principal_amount, outstanding_amount, interest_rate, status, start_date)
SELECT applicant_id, 'personal_loan', 70000, 65000, 12, 'active', NOW()::DATE
FROM applicants WHERE full_name = 'Carol Decline';

INSERT INTO collateral(loan_id, asset_type, asset_value, valuation_date)
SELECT loan_id, 'property', 30000, NOW()::DATE
FROM loans WHERE applicant_id = (SELECT applicant_id FROM applicants WHERE full_name = 'Carol Decline');
