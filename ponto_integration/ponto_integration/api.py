import frappe
import requests
from frappe.utils import flt, getdate

PONTO_API_BASE_URL = "https://api.myponto.com/accounts"

@frappe.whitelist()
def sync_ponto_transactions(bank_account: str) -> None:
    """Main entry point to fetch and sync Ponto transactions."""
    settings = frappe.get_single("Ponto Settings")
    _validate_settings(settings)

    url = f"{PONTO_API_BASE_URL}/{settings.account_id}/transactions"
    headers = {
        "Authorization": f"Bearer {settings.access_token}",
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, params={"limit": 10}, timeout=15)
        response.raise_for_status()
        
        transactions = response.json().get("data", [])
        created_count = _process_transactions(transactions, bank_account)
        
        if created_count > 0:
            frappe.db.commit()
            frappe.msgprint(f"Successfully synced {created_count} transactions.")
        else:
            frappe.msgprint("No new transactions found to sync.")

    except requests.exceptions.RequestException as e:
        frappe.logger().error(f"Ponto API Sync Error: {str(e)}")
        frappe.throw(f"Synchronization failed: {str(e)}")

def _validate_settings(settings: dict) -> None:
    """Ensure all required configurations are present."""
    if not settings.access_token:
        frappe.throw("Ponto Access Token is missing. Please fetch it in Ponto Settings.")
    if not settings.account_id:
        frappe.throw("Account ID is missing in Ponto Settings.")

def _process_transactions(transactions: list, bank_account: str) -> int:
    """Iterate through API data and insert missing Bank Transactions."""
    created_count = 0
    
    for tx in transactions:
        attrs = tx.get("attributes", {})
        tx_id = tx.get("id")
        
        # Deduplication check
        if frappe.db.exists("Bank Transaction", {"reference_number": tx_id}):
            continue

        amount = flt(attrs.get("amount"))
        
        doc = frappe.get_doc({
            "doctype": "Bank Transaction",
            "bank_account": bank_account,
            "date": getdate(attrs.get("valueDate")),
            "reference_number": tx_id,
            "description": attrs.get("description"),
            "bank_party_name": attrs.get("counterpartName"),
            "bank_party_iban": attrs.get("counterpartReference"),
            "deposit": amount if amount > 0 else 0.0,
            "withdrawal": abs(amount) if amount < 0 else 0.0,
            "currency": attrs.get("currency", "EUR")
        })
        
        doc.insert()
        created_count += 1
        
    return created_count