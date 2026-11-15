"""Notification channels. A message counts as SENT only if a channel reports it was.

Only the simulated channel exists. Real delivery (SMS, WhatsApp, push) would be a new subclass that returns
sent=True after the provider confirms; until then the app never claims anything was sent.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class Delivery:
    sent: bool
    note: str


class NotificationChannel(ABC):
    name = "base"

    @abstractmethod
    def send(self, recipient: str, message: str) -> Delivery:
        ...


class SimulatedChannel(NotificationChannel):
    name = "simulated"

    def send(self, recipient: str, message: str) -> Delivery:
        return Delivery(False, "Demo mode: caregiver notification simulated, nothing was sent")
