"""WebSocket API routes for real-time sync."""

import json
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.websocket_manager import manager, create_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["WebSocket"])


@router.websocket("")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: str = Query(..., description="Unique client identifier"),
):
    """
    WebSocket endpoint for real-time sync.

    Query params:
    - client_id: Unique client identifier (required)

    Client can send messages:
    - {"action": "subscribe", "events": ["sale_created", "stock_updated"]}
    - {"action": "unsubscribe", "events": ["sale_created"]}
    - {"action": "ping"} → server responds {"action": "pong"}
    - {"action": "get_status"} → server responds connection status
    """
    await manager.connect(websocket, client_id)

    try:
        # Send welcome message immediately
        await websocket.send_text(json.dumps(create_event(
            "system_alert",
            {"message": "Connected to POS-MOBILE WebSocket", "client_id": client_id},
            client_id=client_id,
        )))
        logger.info(f"Welcome message sent to {client_id}")

        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"error": "Invalid JSON"}))
                continue

            action = message.get("action")

            if action == "subscribe":
                events = message.get("events", [])
                await manager.subscribe(client_id, events)
                await websocket.send_text(json.dumps(create_event(
                    "system_alert",
                    {"message": f"Subscribed to: {', '.join(events)}", "events": events},
                    client_id=client_id,
                )))

            elif action == "unsubscribe":
                events = message.get("events", [])
                await manager.unsubscribe(client_id, events)
                await websocket.send_text(json.dumps(create_event(
                    "system_alert",
                    {"message": f"Unsubscribed from: {', '.join(events)}", "events": events},
                    client_id=client_id,
                )))

            elif action == "ping":
                await websocket.send_text(json.dumps({
                    "action": "pong",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }))

            elif action == "get_status":
                await websocket.send_text(json.dumps(create_event(
                    "system_alert",
                    {
                        "message": "Connection status",
                        "connected_clients": manager.get_connection_count(),
                        "client_id": client_id,
                        "subscriptions": list(manager.client_subscriptions.get(client_id, set())),
                    },
                    client_id=client_id,
                )))

            else:
                await websocket.send_text(json.dumps({
                    "error": f"Unknown action: {action}",
                    "client_id": client_id,
                }))

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {client_id}")
        manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}", exc_info=True)
        manager.disconnect(client_id)


@router.get("/status")
async def websocket_status():
    """Get WebSocket connection status."""
    return {
        "connected_clients": manager.get_connection_count(),
        "clients": manager.get_connected_clients(),
        "available_events": list(manager.event_types),
    }
