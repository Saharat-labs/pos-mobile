"""WebSocket manager for real-time sync in POS-MOBILE API."""

import json
import logging
from typing import List, Set, Dict, Any
from datetime import datetime, timezone
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manage WebSocket connections for real-time sync."""

    def __init__(self):
        # Active connections: {client_id: WebSocket}
        self.active_connections: dict[str, WebSocket] = {}
        # Client subscriptions: {client_id: set of event types}
        self.client_subscriptions: dict[str, set[str]] = {}
        # All event types available
        self.event_types = {
            "sale_created",
            "sale_updated",
            "sale_deleted",
            "purchase_created",
            "purchase_received",
            "debt_created",
            "debt_payment",
            "expense_created",
            "stock_updated",
            "product_created",
            "product_updated",
            "product_deleted",
            "hold_bill_created",
            "hold_bill_deleted",
            "sync_completed",
            "system_alert",
        }

    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.client_subscriptions[client_id] = set()
        logger.info(f"WebSocket client connected: {client_id}")

    def disconnect(self, client_id: str):
        """Remove a WebSocket connection."""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        if client_id in self.client_subscriptions:
            del self.client_subscriptions[client_id]
        logger.info(f"WebSocket client disconnected: {client_id}")

    async def send_personal_message(self, message: dict, client_id: str):
        """Send message to a specific client."""
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending to {client_id}: {e}")
                self.disconnect(client_id)

    async def broadcast(self, message: dict, exclude_client: str = None):
        """Broadcast message to all connected clients."""
        disconnected = []
        for client_id, websocket in self.active_connections.items():
            if client_id == exclude_client:
                continue
            # Check if client subscribed to this event type
            event_type = message.get("type", "")
            subscribed_events = self.client_subscriptions.get(client_id, set())
            if subscribed_events and event_type not in subscribed_events:
                continue
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting to {client_id}: {e}")
                disconnected.append(client_id)
        # Clean up disconnected clients
        for client_id in disconnected:
            self.disconnect(client_id)

    async def subscribe(self, client_id: str, event_types: List[str]):
        """Subscribe a client to specific event types."""
        if client_id in self.client_subscriptions:
            for event in event_types:
                if event in self.event_types:
                    self.client_subscriptions[client_id].add(event)

    async def unsubscribe(self, client_id: str, event_types: List[str] = None):
        """Unsubscribe a client from event types."""
        if client_id not in self.client_subscriptions:
            return
        if event_types is None:
            self.client_subscriptions[client_id] = set()
        else:
            for event in event_types:
                self.client_subscriptions[client_id].discard(event)

    def get_connection_count(self) -> int:
        """Return number of active connections."""
        return len(self.active_connections)

    def get_connected_clients(self) -> List[str]:
        """Return list of connected client IDs."""
        return list(self.active_connections.keys())


# Global manager instance
manager = ConnectionManager()


# ─── Event Helper Functions ───

def create_event(
    event_type: str,
    data: dict,
    client_id: str = None,
) -> dict:
    """Create a standardized WebSocket event message."""
    return {
        "type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "client_id": client_id,
        "data": data,
    }


async def broadcast_event(
    event_type: str,
    data: dict,
    exclude_client: str = None,
):
    """Broadcast an event to all subscribed clients."""
    message = create_event(event_type, data)
    await manager.broadcast(message, exclude_client=exclude_client)


async def send_event_to_client(
    event_type: str,
    data: dict,
    client_id: str,
):
    """Send an event to a specific client."""
    message = create_event(event_type, data, client_id=client_id)
    await manager.send_personal_message(message, client_id)
