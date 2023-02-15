from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class BaseIdentity:
    username: str
    can_moderate: bool

    @property
    def valid(self):
        raise NotImplementedError()


@dataclass
class Identity(BaseIdentity):
    expiration: datetime = field(default_factory=lambda: datetime.now() + timedelta(days=1))

    @property
    def valid(self):
        return self.expiration > datetime.now()


@dataclass
class DebugIdentity(BaseIdentity):

    @property
    def valid(self):
        return True
