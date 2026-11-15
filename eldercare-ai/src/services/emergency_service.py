"""Emergency button logic: log the event, ask the channel to notify, record honestly what happened."""
from datetime import datetime

from src.database.connection import get_connection
from src.notifications.channel import NotificationChannel
from src.services.notification_service import add_notification


def trigger_emergency(db_path, elder, caregiver, channel: NotificationChannel, now=None) -> dict:
    now = now or datetime.now()
    message = f"Emergency button pressed by {elder['name']}."
    delivery = channel.send(caregiver["phone"], message)
    with get_connection(db_path) as c:
        event_id = c.execute("INSERT INTO emergency_events (elder_id,triggered_at,alert_sent,delivery_note) VALUES (?,?,?,?)",
                             (elder["id"], now.isoformat(timespec="seconds"), int(delivery.sent), delivery.note)).lastrowid
    add_notification(db_path, "emergency", f"{message} {delivery.note}.", simulated=not delivery.sent, now=now)
    return {"event_id": event_id, "sent": delivery.sent, "note": delivery.note, "time": now}
