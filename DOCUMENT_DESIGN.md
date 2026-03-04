# Design Document: Payment Prioritization Engine

## 1. Overview
This document outlines the technical design for a "Payment Prioritization Engine" within ERPNext. The feature allows finance users to generate optimal payment batches based on supplier priority and invoice age, while strictly adhering to real-time Ponto bank balances to prevent overdrafts.

## 2. Data Model Design

To support this feature, we will introduce one new DocType, one Child DocType, and customize an existing DocType.

### 2.1. Supplier (Customization)
We need to categorize suppliers by strategic importance to weight them in the scoring algorithm.
* **Field Label:** Priority Level
* **Field Name:** priority_level
* **Type:** Select
* **Options:**
    * Critical (High weight)
    * Standard (Medium weight)
    * Low (Low weight)
* **Default:** Standard

### 2.2. Payment Batch (New DocType)
This is the main document for managing a payment proposal/run.
* **Type:** Standard DocType (Submittable)
* **Fields:**
    * naming_series: PB-.####
    * bank_account: Link (Bank Account) - Filtered to Ponto-linked accounts.
    * ponto_balance: Currency - Read Only, fetches real-time balance from API.
    * total_payment_amount: Currency - Sum of selected invoices.
    * status: Select (Draft, Submitted, Cancelled).
    * invoices: Table (Payment Batch Item).

### 2.3. Payment Batch Item (New Child DocType)
Stores the snapshot of the invoice data and its score at the time of batch creation.
* **Fields:**
    * purchase_invoice: Link (Purchase Invoice).
    * supplier: Link (Supplier).
    * due_date: Date.
    * priority_score: Float - The calculated score used for sorting.
    * outstanding_amount: Currency.
    * payment_amount: Currency - Amount to pay in this batch.

---

## 3. Scoring Logic (The Algorithm)

The system will automatically fetch outstanding Purchase Invoices and rank them. The ranking formula balances "Strategic Importance" with "Urgency" (Age).

**The Formula:**
Score = (Supplier Weight * 10) + (Days Overdue * 0.5)

**Weight Configuration:**
* Critical: 3 Points
* Standard: 2 Points
* Low: 1 Point

**Example Scenario:**
* Invoice A (Critical Supplier, Not Due yet):
  (3 * 10) + (0 * 0.5) = 30
* Invoice B (Low Priority, 60 Days Overdue):
  (1 * 10) + (60 * 0.5) = 10 + 30 = 40

**Result:** Invoice B is prioritized over Invoice A. This algorithm ensures that while critical suppliers are preferred, we do not neglect low-priority vendors indefinitely until they become a liability.

---

## 4. Balance Guard (Real-Time Validation)

To prevent overdrafts, we implement a strict "Check-then-Act" mechanism using the Ponto API.

### 4.1. Fetching Logic
* **On Load:** When the Payment Batch form is opened, we call the get_balance method to update the ponto_balance field for user visibility.
* **UI Constraint:** The "Add Invoices" button will visually verify that total_payment_amount does not exceed ponto_balance.

### 4.2. Submission Guard (The Hard Gate)
Since the balance might change between the time the user drafts the document and submits it, we perform a final validation on the backend on_submit event.

    def validate_balance(self):
        # 1. Force refresh balance from Ponto API immediately
        live_balance = get_live_ponto_balance(self.account_id)
        
        # 2. Compare
        if self.total_payment_amount > live_balance:
            frappe.throw(f"Insufficient funds! Live Balance: {live_balance}, Required: {self.total_payment_amount}")

---

## 5. Race Condition Handling

**Scenario:** Two finance users (User A and User B) open the tool at the same time and try to approve/pay the same invoice (INV-001) in two different batches.

**Prevention Strategy:**
1.  **Filtering (Frontend):** The query to fetch "Outstanding Invoices" will exclude any Invoice currently linked to another Payment Batch that is in Draft or Submitted state.
2.  **Optimistic Locking (Backend):** Upon submission of the batch, the system iterates through each row.
    * It checks frappe.db.get_value("Purchase Invoice", row.invoice, "outstanding_amount").
    * If the outstanding amount is 0 (meaning User A just paid it), the system throws an error: "Invoice INV-001 has already been paid by another transaction. Please refresh."
    * This forces User B to reload and regenerate their batch, ensuring no double payments occur.

---

## 6. Traceability & Audit Trail

**Requirement:** A manager needs to understand why Invoice A was paid before Invoice B in a given batch.

**Solution:**
The Payment Batch Item child table serves as a historical snapshot. We do not calculate the score on the fly during viewing; we save it to the database at the time of creation.

* **The Audit:** By opening a submitted Payment Batch, the manager can see the specific priority_score column for every invoice as it was at that moment.
* **Transparency:** They will clearly see that "Vendor X" had a score of 50 (due to age) while "Vendor Y" had a score of 30, mathematically justifying the decision.