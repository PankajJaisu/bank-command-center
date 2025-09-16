-- SQL script to add new customer fields
-- Run this to update the customers table with CIBIL score and other fields

-- Add new columns to customers table if they don't exist
ALTER TABLE customers ADD COLUMN IF NOT EXISTS cibil_score INTEGER;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS days_since_employment INTEGER;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS employment_status VARCHAR(50);
ALTER TABLE customers ADD COLUMN IF NOT EXISTS cbs_income_verification VARCHAR(50);
ALTER TABLE customers ADD COLUMN IF NOT EXISTS salary_last_date DATE;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS pending_amount FLOAT;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS pendency VARCHAR(50);

-- Show the updated table structure
-- \d customers;

-- Optional: Insert some sample data matching the spreadsheet format
INSERT INTO customers (
    customer_no, name, email, phone, address,
    cibil_score, days_since_employment, employment_status, 
    cbs_income_verification, salary_last_date, 
    cbs_outstanding_amount, cbs_risk_level, 
    pending_amount, pendency, cbs_emi_amount, cbs_due_day,
    cbs_last_payment_date, created_at, updated_at
) VALUES 
('CUST-8801', 'John Smith', 'john.smith@email.com', '+1 (555) 123-4567', '1234 Main Street, City, State 12345',
 720, 15, 'Verified', '35%', '2025-08-02', 
 350000, 'red', 10000, 'Yes', 50000, 5,
 '2025-07-02', NOW(), NOW()),

('CUST-8802', 'Amit Sharma', 'amit.sharma@email.com', '+1 (555) 123-4568', '1234 Main Street, City, State 12345',
 650, 20, 'Unverified', '55%', '2025-08-05',
 520000, 'amber', 0, 'No', 75000, 10,
 '2025-07-05', NOW(), NOW()),

('CUST-8803', 'Priya Kapoor', 'priya.kapoor@email.com', '+1 (555) 123-4569', '1234 Main Street, City, State 12345',
 580, 45, 'High-Risk', '68%', '2025-08-07',
 800000, 'red', 3000, 'Yes', 60000, 15,
 '2025-07-07', NOW(), NOW()),

('CUST-8804', 'Michael Brown', 'michael.brown@email.com', '+1 (555) 123-4570', '1234 Main Street, City, State 12345',
 780, 10, 'Verified', '25%', '2025-08-01',
 200000, 'yellow', 13500, 'Yes', 45000, 20,
 '2025-07-01', NOW(), NOW()),

('CUST-8805', 'Sara Khan', 'sara.khan@email.com', '+1 (555) 123-4571', '1234 Main Street, City, State 12345',
 695, -10, 'Verified', '50%', '2025-08-03',
 450000, 'amber', 0, 'No', 55000, 25,
 '2025-07-03', NOW(), NOW()),

('CUST-8806', 'David Lee', 'david.lee@email.com', '+1 (555) 123-4572', '1234 Main Street, City, State 12345',
 610, -35, 'Unverified', '60%', '2025-08-06',
 670000, 'red', 32000, 'Yes', 80000, 30,
 '2025-07-06', NOW(), NOW()),

('CUST-8807', 'Pankaj Jaiswal', 'work.pankaj21@gmail.com', '+1 (555) 123-4573', '1234 Main Street, City, State 12345',
 650, 39, 'Verified', '75%', '2025-08-07',
 689949, 'amber', 85843, 'Yes', 68949, 15,
 '2025-07-07', NOW(), NOW())

ON CONFLICT (customer_no) DO UPDATE SET
    cibil_score = EXCLUDED.cibil_score,
    days_since_employment = EXCLUDED.days_since_employment,
    employment_status = EXCLUDED.employment_status,
    cbs_income_verification = EXCLUDED.cbs_income_verification,
    salary_last_date = EXCLUDED.salary_last_date,
    pending_amount = EXCLUDED.pending_amount,
    pendency = EXCLUDED.pendency,
    updated_at = NOW();

-- Show count of customers
SELECT COUNT(*) as customer_count FROM customers;
