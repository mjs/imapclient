# Open a connection in IDLE mode and wait for notifications from the server

from imapclient import IMAPClient

HOST = 'imap.host.com'
USERNAME = 'someuser'
PASSWORD = 'password'

server = IMAPClient(HOST)
server.login(USERNAME, PASSWORD)
server.select_folder('INBOX')

# Start IDLE mode
server.idle()
print("Connection is now in IDLE mode, send yourself an email or quit with ^c")

while True:
    try:
        # Wait for up to 30 seconds for an IDLE response
        responses = server.idle_check(timeout=30)
        print("Server sent:", responses if responses else "nothing")
    except KeyboardInterrupt:
        break

server.idle_done()
print("\nIDLE mode done")
server.logout()
