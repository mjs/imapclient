from pprint import pprint
from imapclient import IMAPClient

i = IMAPClient('localhost')
i.login('mailtest', 'foobar')
i.select_folder('INBOX')
msgs = i.search()
print msgs
pprint(i.altfetch(msgs[0], 'RFC822'))
