import logging


class ClientNotificationService:

    def __init__(self, service_name = None, on_event = None):
        self.service_name = service_name
        self.on_event = on_event or self.log_unhandled_event

    async def log_unhandled_event(self, event_data):
        logging.warning("unhandled event: %s" % str(event_data))

    async def publish(self, client_id, event, *args):
        event_data = {
            "service":   self.service_name,
            "name":      str(event),
            "arguments": args
        }

        await self.on_event(client_id, event_data)
