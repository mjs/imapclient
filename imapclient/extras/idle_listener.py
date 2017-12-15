"""Asynchronously wait for IMAP IDLE notifications.

This module is only compatible with Python 3.5+
"""

from collections import OrderedDict, namedtuple
from datetime import datetime, timedelta
import errno
import logging
import queue
import selectors
import socket
import ssl
import time
import threading
from typing import Optional, Set

import cachetools

from imapclient import IMAPClient

logger = logging.getLogger(__name__)

IMAP_IDLE_MAX_AGE = 780  # IDLE commands are renewed every 13 minutes
IMAP_IDLE_READ_TIMEOUT = 15

IDLENotification = namedtuple("IDLENotification",
                              ["client_id", "datetime"])

IDLEClient = namedtuple("IDLEClient",
                        ["client_id", "deadline", "imap_client"])


class ReceivedEOF(Exception):
    """The socket received an End of File.

    In non-blocking sockets, receiving b'' means that the other end initiated
    a shutdown of the connection.
    """


class Blacklist:
    """List of clients that often fail to keep the IDLE connection open.

    A client is considered blacklisted when it generated a handful of errors
    in a short period of time.
    After a while the blacklist expires, giving the client the opportunity
    to resume its normal activity if the problem is fixed.
    """

    TTL = 4 * 60 * 60     # Errors are forgotten after 4 hours
    MAX_ITEMS = 20        # Keep at most 20 errors per client
    ERRORS_THRESHOLD = 5  # A client is considered blacklisted after 5 errors

    def __init__(self):
        # We do not use a defaultdict here as the ratio of clients with
        # problems is rather small. A defaultdict would create many empty
        # instances of TTLCache.
        self._client_errors = dict()
        self._lock = threading.Lock()

    def __contains__(self, client_id: str) -> bool:
        """Tell whether a client is currently blacklisted or not."""
        with self._lock:
            try:
                errors = self._client_errors[client_id]
            except KeyError:
                return False
            else:
                return len(errors) >= self.ERRORS_THRESHOLD

    def record_error(self, client_id: str):
        with self._lock:
            if client_id not in self._client_errors:
                self._client_errors[client_id] = cachetools.TTLCache(
                    self.MAX_ITEMS, self.TTL, timer=time.monotonic
                )

            # We do not care what we put in the TTLCache, we are only
            # interested in the length of it
            self._client_errors[client_id][time.monotonic()] = True


class ExtOrderedDict(OrderedDict):
    """OrderedDict that allows easy fetching of the first inserted element."""

    def first_item(self) -> tuple:
        """Return the first item inserted.

        :returns: a tuple (key, value)
        """
        try:
            return next(iter(self.items()))
        except StopIteration:
            raise ValueError("Empty dictionary")


class IDLEListener:

    def __init__(self, stop_event: Optional[threading.Event]=None,
                 poison_pill: Optional[object]=None):
        """Asynchronously listen for IMAP IDLE notifications.

        When a notification is received it is put in the ``notifications``
        queue.

        :param stop_event: Optionally a threading.Event, if not given one will
                           be created and the `IDLEListener.stop()` must be
                           called to instruct threads to stop.
        :param poison_pill: Optionally an object that will be sent in the
                            notification queue when the IDLEListener
                            terminates. It allows to gracefully stop the
                            thread(s) processing notifications.
        """
        self._idle_clients = ExtOrderedDict()
        self._client_id_being_reactivated = None

        # Lock protecting _idle_clients and _client_id_being_reactivated
        self._lock = threading.RLock()

        self._selector = selectors.DefaultSelector()
        self.blacklist = Blacklist()
        self.notifications = queue.Queue()
        self.poison_pill = poison_pill if poison_pill else object()
        self._should_stop = stop_event if stop_event else threading.Event()

        self.schedule_reactivations_thread = threading.Thread(
            target=self.schedule_reactivations
        )
        self.await_events_thread = threading.Thread(
            target=self.await_events
        )

        logger.info("IDLEListener initialized with %s",
                    self._selector.__class__.__name__)

    def start(self):
        self.schedule_reactivations_thread.start()
        self.await_events_thread.start()

    def terminate(self):
        """Release all the resources used.

        After that, this object cannot be used again.
        """
        self._should_stop.set()
        self.await_events_thread.join()
        self.schedule_reactivations_thread.join()
        with self._lock:
            for client_id in list(self._idle_clients.keys()):
                self.remove_client(client_id, close=True)
        self._selector.close()
        self.notifications.put(self.poison_pill)
        logger.info("IDLEListener terminated")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.terminate()

    def add_client(self, client_id: str, imap_client: IMAPClient):
        """Add a client to listen for incoming emails.

        It is the responsibility of the caller to pass an IMAPClient
        instance connected and in IDLE mode.
        Once a client has been added, its IMAPClient shall not be used until
        it is removed.
        """
        with self._lock:

            if client_id in self._idle_clients:
                raise ValueError("Client already listen to, remove it first")

            imap_client._sock.setblocking(False)
            max_age = IMAP_IDLE_MAX_AGE
            deadline = datetime.utcnow() + timedelta(seconds=max_age)
            idle_client = IDLEClient(client_id, deadline, imap_client)
            self._idle_clients[client_id] = idle_client
            self._selector.register(
                imap_client._sock, selectors.EVENT_READ, client_id
            )

        logger.info("Added client %s to IDLEListener", client_id)

    def remove_client(self, client_id: str,
                      close: bool=False) -> Optional[IDLEClient]:
        """Remove a client form the list of clients to listen.

        After calling this method, the IMAPClient instance can be used normally
        again.

        :param close: Whether or not to close the client socket
        """
        with self._lock:
            try:
                idle_client = self._idle_clients[client_id]
            except KeyError:
                return None
            else:

                try:
                    self._selector.unregister(idle_client.imap_client._sock)
                except KeyError:
                    # Socket might be unregistered already
                    pass

                if close:
                    self._close_idle_client(idle_client)
                else:
                    try:
                        idle_client.imap_client._sock.settimeout(
                            IMAP_IDLE_READ_TIMEOUT
                        )
                    except OSError:
                        # Socket might be closed already
                        pass

                del self._idle_clients[client_id]
                logger.info("Removed client %s", client_id)
                return idle_client

    def has_client(self, client_id: str) -> bool:
        """Whether a client is being listen to or not."""
        return client_id in self.clients

    @property
    def clients(self) -> Set[str]:
        """Give the client IDs of clients being listen to."""
        with self._lock:
            clients = set(self._idle_clients.keys())
            if self._client_id_being_reactivated:
                clients.add(self._client_id_being_reactivated)
            return clients

    @classmethod
    def _close_idle_client(cls, idle_client: IDLEClient):
        """Free all resources associated with an ``IDLEClient``.

        After this call, the client and underlying attributes shall not be
        used again.
        Does not logout from the server to be able to call this code from both
        synchronous and asynchronous parts.
        """
        try:
            idle_client.imap_client._imap.close()
        except Exception:
            pass

    def await_events(self):
        while not self._should_stop.is_set():
            try:
                self._await()
            except Exception:
                logger.exception("Unhandled exception in await")
        logger.debug("Awaiting sockets thread terminated")

    def _await(self):
        """Await for data on registered clients.

        Puts a notification in ``self.notifications`` queue when the data
        received indicates that new events are available on a client.
        """
        logger.debug("Awaiting sockets thread started")
        while True:

            # When the Selector has no socket to listen to, it returns
            # immediately. This check prevents looping to fast and wasting
            # resources while the some sockets are being added to the selector.
            with self._lock:
                has_clients = bool(self._idle_clients)
            if not has_clients:
                logger.debug("No sockets to listen to")
                time.sleep(5)
                continue

            events = self._selector.select(timeout=5)
            logger.debug("%s sockets ready for reading", len(events))

            if self._should_stop.is_set():
                return

            for key, _ in events:
                client_id = key.data
                try:
                    data = self._drain_socket(key.fileobj)
                except (OSError, ssl.SSLError, ReceivedEOF) as e:
                    logger.warning(
                        "Error while reading data from IMAP IDLE socket",
                        exc_info=e
                    )
                    self.remove_client(client_id, close=True)
                    self.blacklist.record_error(client_id)
                else:
                    logger.debug("Received from client %s: %s",
                                 client_id, data)
                    # TODO: hook into IMAPClient parsing
                    # Good enough approach for now
                    if b"EXISTS" in data:
                        self.notifications.put(
                            IDLENotification(client_id, datetime.utcnow())
                        )

    @classmethod
    def _drain_socket(cls, sock) -> bytes:
        """Read and return all available data from the socket.

        It is always a good idea to empty kernel buffers from all data as
        leaving some can disable further notifications when epoll is in
        edge-triggered mode.
        """
        rv = bytes()

        while True:
            try:
                line = sock.recv(4096)
            except (ssl.SSLWantReadError, socket.timeout):
                # No more data to read
                break
            except OSError as e:
                if e.errno == errno.EAGAIN or e.errno == errno.EWOULDBLOCK:
                    # No more data to read
                    break
                raise
            else:
                if line == b'':
                    # The other end is closing the connection
                    raise ReceivedEOF("Read an empty byte-string")
                rv += line

        return rv

    def schedule_reactivations(self):
        logger.debug("Schedule reactivations thread started")
        while True:

            try:
                with self._lock:
                    item = self._idle_clients.first_item()
            except ValueError:
                timeout = IMAP_IDLE_MAX_AGE
            else:
                client_id, idle_client = item
                now = datetime.utcnow()
                if idle_client.deadline <= now:

                    delta = now - idle_client.deadline
                    if delta > timedelta(minutes=3):
                        logger.warning("Reactivation of client %s is late %s",
                                       client_id, delta)

                    try:
                        self._reactivate_client(client_id)
                    except Exception:
                        logger.exception("Error while reactivating client %s",
                                         client_id)
                    timeout = 0
                else:
                    timeout = (idle_client.deadline - now).total_seconds()

            logger.debug("Next reactivation in %s seconds", timeout)
            if self._should_stop.wait(timeout=timeout):
                break

        logger.debug("Schedule reactivations thread terminated")

    def _reactivate_client(self, client_id: str):
        """Reactivate a client for IMAP IDLE.

        The RFC states that IDLE clients should renew their command at least
        every 29 minutes. In practice 13 minutes is a good middle ground.
        This method removes a client, renews the IDLE command and re-adds the
        client back.

        To avoid a race condition wih ``has_client`` and the likes, this
        method places temporally the id of the removed client in the
        ``client_id_being_reactivated`` variable.
        """
        with self._lock:
            idle_client = self.remove_client(client_id)

            if not idle_client:
                logger.warning("Client to reactivate does not exist")
                return

            self._client_id_being_reactivated = idle_client.client_id

        try:
            response, status_updates = idle_client.imap_client.idle_done()
            logger.debug("Closed IDLE command for client %s, server said: %s",
                         idle_client.client_id, response)

            # Process pending status updates
            for status_update in status_updates:
                if status_update[1] == b'EXISTS':
                    self.notifications.put(
                        IDLENotification(idle_client.client_id,
                                         datetime.utcnow())
                    )
                    break

            idle_client.imap_client.idle()
        except Exception as e:
            self._close_idle_client(idle_client)
            logger.warning("Could not reactivate client %s: %s",
                           idle_client.client_id, e)
        else:
            self.add_client(idle_client.client_id,
                            idle_client.imap_client)
            logger.info("Renewed IDLE connection of client %s",
                        idle_client.client_id)
        finally:
            with self._lock:
                self._client_id_being_reactivated = None
