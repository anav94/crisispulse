from datasketch import MinHash, MinHashLSH
import time
class Deduper:
    def __init__(self, threshold: float = 0.8, window_seconds: int = 3600):
        self.lsh = MinHashLSH(threshold=threshold, num_perm=64)
        self.items = {}; self.window_seconds = window_seconds
    def _text_sig(self, text: str):
        m = MinHash(num_perm=64)
        for w in text.lower().split():
            if w: m.update(w.encode('utf8'))
        return m
    def should_drop(self, key: str, title: str, body: str, lat=None, lon=None, ts=None):
        now = ts or time.time(); self._expire(now)
        sig = self._text_sig(f"{title} {body}")
        for dk in list(self.lsh.query(sig)): return True, dk
        self.lsh.insert(key, sig); self.items[key] = now; return False, None
    def _expire(self, now):
        old=[k for k,t in self.items.items() if now - t > self.window_seconds]
        for k in old:
            try: self.lsh.remove(k)
            except Exception: pass
            self.items.pop(k, None)
