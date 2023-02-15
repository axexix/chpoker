import aiohttp.web
import os.path
import json
import logging


class WebServer:

    def __init__(self):
        self.app = aiohttp.web.Application()

        self.app.router.add_get("/", self.index_handler)
        self.app.router.add_static("/static", os.path.join(os.path.dirname(__file__), "resources", "static"))

        self.next_client_id = 0

    def add_protocol(self, name, handler):
        self.app.router.add_get("/%s" % name, handler.connect)

    def run(self, **kwargs):
        aiohttp.web.run_app(self.app, **kwargs)

    async def index_handler(self, request):
        with open(os.path.join(os.path.dirname(__file__), "resources", "index.html")) as file:
            content = file.read()

        return aiohttp.web.Response(
            content_type = "text/html",
            text = content
        )
