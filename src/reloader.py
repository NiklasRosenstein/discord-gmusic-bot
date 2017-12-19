
import os
import socket
import socketserver
import subprocess


class ReloaderRequestHandler(socketserver.BaseRequestHandler):

  def __init__(self, reloader, *args, **kwargs):
    self.reloader = reloader
    super().__init__(*args, **kwargs)

  def handle(self):
    data = self.request.recv(7)
    if data == b'reload\n':
      self.reloader.reload()
    else:
      logging.warn('Reloader: Unexpected data received.')
      self.request.close()


class Reloader:

  def __init__(self, envvar='RELOADER_TCP_PORT'):
    self.server = None
    self._process = None
    self.envvar = envvar

  def is_inner(self):
    return os.getenv(self.envvar, '') != ''

  def send_reload(self):
    assert self.is_inner()
    port = int(os.getenv(self.envvar))
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('localhost', port))
    sock.send(b'reload\n')
    sock.close()

  def reload(self):
    assert not self.is_inner()
    if self._process:
      self._process.terminate()
      self._process.wait()
    env = os.environ.copy()
    env[self.envvar] = str(self.server.socket.getsockname()[1])
    self._process = subprocess.Popen(self._reload_args, env=env)

  def request_handler(self, *args, **kwargs):
    return ReloaderRequestHandler(self, *args, **kwargs)

  def run_forever(self, reload_args):
    self.server = socketserver.TCPServer(('localhost', 0), self.request_handler)
    self.server.timeout = 1.0
    self._reload_args = reload_args
    self.reload()
    try:
      while self._process.poll() is None:
        self.server.handle_request()
    finally:
      self._process.terminate()
      self._process.wait()


module.exports = Reloader
