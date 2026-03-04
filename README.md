# Ponto API Integration for ERPNext

This package contains a custom Frappe app (`ponto_integration`) developed as a technical assessment. It integrates ERPNext with the Ponto Sandbox API for OAuth 2.0 authentication, synchronizes bank transactions, and includes a technical design for a Payment Prioritization Engine.

## What's in this ZIP?
This ZIP contains the `frappe-bench` environment including the custom app located at `apps/ponto_integration`. 

*Note: The MariaDB database is NOT included in this folder structure. You will need to create a fresh site and install the apps on your local database.*

## Installation Guide (From ZIP)

### Step 1: Extract and Setup Environment
1. Extract the provided ZIP file.
2. Open your terminal and navigate into the extracted directory:
    cd frappe-bench
3. Re-link the Python environment and install dependencies (since virtual environment paths break when transferred between machines):
    bench setup env
    bench setup requirements

### Step 2: Set Up a Local Site
Since databases are not included in the bench folder, please create a new site to test the integration:

    bench new-site ponto-test.local
    bench get-app erpnext --branch version-15
    bench --site ponto-test.local install-app erpnext
    bench --site ponto-test.local install-app ponto_integration

### Step 3: Start the Server
    bench start
    bench use ponto-test.local

(Access the site via http://localhost:8000 or the port specified in the terminal).

---

## Testing the Features

### Part 1: Ponto Settings & OAuth 2.0 Token Generation
1. Log into the ERPNext site as Administrator.
2. Search for "Ponto Settings" in the global search bar.
3. Obtain your Client ID, Client Secret, and Account ID from the Ponto Sandbox Dashboard.
4. Enter the credentials into the Ponto Settings form and click Save.
5. Click the custom button "Fetch Token Now" in the top right corner. 
6. The system will connect via Client Credentials flow and automatically populate the Access Token and Expiry Date.

### Part 2: Bank Transaction Synchronization
1. Search for "Bank Account List" in ERPNext.
2. Create a new dummy Bank Account (e.g., "Ponto Main Account") and Save it.
3. Click the custom button "Sync Ponto Transactions" in the top right corner.
4. The system will auto-refresh the token if needed, fetch the latest 10 transactions, and save them as Drafts while preventing duplicates.
5. Search for "Bank Transaction List" to review the synced data.

---

##  Part 3: Design Document - Payment Prioritization Engine

### 1. Overview
This section outlines the technical design for a "Payment Prioritization Engine" within ERPNext. It allows finance users to generate optimal payment batches based on supplier priority and invoice age, while strictly adhering to real-time Ponto bank balances to prevent overdrafts.

### 2. Data Model Design
2.1. Supplier (Customization)
We categorize suppliers by strategic importance to weight them in the scoring algorithm.
* Field: priority_level (Select: Critical, Standard, Low). Default: Standard.

2.2. Payment Batch (New DocType)
This is the main document for managing a payment proposal/run.
* Type: Submittable DocType
* Fields: naming_series, bank_account, ponto_balance (Real-time API fetch), total_payment_amount, status, invoices (Table).

2.3. Payment Batch Item (New Child DocType)
Stores the snapshot of the invoice data and its score at the time of batch creation.
* Fields: purchase_invoice, supplier, due_date, priority_score, outstanding_amount, payment_amount.

### 3. Scoring Logic (The Algorithm)
The system automatically fetches outstanding Purchase Invoices and ranks them.
Formula: Score = (Supplier Weight * 10) + (Days Overdue * 0.5)

* Weights: Critical (3), Standard (2), Low (1).
* Example: Invoice A (Critical, Not Due) = 30. Invoice B (Low, 60 Days Overdue) = 40.
* Result: Invoice B is prioritized. This ensures low-priority vendors are not neglected indefinitely until they become a liability.

### 4. Balance Guard (Real-Time Validation)
To prevent overdrafts, we implement a strict "Check-then-Act" mechanism.
* On Load: System fetches the live balance from the Ponto API.
* On Submit (The Hard Gate): The system performs a final backend validation. If the total payment amount exceeds the live balance, it throws a frappe.ValidationError to block the submission.

### 5. Race Condition Handling
Scenario: Two users attempt to pay the same invoice simultaneously.
* Frontend Filtering: The UI excludes invoices already linked to a Draft or Submitted Payment Batch.
* Optimistic Locking (Backend): Upon submission, the system checks the actual outstanding_amount of the Purchase Invoice in the DB. If it is 0 (paid by another user), it throws an error and forces the user to refresh their batch.

### 6. Traceability & Audit Trail
The Payment Batch Item child table serves as a historical snapshot. We save the priority score to the database at the moment of creation. If a manager audits a submitted batch, they will see the specific score for every invoice as it was at that exact moment, mathematically justifying the payment decision.


---

## 7. What I Would Do Differently (With More Time)

[cite_start]As requested, here is a brief note on how I would improve this solution with more time. To elevate this integration into a fully production-ready system, I would implement the following enhancements:

* [cite_start]**Webhook Listener:** Instead of relying on manual polling to fetch new transactions, I would set up a webhook listener to receive real-time transaction updates directly from Ponto.
* [cite_start]**Payment Initiation API:** I would extend the integration to trigger outbound payments directly from ERPNext using Ponto's Payment Initiation API, automating the full payment lifecycle rather than just generating entries.