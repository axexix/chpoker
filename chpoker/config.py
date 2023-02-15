import argparse
import logging
import tomllib
import os.path
import secrets


class Config:
    CONFIG_FILES = ["chpoker.toml", "~/.config/chpoker.toml", "/etc/chpoker.toml"]
    LOG_LEVEL_BY_VERBOSE = {
        0: logging.WARNING,
        1: logging.INFO,
        2: logging.DEBUG
    }
    SIGNING_KEY_SIZE = 32

    def __init__(self):
        self.config = {}

        self.load_config()
        self.load_args()

    def load_args(self):
        parser = argparse.ArgumentParser(description="chpoker server")

        parser.add_argument(
            "--host", "-H",
            type=str,
            default="0.0.0.0"
        )
        parser.add_argument(
            "--port", "-P",
            type=int,
            default=8080
        )
        parser.add_argument(
            "--verbose", "-v",
            action="count",
            default=0
        )
        parser.add_argument(
            "--debug-identity",
            action="store_true",
            default=False
        )

        self.config.update(vars(parser.parse_args()))

    def load_config(self):
        for filename in self.CONFIG_FILES:
            try:
                with open(os.path.expanduser(filename), "rb") as f:
                    self.config.update(tomllib.load(f))
            except FileNotFoundError:
                pass

    def __getattr__(self, name):
        return self.config[name]

    @property
    def log_level(self):
        return self.LOG_LEVEL_BY_VERBOSE[self.verbose]

    @property
    def debug(self):
        return self.verbose > 1

    @property
    def signing_key(self):
        try:
            return self.config["signing_key"].encode()
        except KeyError:
            pass

        return secrets.token_bytes(self.SIGNING_KEY_SIZE)
