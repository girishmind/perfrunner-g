import random
from collections import defaultdict
from threading import Timer
from time import sleep, time
from typing import Callable
from urllib import parse

from couchbase import experimental, subdocument
from couchbase.bucket import Bucket
from couchbase.exceptions import CouchbaseError, TemporaryFailError
from couchbase.n1ql import N1QLQuery
from couchbase.views.params import ViewQuery
from decorator import decorator
from txcouchbase.connection import Connection as TxConnection

from logger import logger

experimental.enable()


class ErrorTracker:

    MSG = 'Function: {}, error: {}'

    MSG_REPEATED = 'Function: {}, error: {}, repeated {} times'

    QUIET_PERIOD = 10  # 10 seconds

    def __init__(self):
        self.errors = defaultdict(int)

    def track(self, method: str, exc: CouchbaseError):
        if type(exc) not in self.errors:
            self.warn(method, exc)  # Always warn upon the first occurrence
            self.check_later(method, exc)
        self.incr(exc)

    def incr(self, exc: CouchbaseError):
        self.errors[type(exc)] += 1

    def reset(self, exc: CouchbaseError):
        self.errors[type(exc)] = 0

    def check_later(self, method: str, exc: CouchbaseError):
        timer = Timer(self.QUIET_PERIOD, self.maybe_warn, args=[method, exc])
        timer.daemon = True
        timer.start()

    def warn(self, method: str, exc: CouchbaseError, count: int = 0):
        if count:
            logger.warn(self.MSG_REPEATED.format(method, exc, count))
        else:
            logger.warn(self.MSG.format(method, exc))

    def maybe_warn(self, method: str, exc: CouchbaseError):
        count = self.errors[type(exc)]
        if count > 1:
            self.reset(exc)
            self.warn(method, exc, count)
            self.check_later(method, exc)
        else:  # Not repeated, hence stop tracking it
            self.errors.pop(type(exc))


error_tracker = ErrorTracker()


@decorator
def quiet(method: Callable, *args, **kwargs):
    try:
        return method(*args, **kwargs)
    except CouchbaseError as e:
        error_tracker.track(method.__name__, e)


@decorator
def backoff(method: Callable, *args, **kwargs):
    retry_delay = 0.1  # Start with 100 ms
    while True:
        try:
            return method(*args, **kwargs)
        except TemporaryFailError:
            sleep(retry_delay)
            # Increase exponentially with jitter
            retry_delay *= 1 + 0.1 * random.random()


@decorator
def timeit(method: Callable, *args, **kwargs) -> float:
    t0 = time()
    method(*args, **kwargs)
    return time() - t0


class CBAsyncGen:

    TIMEOUT = 60  # seconds

    def __init__(self, **kwargs):
        self.client = TxConnection(quiet=True, **kwargs)
        self.client.timeout = self.TIMEOUT

    def create(self, key: str, doc: dict, persist_to: int = 0,
               replicate_to: int = 0, ttl: int = 0):
        return self.client.upsert(key, doc,
                                  persist_to=persist_to,
                                  replicate_to=replicate_to,
                                  ttl=ttl)

    def read(self, key: str):
        return self.client.get(key)

    def update(self, key: str, doc: dict, persist_to: int = 0,
               replicate_to: int = 0, ttl: int = 0):
        return self.client.upsert(key, doc,
                                  persist_to=persist_to,
                                  replicate_to=replicate_to,
                                  ttl=ttl)

    def delete(self, key: str):
        return self.client.remove(key)


class CBGen(CBAsyncGen):

    TIMEOUT = 10  # seconds

    def __init__(self, ssl_mode: str = 'none', n1ql_timeout: int = None, **kwargs):

        connection_string = 'couchbase://{host}/{bucket}?password={password}&{params}'
        connstr_params = parse.urlencode(kwargs["connstr_params"])

        if ssl_mode == 'data':
            connection_string = connection_string.replace('couchbase',
                                                          'couchbases')
            connection_string += '&certpath=root.pem'

        connection_string = connection_string.format(host=kwargs['host'],
                                                     bucket=kwargs['bucket'],
                                                     password=kwargs['password'],
                                                     params=connstr_params)

        self.client = Bucket(connection_string=connection_string)
        self.client.timeout = self.TIMEOUT
        if n1ql_timeout:
            self.client.n1ql_timeout = n1ql_timeout
        logger.info("Connection string: {}".format(connection_string))

    @quiet
    @backoff
    def create(self, *args, **kwargs):
        super().create(*args, **kwargs)

    @quiet
    @backoff
    @timeit
    def read(self, *args, **kwargs):
        super().read(*args, **kwargs)

    @quiet
    @backoff
    @timeit
    def update(self, *args, **kwargs):
        super().update(*args, **kwargs)

    @quiet
    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)

    @timeit
    def view_query(self, ddoc: str, view: str, query: ViewQuery):
        tuple(self.client.query(ddoc, view, query=query))

    @quiet
    @timeit
    def n1ql_query(self, query: N1QLQuery):
        tuple(self.client.n1ql_query(query))


class SubDocGen(CBGen):

    @quiet
    @timeit
    def read(self, key: str, field: str):
        self.client.lookup_in(key, subdocument.get(path=field))

    @quiet
    @timeit
    def update(self, key: str, field: str, doc: dict):
        new_field_value = doc[field]
        self.client.mutate_in(key, subdocument.upsert(path=field,
                                                      value=new_field_value))

    @quiet
    @timeit
    def read_xattr(self, key: str, field: str):
        self.client.lookup_in(key, subdocument.get(path=field,
                                                   xattr=True))

    @quiet
    @timeit
    def update_xattr(self, key: str, field: str, doc: dict):
        self.client.mutate_in(key, subdocument.upsert(path=field,
                                                      value=doc,
                                                      xattr=True,
                                                      create_parents=True))
