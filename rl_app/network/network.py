import socket
from rl_app.network.serializer import get_serializer, get_deserializer, int_from_bytes, int_to_bytes
import time
from threading import Thread


class Receiver:

  def __init__(self,
               host=None,
               port=None,
               bind=True,
               serializer='pyarrow',
               deserializer='pyarrow'):
    self._thread = None
    self.host = host
    self.port = port
    self._serializer = get_serializer(serializer)
    self._deserializer = get_deserializer(deserializer)
    self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    self.bind = bind
    self.connected = False
    if bind:
      self.socket.bind((host, port))
    else:
      # if server has not called listen yet. Keep retrying
      while True:
        try:
          self.socket.connect((host, port))
          self.connected = True
          print('Connected to %s:%d' % (host, port))
          break
        except ConnectionError:
          time.sleep(.2)
          print('connect to %s:%d failed. Retrying in 200ms' % (host, port))

  def start_loop(self, handler, new_connection_callback=None, blocking=False):
    """
      Args:
          handler: function that takes an incoming client message
              (deserialized)
          blocking: True to block the main program
              False to launch a thread in the background
              and immediately returns
      Returns:
          if non-blocking, returns the created thread that has started
      """
    if blocking:
      self._start(handler, new_connection_callback)
    else:
      if self._thread:
        raise RuntimeError('loop is already running')
      self._thread = Thread(target=self._start,
                            args=[handler, new_connection_callback])
      self._thread.daemon = True
      self._thread.start()
      return self._thread

  def _start(self, handler, new_connection_callback):
    try:
      if self.bind:
        self.socket.listen(1)
        print('server %s:%d waiting to accept new connections' %
              (self.host, self.port))
        conn, addr = self.socket.accept()
        self.connected = True
        if new_connection_callback:
          new_connection_callback(conn, addr)
        print('Connection accepted to client ', addr)
        with conn:
          self._loop(conn, handler)
      else:
        self._loop(self.socket, handler)
    except ConnectionResetError:
      self.connected = False

  def _read_header(self, conn, msg):
    while len(msg) < 4:
      data = conn.recv(1024)
      if not data:
        raise ConnectionError
      msg.extend(data)

    assert len(msg) >= 4
    header = msg[:4]
    msg = msg[4:]
    return int_from_bytes(header), msg

  def _loop(self, conn, handler):
    # whether to read the header in the
    # next iteration or not.
    read_header = True
    msg = bytearray()
    while True:
      if read_header:
        try:
          l, msg = self._read_header(conn, msg)
        except ConnectionError:
          return
        read_header = False

      if l <= len(msg):
        handler(self._deserializer(msg[:l]))
        msg = msg[l:]
        read_header = True
      else:
        data = conn.recv(1024)
        if not data:
          return
        msg.extend(data)


class Sender(Receiver):

  def _add_header(self, msg):
    header = int_to_bytes(len(msg))
    return header + msg

  def _loop(self, conn, handler):
    while True:
      data = handler()
      msg = self._serializer(data)
      msg = self._add_header(msg)
      conn.sendall(msg)
