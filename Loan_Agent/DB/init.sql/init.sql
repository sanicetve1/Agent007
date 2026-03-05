-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ==========================
-- 1) applicants
-- ==========================
DROP TABLE IF EXISTS applicants CASCADE;
CREATE TABLE applicants (
    applicant_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    full_name TEXT NOT NULL,
    dob DATE NOT NULL,
    employment_type TEXT NOT NULL CHECK (employment_type IN ('salaried','self_employed')),
    annual_income NUMERIC NOT NULL,
    kyc_status TEXT NOT NULL CHECK (kyc_status IN ('verified','pending')),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_applicants_kyc_status ON applicants(kyc_status);

-- ==========================
-- 2) credit_scores
-- ==========================
DROP TABLE IF EXISTS credit_scores CASCADE;
CREATE TABLE credit_scores (
    applicant_id UUID PRIMARY KEY REFERENCES applicants(applicant_id) ON DELETE CASCADE,
    bureau_score INT NOT NULL CHECK (bureau_score BETWEEN 300 AND 900),
    bureau_name TEXT NOT NULL,
    report_date DATE NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ==========================
-- 3) transactions
-- ==========================
DROP TABLE IF EXISTS transactions CASCADE;
CREATE TABLE transactions (
    txn_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    applicant_id UUID NOT NULL REFERENCES applicants(applicant_id) ON DELETE CASCADE,
    txn_date DATE NOT NULL,
    amount NUMERIC NOT NULL CHECK (amount >= 0),
    txn_type TEXT NOT NULL CHECK (txn_type IN ('credit','debit')),
    category TEXT NOT NULL,
    merchant TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_transactions_applicant_date ON transactions(applicant_id, txn_date);

-- ==========================
-- 4) loans
-- ==========================
DROP TABLE IF EXISTS loans CASCADE;
CREATE TABLE loans (
    loan_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    applicant_id UUID NOT NULL REFERENCES applicants(applicant_id) ON DELETE CASCADE,
    loan_type TEXT NOT NULL,
    principal_amount NUMERIC NOT NULL CHECK (principal_amount >= 0),
    outstanding_amount NUMERIC NOT NULL CHECK (outstanding_amount >= 0),
    interest_rate NUMERIC NOT NULL CHECK (interest_rate >= 0),
    status TEXT NOT NULL CHECK (status IN ('active','closed')),
    start_date DATE NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_outstanding_le_principal CHECK (outstanding_amount <= principal_amount)
);

CREATE INDEX idx_loans_applicant ON loans(applicant_id);

-- ==========================
-- 5) collateral
-- ==========================
DROP TABLE IF EXISTS collateral CASCADE;
CREATE TABLE collateral (
    collateral_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    loan_id UUID NOT NULL REFERENCES loans(loan_id) ON DELETE CASCADE,
    asset_type TEXT NOT NULL,
    asset_value NUMERIC NOT NULL CHECK (asset_value >= 0),
    valuation_date DATE NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_collateral_loan ON collateral(loan_id);

-- ==========================
-- 6) documents
-- ==========================
DROP TABLE IF EXISTS documents CASCADE;
CREATE TABLE documents (
    document_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    applicant_id UUID NOT NULL REFERENCES applicants(applicant_id) ON DELETE CASCADE,
    document_type TEXT NOT NULL CHECK (document_type IN ('payslip','bank_statement','employment_letter')),
    extracted_income NUMERIC NOT NULL,
    verified BOOLEAN NOT NULL,
    document_date DATE NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_documents_applicant ON documents(applicant_id);

-- ==========================
-- 7) Seed Data: 10 Applicants (simplified for MVP)
-- ==========================
INSERT INTO applicants(full_name,dob,employment_type,annual_income,kyc_status)
VALUES
('Alice Johnson','1985-06-15','salaried',120000,'verified'),
('Bob Smith','1990-03-22','self_employed',80000,'verified'),
('Carol Lee','1978-11-05','salaried',40000,'verified'),
('David Brown','1982-08-18','self_employed',65000,'verified'),
('Eve Davis','1995-12-01','salaried',90000,'verified'),
('Frank Miller','1988-04-10','salaried',75000,'verified'),
('Grace Wilson','1992-07-07','self_employed',55000,'pending'),
('Hank Taylor','1980-01-25','salaried',150000,'verified'),
('Ivy Anderson','1987-09-13','salaried',60000,'verified'),
('Jack Thomas','1991-02-28','self_employed',70000,'verified');

-- Get applicant IDs for FK references
-- Use subqueries to link seed tables
-- Example credit_scores
INSERT INTO credit_scores(applicant_id,bureau_score,bureau_name,report_date)
SELECT applicant_id, FLOOR(RANDOM()*(850-650+1)+650)::INT,'Experian',NOW()::DATE
FROM applicants;

-- Example simple transaction seed (1 per applicant)
INSERT INTO transactions(applicant_id,txn_date,amount,txn_type,category)
SELECT applicant_id,NOW()::DATE,500,'credit','salary' FROM applicants;

-- Example simple loan seed (only for first 5 applicants)
INSERT INTO loans(applicant_id,loan_type,principal_amount,outstanding_amount,interest_rate,status,start_date)
SELECT applicant_id,'personal_loan',10000,5000,10,'active',NOW()::DATE FROM applicants LIMIT 5;

-- Example collateral (linked to first 3 loans)
INSERT INTO collateral(loan_id,asset_type,asset_value,valuation_date)
SELECT loan_id,'property',20000,NOW()::DATE FROM loans LIMIT 3;

-- Example documents (1 per applicant)
INSERT INTO documents(applicant_id,document_type,extracted_income,verified,document_date)
SELECT applicant_id,'payslip',annual_income/12,TRUE,NOW()::DATE FROM applicants;