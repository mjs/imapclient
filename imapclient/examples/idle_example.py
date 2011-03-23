from imapclient import IMAPClient
import time

HOST = 'imap.host.com'
USERNAME = 'someuser'
PASSWORD = 'password'
ssl = True

server = IMAPClient(HOST, use_uid=True, ssl=ssl)

server.login(USERNAME, PASSWORD)

select_info = server.select_folder('INBOX')
print select_info
print

idling = True

def callback(resp, arg):
    global idling
    
    print "Something happened, or timeout was reached"
    print
    print "Callback response:"
    print resp
    print
    print "The callback function received arg: ", arg
    print
    idling = False

server.idle(timeout=5, callback=callback, cb_arg="Hello future self!")
print "Began idling"

while idling:
    print "..still idling.."
    time.sleep(1)
    
print server.logout()