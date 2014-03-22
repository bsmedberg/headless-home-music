import select
import sched
import time

class Poller(object):
    def __init__(self):
        self._p = select.poll()
        self._d = {}
        self._timers = []

    def add_timer(self, delay, fn):
        target = time.time() + delay
        self._timers.append((target, fn))

    def remove_timer(self, fn):
        for idx in xrange(0, len(self._timers)):
            target, tfn = self._timers[idx]
            if tfn == fn:
                del self._timers[idx]
                return
        raise ValueError("timer function not found")

    def add_fd(self, fd, eventmask, fn):
        if fd in self._d:
            raise ValueError("Double-registering fd poller")
        self._p.register(fd, eventmask)
        self._d[fd] = fn

    def remove_fd(self, fd):
        del self._d[fd]
        self._p.unregister(fd)

    def run(self):
        while True:
            if len(self._timers) == 0:
                timeout = None
            else:
                target = min(target for target, fn in self._timers)
                timeout = (target - time.time()) * 1000

            for fd, event in self._p.poll(timeout):
                if fd in self._d:
                    for e in self._d[fd](event):
                        yield e

            # Python list iterators aren't stable. Sort and remove instead
            self._timers.sort(key=lambda i: i[0])
            while len(self._timers) and self._timers[0][0] < time.time():
                target, fn = self._timers.pop(0)
                for e in fn():
                    yield e
