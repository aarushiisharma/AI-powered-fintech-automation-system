"""
Shared event store — avoids circular imports between disputes and integrations routers.
"""

from mock_bank_api.models import WebhookEvent

# Central event store for the event-driven architecture
EVENT_STORE: list[WebhookEvent] = []
