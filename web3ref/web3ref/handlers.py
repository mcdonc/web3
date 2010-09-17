"""Base classes for server/gateway implementations"""

import locale
import os
import sys
import time
from traceback import print_exception

from web3ref.util import guess_scheme
from web3ref.util import is_hop_by_hop
from web3ref.util import CRLF

__all__ = ['BaseHandler', 'SimpleHandler', 'BaseCGIHandler', 'CGIHandler']

# Weekday and month names for HTTP date/time formatting; always English!
_weekdayname = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_monthname = [None, # Dummy so we can use 1-based month numbers
              "Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

def format_date_time(timestamp):
    year, month, day, hh, mm, ss, wd, y, z = time.gmtime(timestamp)
    date = "%s, %02d %3s %4d %02d:%02d:%02d GMT" % (
        _weekdayname[wd], day, _monthname[month], year, hh, mm, ss
    )
    try:
        return bytes(date, 'ascii')
    except TypeError:
        # Python 2
        return date

def get_environ():
    d = {}
    for k, v in os.environ.items():
        # Python 3 compatibility
        if not isinstance(v, bytes):
            # We must explicitly encode the string to bytes under 
            # Python 3.1+
            encoding = locale.getpreferredencoding()
            v = v.encode(encoding, 'surrogateescape')
        d[k] = v
    return d

class BaseHandler:
    """Manage the invocation of a WEB3 application"""

    # Configuration parameters; can override per-subclass or per-instance
    web3_version = (1,0)
    web3_multithread = True
    web3_multiprocess = True
    web3_run_once = False
    web3_async = False

    origin_server = True    # We are transmitting direct to client
    http_version  = b"1.0"   # Version that should be used for response
    server_software = None  # String name of server software, if any

    # os_environ is used to supply configuration from the OS environment:
    # by default it's a copy of 'os.environ' as of import time, but you can
    # override this in e.g. your __init__ method.
    os_environ = get_environ()

    # Error handling (also per-subclass or per-instance)
    traceback_limit = None  # Print entire traceback to self.get_stderr()
    error_status = b"500 Dude, this is whack!"
    error_headers = [(b'Content-Type', b'text/plain')]
    error_body = [b"A server error occurred. Contact the administrator."]

    # State variables (don't mess with these)
    status = result = body = headers = None
    
    headers_sent = False
    headers = None
    bytes_sent = 0

    def run(self, application):
        """Invoke the application"""
        try:
            self.setup_environ()
            self.result = application(self.environ)
            self.finish_response()
        except:
            try:
                self.handle_error()
            except:
                # If we get an error handling an error, just give up already!
                self.close()
                raise   # ...and let the actual server figure it out.

    def setup_environ(self):
        """Set up the environment for one request"""

        env = self.environ = self.os_environ.copy()
        self.add_cgi_vars()

        env['web3.version']      = self.web3_version
        env['web3.url_scheme']   = self.get_scheme()
        env['web3.input']        = self.get_stdin()
        env['web3.errors']       = self.get_stderr()
        env['web3.multithread']  = self.web3_multithread
        env['web3.run_once']     = self.web3_run_once
        env['web3.multiprocess'] = self.web3_multiprocess
        if 'RAW_PATH_INFO' in env:
            env['web3.path_info']    = env['RAW_PATH_INFO']
        env['web3.script_name']  = env['SCRIPT_NAME']
        env['web3.async']        = self.web3_async

        if self.origin_server and self.server_software:
            env.setdefault('SERVER_SOFTWARE', self.server_software)

    def finish_response(self):
        """Send any iterable data, then close self and the iterable

        Subclasses intended for use in asynchronous servers will
        want to redefine this method, such that it sets up callbacks
        in the event loop to iterate over the data, and to call
        'self.close()' once the response is finished.
        """
        if hasattr(self.result, '__call__'):
            raise AssertionError('This server does not support asynchronous '
                                 'responses')

        status, headers, body = self.result

        if not isinstance(status, bytes):
            raise AssertionError(
                "Status must be bytes: %r" % status)
        if not len(status)>=4:
            raise AssertionError(
                "Status must be at least 4 characters: %r" % status)
        if not int(status[:3]):
            raise AssertionError(
                "Status message must begin w/3-digit code: %r" % status)
        if not status[3:4]==b" ":
            import pdb; pdb.set_trace()
            raise AssertionError(
                "Status message must have a space after code: %r" % status)

        for name, val in headers:
            if not isinstance(name, bytes):
                raise AssertionError(
                    "Header names must be bytes: %r" % name)
            if not isinstance(val, bytes):
                raise AssertionError(
                    "Header values must be bytes: %r" % val)
            if is_hop_by_hop(name):
                raise AssertionError(
                    "Hop-by-hop headers not allowed: %r" % name)

        self.status = status
        self.headers = headers
        self.body = body

        self.send_headers()

        for data in body:
            self.write(data)

        self.close()

    def get_scheme(self):
        """Return the URL scheme being used"""
        return guess_scheme(self.environ)

    def has_header(self, name):
        for k, v in self.headers:
            if k.lower() == name.lower():
                return True
        return False

    def send_preamble(self):
        """Transmit version/status/date/server, via self._write()"""
        if self.origin_server:
            if self.client_is_modern():
                self._write(
                    b'HTTP/' + self.http_version + b' ' + self.status + CRLF)
                if not self.has_header(b'Date'):
                    self._write(
                        b'Date: ' + format_date_time(time.time()) + CRLF
                    )
                if self.server_software and not self.has_header(b'Server'):
                    self._write(b'Server: ' + self.server_software + CRLF)
        else:
            self._write(b'Status: ' + self.status + CRLF)

    def write(self, data):

        if not self.status:
            raise AssertionError("write() before status set")

        elif not self.headers_sent:
            raise AssertionError("write() before headers set")
        
        self.bytes_sent += len(data)

        self._write(data)
        self._flush()

    def close(self):
        """Close the iterable (if needed) and reset all instance vars

        Subclasses may want to also drop the client connection.
        """
        try:
            if hasattr(self.body, 'close'):
                self.body.close()
        finally:
            self.result=self.body=self.headers=self.status=self.environ = None
            self.bytes_sent = 0; self.headers_sent = False

    def send_headers(self):
        """Transmit headers to the client, via self._write()"""
        self.headers_sent = True
        if not self.origin_server or self.client_is_modern():
            self.send_preamble()
            for k, v in self.headers:
                self._write(k + b': ' + v + CRLF)
            self._write(CRLF)

    def client_is_modern(self):
        """True if client can accept status and headers"""
        return self.environ['SERVER_PROTOCOL'].upper() != b'HTTP/0.9'

    def log_exception(self,exc_info):
        """Log the 'exc_info' tuple in the server log

        Subclasses may override to retarget the output or change its format.
        """
        try:
            stderr = self.get_stderr()
            print_exception(
                exc_info[0], exc_info[1], exc_info[2],
                self.traceback_limit, stderr
            )
            stderr.flush()
        finally:
            exc_info = None

    def handle_error(self):
        """Log current error, and send error output to client if possible"""
        self.log_exception(sys.exc_info())
        if not self.headers_sent:
            self.result = self.error_output(self.environ)
            self.finish_response()

    def error_output(self, environ):
        """WEB3 mini-app to create error output

        By default, this just uses the 'error_status', 'error_headers',
        and 'error_body' attributes to generate an output page.  It can
        be overridden in a subclass to dynamically generate diagnostics,
        choose an appropriate message for the user's preferred language, etc.

        Note, however, that it's not recommended from a security perspective to
        spit out diagnostics to any old user; ideally, you should have to do
        something special to enable diagnostic output, which is why we don't
        include any here!
        """
        return (self.error_status, self.error_headers, self.error_body)

    # Pure abstract methods; *must* be overridden in subclasses

    def _write(self,data):
        """Override in subclass to buffer data for send to client

        It's okay if this method actually transmits the data; BaseHandler
        just separates write and flush operations for greater efficiency
        when the underlying system actually has such a distinction.
        """
        raise NotImplementedError

    def _flush(self):
        """Override in subclass to force sending of recent '_write()' calls

        It's okay if this method is a no-op (i.e., if '_write()' actually
        sends the data.
        """
        raise NotImplementedError

    def get_stdin(self):
        """Override in subclass to return suitable 'web3.input'"""
        raise NotImplementedError

    def get_stderr(self):
        """Override in subclass to return suitable 'web3.errors'"""
        raise NotImplementedError

    def add_cgi_vars(self):
        """Override in subclass to insert CGI variables in 'self.environ'"""
        raise NotImplementedError

class SimpleHandler(BaseHandler):
    """Handler that's just initialized with streams, environment, etc.

    This handler subclass is intended for synchronous HTTP/1.0 origin servers,
    and handles sending the entire response output, given the correct inputs.

    Usage::

        handler = SimpleHandler(
            inp,out,err,env, multithread=False, multiprocess=True
        )
        handler.run(app)"""

    def __init__(self, stdin, stdout, stderr, environ, multithread=True,
                 multiprocess=False):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.base_env = environ
        self.web3_multithread = multithread
        self.web3_multiprocess = multiprocess

    def get_stdin(self):
        return self.stdin

    def get_stderr(self):
        return self.stderr

    def add_cgi_vars(self):
        self.environ.update(self.base_env)

    def _write(self,data):
        self.stdout.write(data)
        self._write = self.stdout.write

    def _flush(self):
        self.stdout.flush()
        self._flush = self.stdout.flush


class BaseCGIHandler(SimpleHandler):

    """CGI-like systems using input/output/error streams and environ mapping

    Usage::

        handler = BaseCGIHandler(inp,out,err,env)
        handler.run(app)

    This handler class is useful for gateway protocols like ReadyExec and
    FastCGI, that have usable input/output/error streams and an environment
    mapping.  It's also the base class for CGIHandler, which just uses
    sys.stdin, os.environ, and so on.

    The constructor also takes keyword arguments 'multithread' and
    'multiprocess' (defaulting to 'True' and 'False' respectively) to control
    the configuration sent to the application.  It sets 'origin_server' to
    False (to enable CGI-like output), and assumes that 'web3.run_once' is
    False.
    """

    origin_server = False


class CGIHandler(BaseCGIHandler):

    """CGI-based invocation via sys.stdin/stdout/stderr and os.environ

    Usage::

        CGIHandler().run(app)

    The difference between this class and BaseCGIHandler is that it always
    uses 'web3.run_once' of 'True', 'web3.multithread' of 'False', and
    'web3.multiprocess' of 'True'.  It does not take any initialization
    parameters, but always uses 'sys.stdin', 'os.environ', and friends.

    If you need to override any of these parameters, use BaseCGIHandler
    instead.
    """

    web3_run_once = True

    def __init__(self):
        BaseCGIHandler.__init__(
            self, sys.stdin, sys.stdout, sys.stderr, get_environ(),
            multithread=False, multiprocess=True
        )
