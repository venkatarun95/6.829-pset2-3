import socket
from rl_app.network.serializer import get_serializer, get_deserializer, int_from_bytes, int_to_bytes
from rl_app.util import Timer
import time
from threading import Thread
import fcntl, array, struct

READ_SIZE = 8192
MTU = 1500


class Receiver:

  def __init__(self,
               host=None,
               port=None,
               bind=True,
               serializer='pyarrow',
               deserializer='pyarrow',
               data_unsent_thresold=MTU,
               verbose=False):
    self._thread = None
    self.host = host
    self.port = port
    self._data_unsent_thresold = data_unsent_thresold
    self._serializer = get_serializer(serializer)
    self._deserializer = get_deserializer(deserializer)
    self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    self.socket.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
    self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    self.socket.setsockopt(socket.SOL_TCP, socket.TCP_CONGESTION, b'ccp')
    # self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 20000)
    # self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 9000)

    self.bind = bind
    self.connected = False
    self.verbose = verbose
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

  def get_cwnd(self):
    fmt = "B" * 7 + "I" * 24  #+ "Q" * 4 + "I" * 6 + "Q" * 3
    tcp_info = struct.unpack(
        fmt, self.socket.getsockopt(socket.IPPROTO_TCP, socket.TCP_INFO, 104))
    return int(tcp_info[25] * tcp_info[20])

  def _read_n_bytes(self, conn, n_bytes):
    msg = bytearray()
    while len(msg) < n_bytes:
      data = conn.recv(min(READ_SIZE, n_bytes - len(msg)))
      if not data:
        raise ConnectionError
      msg.extend(data)

    assert len(msg) == n_bytes
    return msg

  def _read_header(self, conn):
    header = self._read_n_bytes(conn, 4)
    return int_from_bytes(header)

  def _loop(self, conn, handler):
    # whether to read the header in the
    # next iteration or not.
    try:
      while True:
        with Timer() as timer:
          l = self._read_header(conn)
          msg = self._read_n_bytes(conn, l)
          handler(self._deserializer(msg))
        if self.verbose:
          print('cycle time: %.3f' % timer.time())
    except ConnectionError:
      if self.verbose:
        print('Received ConnectionError')
      return


# SIOCOUTQ = 0x5411
SIOCOUTQNSD = 0x894B


class Sender(Receiver):

  def _add_header(self, msg):
    header = int_to_bytes(len(msg))
    return header + msg

  def _get_data_not_sent(self, fno):
    buf = array.array('i', [-1])
    fcntl.ioctl(fno, SIOCOUTQNSD, buf, True)
    val = int(buf[0])
    if self.verbose:
      print('not yet sent (SIOCOUTQNSD): ', val)
    return val

  def _loop(self, conn, handler):
    fno = conn.fileno()
    while True:
      while True:
        data_not_sent = self._get_data_not_sent(fno)
        if data_not_sent <= self._data_unsent_thresold:
          break
        else:
          time.sleep(.0005)
      data = handler()
      msg = self._serializer(data)
      msg = self._add_header(msg)
      while len(msg) > 0:
        sent = conn.send(msg)
        msg = msg[sent:]
