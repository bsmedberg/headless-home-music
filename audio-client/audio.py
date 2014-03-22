import alsaaudio
import wave
import time
from events import AudioEvent

class WAVPlayer(object):
    _FORMAT_LIST = (
        alsaaudio.PCM_FORMAT_U8,
        alsaaudio.PCM_FORMAT_S16_LE,
        alsaaudio.PCM_FORMAT_S24_LE,
        alsaaudio.PCM_FORMAT_S32_LE
        )
    _PERIOD = 500
    _FUDGE = 0.1

    def __init__(self, filename, poller):
        self._w = wave.open(filename, "rb")
        self._p = poller
        self._d = None
        self._playing = False
        self._frame = 0
        self.autoclose = False

    def close(self):
        if self._playing:
            self.stop()
        self._w.close()

    def play(self):
        if self._playing:
            return
        self._play()

    def pause(self):
        if not self._playing:
            return
        self._stop()

    def stop(self):
        if self._playing:
            self._stop()
        self._frame = 0

    def _play(self):
        assert not self._playing
        self._playing = True
        self._data = None
        self._draining = False

        self._d = alsaaudio.PCM(card="plug:dmix", mode=alsaaudio.PCM_NONBLOCK)
        self._d.setchannels(self._w.getnchannels())
        self._d.setrate(self._w.getframerate())
        self._d.setformat(self._FORMAT_LIST[self._w.getsampwidth() - 1])
        self._d.setperiodsize(self._PERIOD)
        for fd, mask in self._d.polldescriptors():
            self._p.add_fd(fd, mask, self._cb)

        # skip to self._frame
        self._w.rewind()
        if self._frame:
            self._w.readframes(self._frame)

        self._write()

    def _stop(self):
        assert self._playing
        self._playing = False

        # reset _frame to the current position in case we're pausing/seeking
        try:
            avail, delay = self._d.availdelay()
            self._frame -= avail + delay
        except alsaaudio.ALSAAudioError:
            pass

        for fd, mask in self._d.polldescriptors():
            self._p.remove_fd(fd)
        self._d.close()
        self._d = None

        if self._draining:
            self._clear_timer()

        if self.autoclose:
            self.close()

    def _write(self):
        assert self._playing
        if self._draining:
            return
        while True:
            if self._data is None:
                self._data = self._w.readframes(self._PERIOD)
            if len(self._data) == 0:
                self._draining = True
                self._set_timer()
                return
            if self._d.write(self._data) == 0:
                return
            self._frame += len(self._data) / self._w.getsampwidth()
            self._data = None

    def _set_timer(self):
        assert self._draining
        self._stime = time.time()
        availdelay = sum(self._d.availdelay())
        timeout = availdelay / self._w.getframerate() + self._FUDGE
        self._p.add_timer(timeout, self._timerfn)

    def _clear_timer(self):
        assert self._draining
        self._p.remove_timer(self._timerfn)

    def _cb(self, reason):
        # hacky "make this a generator"
        if False: yield None
        if self._playing:
            self._write()

    def _timerfn(self):
        if not self._playing:
            return

        avail = 0
        try:
            avail, delay = self._d.availdelay()
        except alsaaudio.ALSAAudioError:
            pass
        if avail:
            self._set_timer()
        else:
            self._draining = False
            self._stop()
            self._frame = 0
            yield AudioEvent("AUDIO_COMPLETE", audio=self)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()

if __name__ == "__main__":
    import sys
    import os
    import poller
    import ircommands
    
    p = poller.Poller()
    ircommands.Commands(p)

    fname, = sys.argv[1:]

    blipfile = os.path.join(os.path.dirname(__file__), 'effects', 'mario.wav')

    with WAVPlayer(fname, p) as a:
        for e in p.run():
            if e.name == "KEY_PLAY":
                a.play()
            elif e.name == "KEY_PAUSE":
                a.pause()
            elif e.name == "KEY_STOP":
                a.stop()
            elif e.name == "AUDIO_COMPLETE":
                if e.audio == a:
                    print "all done, thanks!"
                    sys.exit(0)
            elif e.name == "KEY_POWER":
                print "bye"
                sys.exit(0)
            else:
                print "unhandled event: %s" % e.name
                a2 = WAVPlayer(blipfile, p)
                a2.autoclose = True
                a2.play()
