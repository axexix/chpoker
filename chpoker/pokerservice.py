from enum import StrEnum, auto, unique

import logging
import statistics

from .models.user import Session, SessionType, IdentityUser

logger = logging.getLogger(__name__)


class PokerServiceError(Exception):
    pass


class IdentityError(PokerServiceError):
    pass


class PermissionsError(PokerServiceError):
    pass


class PokerService:

    @unique
    class Events(StrEnum):
        LOGGED_IN_VOTER = auto()
        LOGGED_IN_HOST = auto()
        LOGGED_OUT_USER = auto()
        UPDATED_USER = auto()
        PROFILE_UPDATED = auto()
        JOINED_MEETING = auto()
        LEFT_MEETING = auto()
        NEW_TARGET = auto()
        SCORES_REVEALED = auto()
        NO_IDENTITY_FOUND = auto()
        LOG_MESSAGE_SENT = auto()

    def __init__(self, notification_service, identity_signer):
        self.notification_service = notification_service
        self.identity_signer = identity_signer
        self.sessions_by_id = {}
        self.users = []
        self.scores_revealed = False

    def find_user_by_name(self, name):
        for user in self.users:
            if user.name == name:
                return user

        raise ValueError()

    def get_scores(self):
        return [user.score for user in self.users if user.voting]

    def purge_inactive_sessions(self, user):
        for session in user.sessions:
            if not session.active:
                user.sessions.remove(session)
                del self.sessions_by_id[session.id]

    async def create_session(self, session_id, session_data):
        try:
            identity = self.identity_signer.unsign_identity(session_data.get("identity", ""))
        except AssertionError:
            logger.debug("error loading identity for session %s: %s", session_id, session_data)
            await self.notification_service.publish(session_id, self.Events.NO_IDENTITY_FOUND)
            raise IdentityError("error loading identity for session %s" % session_id)

        try:
            user = self.find_user_by_name(identity.username)
        except ValueError:
            user = IdentityUser(identity=identity)
            self.users.append(user)

        session = Session(id=session_id, user=user)
        user.sessions.append(session)
        self.sessions_by_id[session.id] = session

        return session

    async def on_connected(self, session_id, session_data):
        logger.info("connecting session: %s", session_id)

        try:
            session = self.sessions_by_id[session_id]
        except KeyError:
            session = await self.create_session(session_id, session_data)

        session.active = True
        self.purge_inactive_sessions(session.user)

        await self.update_user(session.user)

    async def on_disconnected(self, session_id):
        logger.info("disconnecting session: %s", session_id)

        session = self.sessions_by_id[session_id]
        session.active = False

        await self.update_user(session.user)

    async def notify(self, event, *args, session_type=SessionType.HOST | SessionType.VOTER, user=None):
        for session in self.sessions_by_id.values():
            if not(session.active and session.session_type & session_type):
                continue

            if user and session.user is not user:
                continue

            logger.debug("sending \"%s\" to %s with %s", event, session.id, args)
            await self.notification_service.publish(session.id, event, *args)

    async def notify_hosts(self, event, *args):
        logger.debug("notify hosts: %s (%s)", event, args)
        await self.notify(event, *args, session_type=SessionType.HOST)

    async def update_user(self, user, **kwargs):
        logging.debug("updating user %s: %s", user.id, str(dict(user)))

        for name, value in kwargs.items():
            setattr(user, name, value)

        await self.notify(self.Events.PROFILE_UPDATED, user, session_type=SessionType.ANY, user=user)

        if user.voting:
            await self.notify_hosts(self.Events.UPDATED_USER, user)

    async def login_voter(self, session_id):
        session = self.sessions_by_id[session_id]
        session.session_type = SessionType.VOTER

        await self.notification_service.publish(session_id, self.Events.LOGGED_IN_VOTER, not self.scores_revealed)
        await self.notify_hosts(self.Events.JOINED_MEETING, session.user)

        logger.info("client %s registered as a voter with username %s", session_id, session.user.name)

    async def login_host(self, session_id):
        session = self.sessions_by_id[session_id]
        session.session_type = session.session_type = SessionType.HOST

        if not session.user.can_host:
            raise PermissionsError("not allowed")

        await self.notification_service.publish(session_id, self.Events.LOGGED_IN_HOST)
        logger.info("client %s joined as host", session_id)

        for user in self.users:
            if user.active and user.voting:
                await self.notification_service.publish(session_id, self.Events.JOINED_MEETING, user)

    async def logout_user(self, session_id):
        session = self.sessions_by_id[session_id]
        session.session_type = SessionType.NONE

        await self.notification_service.publish(session_id, self.Events.LOGGED_OUT_USER)

        if not session.user.voting:
            await self.notify_hosts(self.Events.LEFT_MEETING, session.user)

        logger.info("logged out: %s", session_id)

    async def new_target(self, session_id):
        self.scores_revealed = False

        for user in self.users:
            user.score = 0

        await self.notify(self.Events.NEW_TARGET)

    async def estimate_target(self, session_id, score):
        user = self.sessions_by_id[session_id].user
        logger.info("score received from %s: %s", session_id, score)

        if self.scores_revealed:
            logger.info("the scores are already revealed, ignoring")
            return

        await self.update_user(user, score=score)

        if all(self.get_scores()):
            await self.reveal_scores()

    async def reveal_scores(self, session_id=None):
        logger.info("revealing scores")

        self.scores_revealed = True
        scores = sorted(filter(lambda x: x > 0, self.get_scores()))

        await self.notify(self.Events.SCORES_REVEALED)

        if scores:
            msg = "scores: %s\nmean: %.2f\nmedian: %.2f" % (
                ", ".join([str(score) for score in scores]),
                statistics.mean(scores),
                statistics.median(scores)
            )
        else:
            msg = "no votes"

        await self.notify_hosts(self.Events.LOG_MESSAGE_SENT, msg)
