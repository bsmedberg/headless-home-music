class Event(object):
    def __init__(self, name, **kwargs):
        self.name = name
        for name, val in kwargs.items():
            setattr(self, name, val)

class UIEvent(Event):
    pass
