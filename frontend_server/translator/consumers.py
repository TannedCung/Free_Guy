"""
WebSocket consumers for real-time simulation observation.
"""

import logging

from channels.generic.websocket import AsyncJsonWebsocketConsumer

logger = logging.getLogger(__name__)


class SimulationConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer for live simulation observation.

    Connect: ws/simulations/{sim_id}/?token=<jwt>
    """

    async def connect(self) -> None:
        self.sim_id: str = self.scope["url_route"]["kwargs"]["sim_id"]
        self.group_name: str = f"simulation_{self.sim_id}"

        # Token validation and access control will be added in US-017
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code: int) -> None:
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content: dict, **kwargs: object) -> None:
        pass

    async def step_update(self, event: dict) -> None:
        await self.send_json(event)

    @classmethod
    async def broadcast_step(cls, sim_id: str, payload: dict) -> None:
        from channels.layers import get_channel_layer

        channel_layer = get_channel_layer()
        group_name = f"simulation_{sim_id}"
        await channel_layer.group_send(group_name, {"type": "step_update", **payload})
