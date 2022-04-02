from json import JSONEncoder


class SimpleJsonEncoder(JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'to_json'):
            return obj.to_json()
        else:
            return obj.__dict__
