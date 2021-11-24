from datetime import datetime, timedelta
from selectors import DefaultSelector, EVENT_READ

from imapclient import IMAPClient

HOST = "localhost"
USERNAME = "user"
PASSWORD = "Tr0ub4dor&3"
RESPONSE_TIMEOUT_SECONDS = 15
IDLE_SECONDS = 60 * 24

with IMAPClient(HOST, timeout=RESPONSE_TIMEOUT_SECONDS) as server:
    server.login(USERNAME, PASSWORD)
    server.select_folder("INBOX", readonly=True)
    server.idle()
    print(
        "Connection is now in IDLE mode,"
        " send yourself an email or quit with ^c"
    )
    try:
        with DefaultSelector() as selector:
            selector.register(server.socket(), EVENT_READ, None)
            now = datetime.now
            end_at = now() + timedelta(seconds=IDLE_SECONDS)
            while selector.select((end_at - now()).total_seconds()):
                responses = server.idle_check(timeout=0)
                if not responses:
                    raise ConnectionError(
                        "Socket readable without data. Likely closed."
                    )
                print("Server sent:", responses)
        print("IDLE time out.")
    except KeyboardInterrupt:
        print("")  # Newline after the typically echoed ^C.
    server.idle_done()
    print("IDLE mode done")
