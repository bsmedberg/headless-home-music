import os
import pylirc
import select
from events import UIEvent

class Commands(object):
    def __init__(self, poll):
        thisdir = os.path.dirname(__file__)
        config = os.path.join(thisdir, "lirc.rc")
        self._fd = pylirc.init("headless-home-music", config, False)
        if self._fd == 0:
            raise RuntimeError("pylirc failed to initialized")

        poll.add_fd(self._fd, select.POLLIN | select.POLLHUP, self._cb)
        self._poller = poll

    def close(self):
        self._poller.remove_fd(self._fd)
        self._fd = 0

    def _cb(self, eventmask):
        while True:
            btns = pylirc.nextcode(False)
            if btns is None:
                return
            for b in btns:
                yield UIEvent(b)

if __name__ == "__main__":
    import poller
    p = poller.Poller()

    c = Commands(p)

    for e in p.run():
        print e.name
