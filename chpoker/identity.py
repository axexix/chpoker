import base64
import itertools
import json
import pickle
from hashlib import blake2b
from hmac import compare_digest

from .models.identity import Identity, DebugIdentity


class InvalidPayload(Exception):
    pass


class InvalidSignature(Exception):
    pass


class BaseIdentitySigner:
    def sign_identity(self, identity: Identity):
        raise NotImplementedError()

    def unsign_identity(self, signed_identity: str):
        raise NotImplementedError()


class IdentitySigner(BaseIdentitySigner):
    KEY_SIZE = 32
    AUTH_SIZE = 32

    def __init__(self, secret_key):
        self.secret_key = secret_key

    def sign(self, payload):
        h = blake2b(digest_size=self.AUTH_SIZE, key=self.secret_key)
        h.update(payload)
        return h.hexdigest()

    def verify(self, payload, sig):
        good_sig = self.sign(payload)
        return compare_digest(good_sig, sig)

    def sign_object(self, payload):
        encoded_payload = base64.b64encode(pickle.dumps(payload))
        signature = self.sign(encoded_payload)

        payload_string = encoded_payload.decode("ascii")
        return f"{payload_string}:{signature}"

    def unsign_object(self, signed_payload):
        try:
            raw_payload, signature = signed_payload.split(":")
            encoded_payload = raw_payload.encode("ascii")
        except ValueError:
            raise InvalidPayload()

        if not self.verify(encoded_payload, signature):
            raise InvalidSignature()

        return pickle.loads(base64.b64decode(encoded_payload))

    def sign_identity(self, identity: Identity):
        return self.sign_object(identity.__dict__)

    def unsign_identity(self, signed_identity: str):
        assert signed_identity, "invalid identity string"

        identity_data = self.unsign_object(signed_identity)
        identity = Identity(**identity_data)
        assert identity.valid, "invalid identity"

        return identity


class DebugIdentitySigner(BaseIdentitySigner):
    def __init__(self):
        self.auto_user_counter = itertools.cycle(range(5))

    def sign_identity(self, identity: DebugIdentity):
        return json.dumps(identity.__dict__)

    def unsign_identity(self, signed_identity: str):
        if signed_identity:
            return DebugIdentity(**json.loads(signed_identity))

        next_id = next(self.auto_user_counter)

        return DebugIdentity(
            id="user_%d" % next_id,
            first_name="User",
            last_name="Debug",
            display_name="User %d" % next_id,
            can_moderate=True
        )
