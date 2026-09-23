from contextlib import contextmanager
import time
@contextmanager
def span(name: str, attributes: dict | None=None):
    started=time.perf_counter()
    try: yield {"name":name,"attributes":attributes or {}}
    finally: _=time.perf_counter()-started
