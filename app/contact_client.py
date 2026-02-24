from typing import Any, Dict, Optional
from app.exceptions import MauticAPIError
from app.mautic_client import MauticClient

class ContactClient:
    def __init__(self, mautic: MauticClient, create_endpoint: str):
        self.mautic = mautic
        self.create_endpoint = create_endpoint

    def create_contact(self, payload: Dict[str, Any]) -> int:
        if not payload.get("email"):
            raise ValueError("email is required")

        data = self.mautic.request_json("POST", self.create_endpoint, json_body=payload)

        contact = data.get("contact")
        if not isinstance(contact, dict) or not contact.get("id"):
            raise MauticAPIError("Contact created but missing contact.id", response_body=data)

        return int(contact["id"])

    def get_contact_by_email(self, email: str) -> Optional[int]:
        params = {"search": f"email:{email}", "limit": 1}
        data = self.mautic.request_json("GET", "api/contacts", params=params)
        
        contacts = data.get("contacts", {})
        if contacts:
            return int(next(iter(contacts)))
        return None

    def get_contact_by_id(self, contact_id: int) -> Dict[str, Any]:
        endpoint = f"api/contacts/{contact_id}"
        data = self.mautic.request_json("GET", endpoint)
        return data.get("contact", {})
