"""BaseHTTPServer that implements the Web3 protocol.

This is an example of how Web3 can be implemented, using tools present
only in the Python standard library.

For example usage, see the ``if __name__=="__main__"`` block at the end of the
module.  See also the BaseHTTPServer module docs for other API information.
"""

import sys
import urllib

from BaseHTTPServer import BaseHTTPRequestHandler
from BaseHTTPServer import HTTPServer
from web3ref.handlers import SimpleHandler
from web3ref.util import to_bytes

__version__ = "0.0"
__all__ = ['Web3Server', 'Web3RequestHandler', 'demo_app', 'make_server']

server_version = "Web3Server/" + __version__
sys_version = "Python/" + sys.version.split()[0]
software_version = server_version + ' ' + sys_version

class Web3Server(HTTPServer):
    """BaseHTTPServer that implements the Web3 protocol"""

    application = None

    def server_bind(self):
        """Override server_bind to store the server name."""
        HTTPServer.server_bind(self)
        self.setup_environ()

    def setup_environ(self):
        # Set up base environment
        env = self.base_environ = {}
        env['SERVER_NAME'] = to_bytes(self.server_name)
        env['GATEWAY_INTERFACE'] = b'CGI/1.1'
        env['SERVER_PORT'] = to_bytes(str(self.server_port))
        env['REMOTE_HOST'] = b''
        env['CONTENT_LENGTH'] = b''
        env['SCRIPT_NAME'] = b''

    def get_app(self):
        return self.application

    def set_app(self,application):
        self.application = application

class Web3RequestHandler(BaseHTTPRequestHandler):

    server_version = "Web3Server/" + __version__

    def get_environ(self):
        env = self.server.base_environ.copy()
        env['SERVER_PROTOCOL'] = to_bytes(self.request_version)
        env['REQUEST_METHOD'] = to_bytes(self.command)
        if '?' in self.path:
            path, query = self.path.split('?', 1)
        else:
            path, query = self.path, ''

        env['PATH_INFO'] = to_bytes(urllib.unquote(path))
        env['QUERY_STRING'] = to_bytes(query)

        host = self.address_string()
        if host != self.client_address[0]:
            env['REMOTE_HOST'] = to_bytes(host)
        env['REMOTE_ADDR'] = to_bytes(self.client_address[0])

        typeheader = self.headers.get('content-type')

        if typeheader is None:
            env['CONTENT_TYPE'] = b'text/plain'
        else:
            env['CONTENT_TYPE'] = to_bytes(typeheader)

        length = self.headers.get('content-length')
        if length:
            env['CONTENT_LENGTH'] = to_bytes(length)

        headers = self.headers.items()

        for k, v in headers:
            k = k.replace('-','_').upper()
            v = v.strip()
            if k in env:
                continue                    # skip content length, type,etc.
            if 'HTTP_'+k in env:
                env['HTTP_'+k] += b','+ to_bytes(v) # comma-separate multiples
            else:
                env['HTTP_'+k] = to_bytes(v)
        return env

    def get_stderr(self):
        return sys.stderr

    def handle(self):
        """Handle a single HTTP request"""
        self.raw_requestline = self.rfile.readline()
        if not self.parse_request(): # An error code has been sent, just exit
            return

        handler = SimpleHandler(
            self.rfile, self.wfile, self.get_stderr(), self.get_environ()
        )
        handler.request_handler = self      # backpointer for logging
        handler.run(self.server.get_app())

def demo_app(environ):
    result = b'Hello world!'
    headers = [
        (b'Content-Length', to_bytes(len(result))),
        (b'Content-Type', b'text/plain'),
        ]
    return (b'200 OK', headers, [result])

def make_server(
    host,
    port,
    app,
    server_class=Web3Server,
    handler_class=Web3RequestHandler
    ):
    """Create a new WSGI server listening on `host` and `port` for `app`"""
    server = server_class((host, port), handler_class)
    server.set_app(app)
    return server

if __name__ == '__main__':
    httpd = make_server('', 8000, demo_app)
    sa = httpd.socket.getsockname()
    print "Serving HTTP on", sa[0], "port", sa[1], "..."
    import webbrowser
    webbrowser.open('http://localhost:8000/xyz?abc')
    httpd.handle_request()  # serve one request, then exit
