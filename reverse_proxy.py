#!/usr/bin/env python
import ssl
import socket

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http.client import HTTPConnection

from config import ADDR, PORT, DEFAULT_TIMEOUT, SERVER_NAME, HOST_MAP, HNF_REDIRECT, BUFSIZE, CERTFILE, KEYFILE


class ProxyHTTPRequestHandler(BaseHTTPRequestHandler):

    protocol_version = 'HTTP/1.1'

    handler_ids = []

    def __del__(self):
        if hasattr(self, '_id'):
            self.deallocate_id()
        if hasattr(self, 'proxy_client'):
            self.proxy_client.close()

    def allocate_id(self):
        lowest_available = 0
        ids = ProxyHTTPRequestHandler.handler_ids
        for _id in ids:
            if lowest_available != _id:
                break
            lowest_available += 1
        ProxyHTTPRequestHandler.handler_ids = sorted(ids + [lowest_available])
        self._id = lowest_available
        self.log_message(f"Created handler #{self._id} - no. handlers: {len(ids)+1}")

    def deallocate_id(self):
        ids = ProxyHTTPRequestHandler.handler_ids
        ids.remove(self._id)
        self.log_message(f"Destroyed handler #{self._id} - no. handlers {len(ids)}")

    def send_response(self, code, message=None):
        """Add the response header to the headers buffer and log the
        response code.

        Also send two standard headers with the server software
        version and the current date.

        """
        self.log_request(code)
        self.send_response_only(code, message)
        self.send_header('Server', SERVER_NAME)
        self.send_header('Date', self.date_time_string())

    def do_GET(self):
        self.handle_all()

    def do_POST(self):
        self.handle_all()

    def do_PUT(self):
        self.handle_all()

    def do_DELETE(self):
        self.handle_all()

    def host_not_found(self, host):
        self.log_message(f'host \'{host}\' not found in config')
        self.send_response(302, 'Found')
        self.send_header('Location', HNF_REDIRECT)
        self.send_header('Content-Length', '0')
        self.end_headers()

    def service_not_available(self):
        self.send_response(503, 'Service Unavailable')
        self.send_header('Content-Type', 'text/html')
        self.send_header('Content-Length', '32')
        self.end_headers()
        self.wfile.write(b'503 Service Unavailable')

    def buffered_rw(self, read_fn, write_fn, count):
        while count > BUFSIZE:
            buf = read_fn(BUFSIZE)
            write_fn(buf)
            count -= BUFSIZE
        if count > 0:
            buf = read_fn(count)
            write_fn(buf)

    def forward_request(self):
        content_len = 0
        self.proxy_client.putrequest(self.command, self.path, skip_host=True, skip_accept_encoding=True)
        for key, val in self.headers.items():
            if key.lower() == 'content-length':
                content_len = int(val)
            self.proxy_client.putheader(key, val)
        self.proxy_client.endheaders()
        self.buffered_rw(self.rfile.read, self.proxy_client.send, content_len)
        return self.proxy_client.getresponse()

    def return_response(self, resp):
        self.send_response(resp.getcode())
        resp_headers = resp.getheaders()
        content_len = 0
        for key, val in resp_headers:
            if key.lower() == 'date' or key.lower() == 'server':
                # these are already sent by self.send_response()
                continue
            if key.lower() == 'content-length':
                content_len = int(val)
            self.send_header(key, val)
        self.end_headers()
        self.buffered_rw(resp.read, self.wfile.write, content_len)
        resp.close()

    def handle_all(self):
        if 'Host' not in self.headers:
            self.send_error(400, None, 'Missing "Host" header')
            return

        if self.headers['Host'] not in HOST_MAP:
            self.host_not_found(self.headers['Host'])
            return

        if not hasattr(self, 'proxy_client'):
            self.allocate_id()
            host_info = HOST_MAP[self.headers['Host']]
            self.proxy_client = HTTPConnection(*host_info)
            try:
                self.proxy_client.connect()
            except ConnectionRefusedError:
                self.service_not_available()
                return

        try: 
            resp = self.forward_request()
        except ConnectionRefusedError:
            self.service_not_available()
            return

        self.return_response(resp)


if __name__ == '__main__':
    # prevent getting stuck on ssl handshake
    socket.setdefaulttimeout(DEFAULT_TIMEOUT)

    server_address = (ADDR, PORT)

    if KEYFILE and CERTFILE:
        httpd = ThreadingHTTPServer(server_address, ProxyHTTPRequestHandler)
        httpd.socket = ssl.wrap_socket(
                               httpd.socket,
                               server_side=True,
                               keyfile=KEYFILE,
                               certfile=CERTFILE,
                               ssl_version=ssl.PROTOCOL_TLS
        )
    else:
        httpd = ThreadingHTTPServer(server_address, ProxyHTTPRequestHandler)

    print(f"proxy server running on port {server_address[1]}")    

    httpd.serve_forever()

