import json
import logging
import uuid

import aiohttp.web

from .jsonencoder import JSONEncoder

logger = logging.getLogger(__name__)


class WebSocketRPCProtocol:

    def __init__(self):
        self.service_container = {}
        self.service_allowed_methods = {}
        self.disconnect_handlers = {}
        self.clients_by_id = {}

    async def connect(self, request):
        socket = aiohttp.web.WebSocketResponse()
        await socket.prepare(request)

        client_id, client_data = await self.handshake(socket)
        self.clients_by_id[client_id] = socket

        session_data = {
            **request.cookies,
            **client_data
        }

        for service_name, service in self.service_container.items():
            await service.on_connected(client_id, session_data)

        await self.receive_messages(socket, client_id)

        return socket

    async def handshake(self, socket):
        async for msg in socket:
            if msg.type == aiohttp.WSMsgType.text:
                rpc_body = json.loads(msg.data)
                logger.debug("rpc body: %s", rpc_body)

                if rpc_body["type"] != "hello":
                    raise Exception("invalid hello message")

                client_id = rpc_body.get("client_id", str(uuid.uuid1()))
                hello_message = {
                    "type": "hello",
                    "client_id": client_id
                }

                await socket.send_str(json.dumps(hello_message))
                return client_id, {k: v for k, v in rpc_body.items() if k not in ("type", "client_id")}

            elif msg.type == aiohttp.WSMsgType.close:
                raise Exception("connection closed without explanation")

        raise Exception("no handshake received")

    async def receive_messages(self, socket, client_id):
        async for msg in socket:
            if msg.type == aiohttp.WSMsgType.text:
                try:
                    message_body = json.loads(msg.data)
                    if message_body["type"] != "rpc":
                        raise Exception("unhandled message of type %s" % message_body["type"])

                    rpc_body = message_body["rpc"]
                    service_name = rpc_body["service"]
                    method_name = rpc_body["method"]
                    service = self.service_container[service_name]

                    if method_name in self.service_allowed_methods[service_name]:
                        await getattr(service, method_name)(client_id, **rpc_body.get("params", {}))
                    else:
                        logger.warning("method %s is not allowed for service %s", method_name, service_name)
                except Exception as e:
                    logger.exception(str(e))
            elif msg.type == aiohttp.WSMsgType.close:
                pass

        for service_name, service in self.service_container.items():
            await service.on_disconnected(client_id)

    def register_service(self, service_instance, allowed_methods):
        service_name = service_instance.__class__.__name__
        self.service_container[service_name] = service_instance
        self.service_allowed_methods[service_name] = allowed_methods

    async def send_event(self, client_id, event_data):
        socket = self.clients_by_id[client_id]

        message = {
            "type": "event",
            "event": event_data }

        await socket.send_str(json.dumps(message, cls = JSONEncoder))
