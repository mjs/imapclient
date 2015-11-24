# Copyright (c) 2015, Menno Smits
# Released subject to the New BSD License
# Please see http://en.wikipedia.org/wiki/BSD_licenses

from __future__ import unicode_literals

# TODO: can't six do this for us?
try:
    from ConfigParser import SafeConfigParser, NoOptionError
except ImportError:
    from configparser import SafeConfigParser, NoOptionError

from os import path
from backports import ssl

from six import iteritems
from six.moves.urllib.request import urlopen
from six.moves.urllib.parse import urlencode

import imapclient
from .tls import create_default_context

try:
    import json
except ImportError:
    json = None

def get_config_defaults():
    return dict(
        username=None,
        password=None,
        ssl=False,
        ssl_check_hostname=True,
        ssl_verify_cert=True,
        ssl_ca_file=None,
        timeout=None,
        starttls=False,
        stream=False,
        oauth=False,
        oauth_token=None,
        oauth_token_secret=None,
        oauth_url=None,
        oauth2=False,
        oauth2_client_id=None,
        oauth2_client_secret=None,
        oauth2_refresh_token=None,
        expect_failure=None,
    )


def parse_config_file(filename):
    """Parse INI files containing IMAP connection details.

    Used by livetest.py and interact.py
    """

    parser = SafeConfigParser(get_string_config_defaults())
    with open(filename, 'r') as fh:
        parser.readfp(fh)

    conf = _read_config_section(parser, "DEFAULT")
    if conf.expect_failure:
        raise ValueError("expect_failure should not be set for the DEFAULT section")

    conf.alternates = {}
    for section in parser.sections():
        conf.alternates[section] = _read_config_section(parser, section)

    return conf


def get_string_config_defaults():
    out = {}
    for k, v in iteritems(get_config_defaults()):
        if v is True:
            v = 'true'
        elif v is False:
            v = 'false'
        out[k] = v
    return out


def _read_config_section(parser, section):
    get = lambda name: parser.get(section, name)
    getboolean = lambda name: parser.getboolean(section, name)

    def get_allowing_none(name, typefunc):
        try:
            v = parser.get(section, name)
        except NoOptionError:
            return None
        if not v:
            return None
        return typefunc(v)

    def getint(name):
        return get_allowing_none(name, int)

    def getfloat(name):
        return get_allowing_none(name, float)

    ssl_ca_file = get('ssl_ca_file')
    if ssl_ca_file:
        ssl_ca_file = path.expanduser(ssl_ca_file)

    return Bunch(
        host=get('host'),
        port=getint('port'),
        ssl=getboolean('ssl'),
        starttls=getboolean('starttls'),
        ssl_check_hostname=getboolean('ssl_check_hostname'),
        ssl_verify_cert=getboolean('ssl_verify_cert'),
        ssl_ca_file=ssl_ca_file,
        timeout=getfloat('timeout'),

        stream=getboolean('stream'),

        username=get('username'),
        password=get('password'),

        oauth=getboolean('oauth'),
        oauth_url=get('oauth_url'),
        oauth_token=get('oauth_token'),
        oauth_token_secret=get('oauth_token_secret'),

        oauth2=getboolean('oauth2'),
        oauth2_client_id=get('oauth2_client_id'),
        oauth2_client_secret=get('oauth2_client_secret'),
        oauth2_refresh_token=get('oauth2_refresh_token'),

        expect_failure=get('expect_failure')
    )

OAUTH2_REFRESH_URLS = {
    'imap.gmail.com': 'https://accounts.google.com/o/oauth2/token',
    'imap.mail.yahoo.com': "https://api.login.yahoo.com/oauth2/get_token",
}

def refresh_oauth2_token(hostname, client_id, client_secret, refresh_token):
    if not json:
        raise RuntimeError("OAUTH2 functionality relies on 'json' module")

    url = OAUTH2_REFRESH_URLS.get(hostname)
    if not url:
        raise ValueError("don't know where to refresh OAUTH2 token for %r" % hostname)

    post = dict(client_id=client_id.encode('ascii'),
                client_secret=client_secret.encode('ascii'),
                refresh_token=refresh_token.encode('ascii'),
                grant_type=b'refresh_token')
    response = urlopen(url, urlencode(post).encode('ascii')).read()
    return json.loads(response.decode('ascii'))['access_token']

# Tokens are expensive to refresh so use the same one for the duration of the process.
_oauth2_cache = {}

def get_oauth2_token(hostname, client_id, client_secret, refresh_token):
    cache_key = (hostname, client_id, client_secret, refresh_token)
    token = _oauth2_cache.get(cache_key)
    if token:
        return token

    token = refresh_oauth2_token(hostname, client_id, client_secret, refresh_token)
    _oauth2_cache[cache_key] = token
    return token

def create_client_from_config(conf):
    ssl_context = None
    if conf.ssl:
        ssl_context = create_default_context()
        ssl_context.check_hostname = conf.ssl_check_hostname
        if not conf.ssl_verify_cert:
            ssl_context.verify_mode = ssl.CERT_NONE
        if conf.ssl_ca_file:
            ssl_context.load_verify_locations(cafile=conf.ssl_ca_file)

    client = imapclient.IMAPClient(conf.host, port=conf.port,
                                   ssl=conf.ssl,
                                   ssl_context=ssl_context,
                                   stream=conf.stream,
                                   timeout=conf.timeout)
    try:
        if conf.starttls:
            client.starttls()

        if conf.oauth:
            client.oauth_login(conf.oauth_url,
                               conf.oauth_token,
                               conf.oauth_token_secret)
        elif conf.oauth2:
            access_token = get_oauth2_token(conf.host,
                                            conf.oauth2_client_id,
                                            conf.oauth2_client_secret,
                                            conf.oauth2_refresh_token)
            client.oauth2_login(conf.username, access_token)

        elif not conf.stream:
            client.login(conf.username, conf.password)
        return client
    except:
        client.shutdown()
        raise


class Bunch(dict):

    def __getattr__(self, k):
        try:
            return self[k]
        except KeyError:
            raise AttributeError

    def __setattr__(self, k, v):
        self[k] = v
