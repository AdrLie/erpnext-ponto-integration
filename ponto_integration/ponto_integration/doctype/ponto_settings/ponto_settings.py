import frappe
import requests
from frappe.model.document import Document
from frappe.utils import add_to_date, now_datetime, get_datetime

PONTO_TOKEN_URL = "https://api.myponto.com/oauth2/token"

class PontoSettings(Document):
    def get_access_token(self) -> str:
        """Return a valid access token, refreshing it if necessary."""
        if self.is_token_expired():
            self.fetch_new_token()
        
        return self.access_token

    def is_token_expired(self) -> bool:
        """Check if the token is missing or expires within the next 5 minutes."""
        if not self.access_token or not self.token_expiry:
            return True
            
        expiry = get_datetime(self.token_expiry)
        buffer_time = add_to_date(now_datetime(), minutes=5)
        
        return expiry < buffer_time

    @frappe.whitelist()
    def fetch_new_token(self) -> None:
        """Fetch a new OAuth2 token from Ponto API and save it."""
        client_id = self.client_id
        client_secret = self.get_password("client_secret")

        if not client_id or not client_secret:
            frappe.throw("Client ID and Client Secret are required to fetch the token.")

        try:
            response = requests.post(
                PONTO_TOKEN_URL,
                data={"grant_type": "client_credentials"},
                auth=(client_id, client_secret),
                headers={"Accept": "application/json"},
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            self._update_token_data(data)
            
            frappe.msgprint("Successfully connected to Ponto API.")
            
        except requests.exceptions.RequestException as e:
            # Catat error detail di log internal Frappe, tampilkan pesan user-friendly di UI
            frappe.logger().error(f"Ponto API Connection Error: {str(e)}")
            frappe.throw("Failed to connect to Ponto API. Please check your network or credentials.")

    def _update_token_data(self, data: dict) -> None:
        """Private method to map response data to document fields and save."""
        self.access_token = data.get("access_token")
        expires_in = data.get("expires_in", 3600)
        self.token_expiry = add_to_date(now_datetime(), seconds=expires_in)
        
        self.save(ignore_permissions=True)