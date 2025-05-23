import json
from channels.generic.websocket import AsyncWebsocketConsumer

class BookingStatusConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.lot_id = self.scope['url_route']['kwargs']['lot_id']
        self.group_name = f'booking_updates_lot_{self.lot_id}'

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def booking_update(self, event):
        await self.send(text_data=json.dumps({
            "space_id": event["space_id"],
            "status": event["status"],
        }))
