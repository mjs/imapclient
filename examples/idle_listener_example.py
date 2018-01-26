# Open a connection in IDLE mode to multiple clients and wait asynchronously
# for notifications from the server

import logging

from imapclient import IMAPClient
from imapclient.extras.idle_listener import IDLEListener

HOST = 'imap.host.com'
USERNAME = 'someuser'
PASSWORD = 'password'

def main():
    logging.basicConfig(level=logging.DEBUG)

    # Open a connection and put it in IDLE mode
    server = IMAPClient(HOST)
    server.login(USERNAME, PASSWORD)
    server.select_folder('INBOX')
    server.idle()

    with IDLEListener() as il:

        # Add the client to IDLEListener
        # For the example we have a single client, but in reality it
        # only makes sense with many of them.
        il.add_client("client 1", server)

        while True:
            try:
                notification = il.notifications.get()
                logging.info("Received a notification from %s",
                             notification.client_id)
            except KeyboardInterrupt:
                break


if __name__ == '__main__':
    main()
