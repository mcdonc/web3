"""Miscellaneous Web3-related Utilities"""

import posixpath

__all__ = [
    'guess_scheme', 'application_uri', 'request_uri',
    'shift_path_info', 'setup_testing_defaults', 'CRLF'
]

CRLF = b'\r\n'

def guess_scheme(environ):
    """Return a guess for whether 'wsgi.url_scheme' should be 'http' or 'https'
    """
    if environ.get("HTTPS") in (b'yes', b'on', b'1'):
        return b'https'
    else:
        return b'http'

def application_uri(environ):
    """Return the application's base URI (no PATH_INFO or QUERY_STRING)"""
    url = environ['wsgi.url_scheme']+b'://'
    from urllib import quote

    if environ.get('HTTP_HOST'):
        url += environ['HTTP_HOST']
    else:
        url += environ['SERVER_NAME']

        if environ['wsgi.url_scheme'] == b'https':
            if environ['SERVER_PORT'] != b'443':
                url += ':' + environ['SERVER_PORT']
        else:
            if environ['SERVER_PORT'] != b'80':
                url += ':' + environ['SERVER_PORT']

    url += quote(environ.get('SCRIPT_NAME') or b'/')
    return url

def request_uri(environ, include_query=1):
    """Return the full request URI, optionally including the query string"""
    url = application_uri(environ)
    from urllib import quote
    path_info = quote(environ.get('PATH_INFO', b''))
    if not environ.get('SCRIPT_NAME'):
        url += path_info[1:]
    else:
        url += path_info
    if include_query and environ.get('QUERY_STRING'):
        url += b'?' + environ['QUERY_STRING']
    return url

def shift_path_info(environ):
    """Shift a name from PATH_INFO to SCRIPT_NAME, returning it

    If there are no remaining path segments in PATH_INFO, return None.
    Note: 'environ' is modified in-place; use a copy if you need to keep
    the original PATH_INFO or SCRIPT_NAME.

    Note: when PATH_INFO is just a '/', this returns '' and appends a trailing
    '/' to SCRIPT_NAME, even though empty path segments are normally ignored,
    and SCRIPT_NAME doesn't normally end in a '/'.  This is intentional
    behavior, to ensure that an application can tell the difference between
    '/x' and '/x/' when traversing to objects.
    """
    path_info = environ.get('PATH_INFO', b'')
    if not path_info:
        return None

    path_parts = path_info.split(b'/')
    path_parts[1:-1] = [p for p in path_parts[1:-1] if p and p!=b'.']
    name = path_parts[1]
    del path_parts[1]

    script_name = environ.get('SCRIPT_NAME', b'')
    script_name = posixpath.normpath(script_name+b'/'+name)
    if script_name.endswith(b'/'):
        script_name = script_name[:-1]
    if not name and not script_name.endswith(b'/'):
        script_name += b'/'

    environ['SCRIPT_NAME'] = script_name
    environ['PATH_INFO']   = b'/'.join(path_parts)

    # Special case: '/.' on PATH_INFO doesn't get stripped,
    # because we don't strip the last element of PATH_INFO
    # if there's only one path part left.  Instead of fixing this
    # above, we fix it here so that PATH_INFO gets normalized to
    # an empty string in the environ.
    if name == b'.':
        name = None
    return name

def setup_testing_defaults(environ):
    """Update 'environ' with trivial defaults for testing purposes

    This adds various parameters required for WSGI, including HTTP_HOST,
    SERVER_NAME, SERVER_PORT, REQUEST_METHOD, SCRIPT_NAME, PATH_INFO,
    and all of the wsgi.* variables.  It only supplies default values,
    and does not replace any existing settings for these variables.

    This routine is intended to make it easier for unit tests of WSGI
    servers and applications to set up dummy environments.  It should *not*
    be used by actual WSGI servers or applications, since the data is fake!
    """

    environ.setdefault('SERVER_NAME', b'127.0.0.1')
    environ.setdefault('SERVER_PROTOCOL', b'HTTP/1.0')

    environ.setdefault('HTTP_HOST', environ['SERVER_NAME'])
    environ.setdefault('REQUEST_METHOD', b'GET')

    if 'SCRIPT_NAME' not in environ and 'PATH_INFO' not in environ:
        environ.setdefault('SCRIPT_NAME', b'')
        environ.setdefault('PATH_INFO', b'/')

    environ.setdefault('web3.version', (1,0))
    environ.setdefault('web3.run_once', 0)
    environ.setdefault('web3.multithread', 0)
    environ.setdefault('web3.multiprocess', 0)

    from StringIO import StringIO
    environ.setdefault('web3.input', StringIO(""))
    environ.setdefault('web3.errors', StringIO())
    environ.setdefault('web3.url_scheme',guess_scheme(environ))

    if environ['wsgi.url_scheme'] == b'http':
        environ.setdefault('SERVER_PORT', b'80')
    elif environ['wsgi.url_scheme']==b'https':
        environ.setdefault('SERVER_PORT', b'443')

_hoppish = {
    'connection':1, 'keep-alive':1, 'proxy-authenticate':1,
    'proxy-authorization':1, 'te':1, 'trailers':1, 'transfer-encoding':1,
    'upgrade':1
    }

def is_hop_by_hop(header_name):
    """Return true if 'header_name' is an HTTP/1.1 "Hop-by-Hop" header"""
    return header_name.lower() in _hoppish

def to_bytes(data):
    return str(data).encode('ascii')


























#
