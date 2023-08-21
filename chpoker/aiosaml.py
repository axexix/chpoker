import functools
import os.path
from datetime import datetime
from urllib.parse import urljoin

from aiohttp import web
from saml2 import (
    BINDING_HTTP_POST,
    BINDING_HTTP_REDIRECT,
    entity,
)
from saml2.config import Config as Saml2Config
from saml2.client import Saml2Client
from saml2.metadata import create_metadata_string
from saml2.saml import NAME_FORMAT_BASIC

from .models.identity import Identity

routes = web.RouteTableDef()


class AiosamlApplication(web.Application):
    def __init__(self, *args, base_url, idp_metadata_urls, sp_config, create_identity=None, pysaml_debug=False, **kwargs):
        super().__init__(*args, **kwargs)

        self.add_routes(routes)

        self.base_url = base_url
        self.idp_metadata_urls = idp_metadata_urls
        self.sp_config = sp_config
        self.create_identity = create_identity
        self.pysaml_debug = pysaml_debug

    @functools.cached_property
    def saml_config(self):
        acs_url = urljoin(self.base_url, str(self.router["asc"].url_for()))
        metadata_url = urljoin(self.base_url, str(self.router["metadata"].url_for()))

        config = Saml2Config()
        config.load({
            "debug": int(self.pysaml_debug),
            "entityid": "chpoker",
            "metadata": {
                "remote": [{"url": url} for url in self.idp_metadata_urls if url.startswith("http")],
                "local": [url for url in self.idp_metadata_urls if url.startswith("/")],
            },
            "attribute_map_dir": os.path.join(os.path.dirname(__file__), "saml_attributes"),
            "service": {
                "sp": {
                    "endpoints": {
                        "assertion_consumer_service": [
                            (acs_url, BINDING_HTTP_REDIRECT),
                            (acs_url, BINDING_HTTP_POST),
                        ],
                    },
                    "allow_unsolicited": True,
                    "authn_requests_signed": False,
                    "logout_requests_signed": True,
                    "want_assertions_signed": True,
                    "want_response_signed": False,
                    "required_attributes": [
                        "first_name",
                        "last_name"
                    ],
                    "optional_attributes": [
                        "display_name",
                        "can_moderate"
                    ],
                    "requested_attribute_name_format": NAME_FORMAT_BASIC,
                },
            },
            "valid_for": 24 * 7,  # hours
            **self.sp_config
        })

        return config

    @functools.cached_property
    def saml_client(self):
        return Saml2Client(self.saml_config)


async def assertion_consumer_service(request, *response_args):
    saml_client = request.app.saml_client
    authn_response = saml_client.parse_authn_request_response(*response_args)
    identity = authn_response.get_identity()

    identifier = authn_response.get_subject().text

    response = web.Response(status=302, headers={"Location": "/"})

    if request.app.create_identity:
        identity = Identity(
            id=identifier,
            first_name=identity["first_name"][0],
            last_name=identity["last_name"][0],
            display_name=identity["display_name"][0],
            can_moderate=identity["can_moderate"][0] == "true"
        )

        identity_string = request.app.create_identity(identity)
        valid_for = identity.expiration - datetime.now()
        response.set_cookie("identity", identity_string, max_age=valid_for.total_seconds())

    return response


@routes.get("/acs", name="asc")
async def assertion_consumer_service_get(request):
    response = await assertion_consumer_service(request, request.query["SAMLResponse"], BINDING_HTTP_REDIRECT)
    return response


@routes.post("/acs")
async def assertion_consumer_service_post(request):
    post_data = await request.post()
    response = await assertion_consumer_service(request, post_data["SAMLResponse"], BINDING_HTTP_POST)
    return response


@routes.get("/metadata", name="metadata")
async def metadata_service(request):
    return web.Response(
        body=create_metadata_string(None, config=request.app.saml_config),
        content_type="application/xml"
    )
