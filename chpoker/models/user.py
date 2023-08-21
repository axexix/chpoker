import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Flag, auto

from .identity import Identity


class SessionType(Flag):
    NONE = auto()
    HOST = auto()
    VOTER = auto()
    ANY = NONE | HOST | VOTER


@dataclass
class Session:
    id: str = field(default_factory=lambda: str(uuid.uuid1()))
    session_type: SessionType = SessionType.NONE
    user: "User" = None
    connected: bool = True
    last_seen: datetime = field(default_factory=datetime.now)

    @property
    def host(self):
        return self.session_type & SessionType.HOST

    @property
    def voter(self):
        return self.session_type & SessionType.VOTER

    @property
    def active(self):
        return self.connected or (
            datetime.now() - self.last_seen < timedelta(minutes=10)
        )


@dataclass
class User:
    id: str = field(default_factory=lambda: str(uuid.uuid1()))
    score: int = 0
    sessions: list[Session] = field(default_factory=list)

    @property
    def remote_id(self):
        raise NotImplementedError()

    @property
    def name(self):
        raise NotImplementedError()

    @property
    def can_host(self):
        raise NotImplementedError()

    @property
    def voter_sessions(self):
        return [session for session in self.sessions if session.voter]

    @property
    def host_sessions(self):
        return [session for session in self.sessions if session.host]

    @property
    def voting(self):
        return len(self.voter_sessions) > 0

    @property
    def hosting(self):
        return len(self.host_sessions) > 0

    @property
    def active(self):
        return any([session.active for session in self.sessions])

    @property
    def connected(self):
        return any([session.connected for session in self.sessions])

    def __iter__(self):
        for k in ("id", "name", "score", "can_host", "active", "connected"):
            yield k, getattr(self, k)


@dataclass
class IdentityUser(User):
    identity: Identity = None

    @property
    def remote_id(self):
        return self.identity.id

    @property
    def name(self):
        if self.identity.display_name:
            return self.identity.display_name

        return self.identity.first_name

    @property
    def can_host(self):
        return self.identity.can_moderate
