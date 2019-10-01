import socket
from rl_app.network import get_serializer, get_deserializer, int_from_bytes, int_to_bytes
from threading import Thread


class Receiver:

  def __init__(self,
               host=None,
               port=None,
               bind=True,
               serializer='pyarrow',
               deserializer='pyarrow'):
    self._thread = None
    self._serializer = get_serializer(serializer)
    self._deserializer = get_deserializer(deserializer)
    self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.bind = bind
    if bind:
      self.socket.bind((host, port))
    else:
      # if server has not called listen yet. Keep retrying
      while True:
        try:
          self.socket.connect((host, port))
          break
        except ConnectionError:
          time.sleep(.5)
          print('connect to %s:%d failed. Retrying in 500ms.')

  def start_loop(self, handler, blocking=False):
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
      self._loop(handler)
    else:
      if self._thread:
        raise RuntimeError('loop is already running')
      self._thread = Thread(target=self._loop, args=[handler])
      self._thread.start()
      return self._thread

  def _start(self, handler):
    if self.bind:
      self.socket.listen(1)
      conn, addr = s.accept()
      with conn:
        self._loop(conn, handler)
    else:
      self._loop(self.socket, handler)

  def _read_header(self, conn, msg):
    while len(msg) < 4:
      data = conn.recv(1024)
      msg.extend(data)

    assert len(msg) >= 4
    header = msg[:4]
    msg = msg[4:]
    return int_from_bytes(header), msg

  def _loop(self, conn, handler):
    read_header = False
    msg = bytearray()
    while True:
      data = conn.recv(1024)
      if not data:
        # we only handle one connection
        return
      msg.extend(data)
      while l <= len(msg):
        handler(self._deserializer(msg[:l]))
        msg = msg[l:]
        # if nothing left connection could terminate here
        if len(msg) == 0:
          data = conn.recv(1024)
          if not data:
            return
          msg.extend(data)

        l, msg = self._read_header(conn, msg)


class Sender(Receiver):

  def _add_header(self, msg):
    header = int_to_bytes(len(msg))
    return header + msg

  def _loop(self, conn, handler):
    while True:
      data = handler.get()
      if data is None:
        conn.close()
        return
      msg = self._serializer(data)
      msg = self._add_header(msg)
      conn.sendall(msg)
