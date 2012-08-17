from ConfigParser import SafeConfigParser, NoOptionError
import imapclient


def parse_config_file(path):
    """Parse INI files containing IMAP connection details.

    Used by livetest.py and interact.py
    """
    parser = SafeConfigParser(dict(
        username=None,
        password=None,
        ssl='false',
        stream='false',
        oauth='false',
        oauth_token=None,
        oauth_token_secret=None,
        oauth_url=None,
        ))
    fh = file(path)
    parser.readfp(fh)
    fh.close()
    section = 'main'
    assert parser.sections() == [section], 'Only expected a [main] section'

    try:
        port = parser.getint(section, 'port')
    except NoOptionError:
        port = None

    return Bunch(
        host=parser.get(section, 'host'),
        port=port,
        ssl=parser.getboolean(section, 'ssl'),
        stream=parser.getboolean(section, 'stream'),
        username=parser.get(section, 'username'),
        password=parser.get(section, 'password'),
        oauth=parser.getboolean(section, 'oauth'),
        oauth_url=parser.get(section, 'oauth_url'),
        oauth_token=parser.get(section, 'oauth_token'),
        oauth_token_secret=parser.get(section, 'oauth_token_secret'),
    )

def create_client_from_config(conf):
    client = imapclient.IMAPClient(conf.host, port=conf.port,
                                   ssl=conf.ssl, stream=conf.stream)
    if conf.oauth:
        client.oauth_login(conf.oauth_url,
                           conf.oauth_token,
                           conf.oauth_token_secret)
    elif not conf.stream:
        client.login(conf.username, conf.password)
    return client

class Bunch(dict):

    def __getattr__(self, k):
        try:
            return self[k]
        except KeyError:
            raise AttributeError

    def __setattr__(self, k, v):
        self[k] = v
