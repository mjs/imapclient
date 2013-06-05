from __future__ import unicode_literals

try:
    from ConfigParser import SafeConfigParser, NoOptionError
except ImportError:
    from configparser import SafeConfigParser, NoOptionError

import imapclient
import urllib

try:
    import json
except ImportError:
    json = None


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
        oauth2='false',
        oauth2_client_id=None,
        oauth2_client_secret=None,
        oauth2_refresh_token=None,
        ))
    with open(path, 'r') as fh:
        parser.readfp(fh)
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

        oauth2=parser.getboolean(section, 'oauth2'),
        oauth2_client_id=parser.get(section, 'oauth2_client_id'),
        oauth2_client_secret=parser.get(section, 'oauth2_client_secret'),
        oauth2_refresh_token=parser.get(section, 'oauth2_refresh_token'),
    )

def refresh_oauth2_token(client_id, client_secret, refresh_token):
    if not json:
        raise RuntimeError("livetest OAUTH2 functionality relies on 'json' module")
    post = dict(client_id=client_id,
                client_secret=client_secret,
                refresh_token=refresh_token,
                grant_type='refresh_token')
    response = urllib.urlopen('https://accounts.google.com/o/oauth2/token',
                              urllib.urlencode(post)).read()
    return json.loads(response)['access_token']

# Tokens are expensive to refresh so use the same one for the duration of the process.
_oauth2_cache = {}
def get_oauth2_token(client_id, client_secret, refresh_token):
    cache_key = (client_id, client_secret, refresh_token)
    token = _oauth2_cache.get(cache_key)
    if token:
        return token
    token = refresh_oauth2_token(client_id, client_secret, refresh_token)
    _oauth2_cache[cache_key] = token
    return token

def create_client_from_config(conf):
    client = imapclient.IMAPClient(conf.host, port=conf.port,
                                   ssl=conf.ssl, stream=conf.stream)
    if conf.oauth:
        client.oauth_login(conf.oauth_url,
                           conf.oauth_token,
                           conf.oauth_token_secret)
    elif conf.oauth2:
        access_token = get_oauth2_token(conf.oauth2_client_id,
                                        conf.oauth2_client_secret,
                                        conf.oauth2_refresh_token)
        client.oauth2_login(conf.username, access_token)

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
