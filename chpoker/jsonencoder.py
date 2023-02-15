import json


class JSONEncoder(json.JSONEncoder):

    def default(self, o):
        try:
            return super().default(o)
        except TypeError:
            pass

        try:
            return dict(o)
        except TypeError:
            pass

        raise TypeError("not supported")
