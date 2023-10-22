import logging.config

from .config import Config
from .webserver import WebServer
from .pokerservice import PokerService
from .websocketrpcprotocol import WebSocketRPCProtocol
from .clientnotificationservice import ClientNotificationService
from .aiosaml import AiosamlApplication
from .identity import IdentitySigner, DebugIdentitySigner


def main():
    config = Config()

    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": True,
        "formatters": {
            "verbose": {
                "format": "[%(asctime)s] [%(levelname)s] [%(name)s.%(funcName)s] %(message)s",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "level": config.log_level,
                "formatter": "verbose"
            }
        },
        "loggers": {
            "chpoker": {
                "level": "DEBUG",
                "handlers": ["console"],
                "propagate": False,
            },
            "saml2": {
                "level": "DEBUG",
                "handlers": ["console"],
                "propagate": False,
            },
            "aiohttp": {
                "level": "DEBUG",
                "handlers": ["console"],
                "propagate": False,
            }
        }
    })

    rpc_protocol = WebSocketRPCProtocol()
    identity_signer = DebugIdentitySigner() if config.debug_identity else IdentitySigner(config.signing_key)

    poker_notification_service = ClientNotificationService(
        service_name=PokerService.__name__,
        on_event=rpc_protocol.send_event)
    pokerservice = PokerService(
        notification_service=poker_notification_service,
        identity_signer=identity_signer
    )

    rpc_protocol.register_service(pokerservice, {
        "login_voter",
        "login_host",
        "logout_user",
        "new_target",
        "estimate_target",
        "reveal_scores"
    })

    webserver = WebServer()
    webserver.add_protocol("ws", rpc_protocol)

    aiosaml_application = AiosamlApplication(
        base_url=config.base_url,
        idp_metadata_urls=config.idp_metadata_urls,
        sp_config=config.sp_config,
        create_identity=identity_signer.sign_identity,
        pysaml_debug=config.debug
    )
    webserver.app.add_subapp("/saml/", aiosaml_application)

    webserver.run(host=config.host, port=config.port)
