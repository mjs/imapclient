# Download unread emails and parse them into standard EmailMessage objects
import email

from imapclient import IMAPClient

HOST = "imap.host.com"
USERNAME = "someuser"
PASSWORD = "secret"

with IMAPClient(HOST) as server:
    server.login(USERNAME, PASSWORD)
    server.select_folder("INBOX", readonly=True)

    messages = server.search("UNSEEN")
    for uid, message_data in server.fetch(messages, "RFC822").items():
        email_message = email.message_from_bytes(message_data[b"RFC822"])
        print(uid, email_message.get("From"), email_message.get("Subject"))
