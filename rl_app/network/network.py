"""
This module has been taken from
https://github.com/SurrealAI/caraml/tree/master/caraml/zmq
"""
"""
Provides abstractions over zmq sockets
"""
from threading import Thread
import zmq
from .serializer import get_serializer, get_deserializer


class ZmqTimeoutError(Exception):
  """
    Raised when a socket operation times out
    """

  def __init__(self):
    super().__init__('Request Timed Out')


class ZmqSocket(object):
  """
        Wrapper around the data that we use to initialize zmq sockets.
        Use establish() to actually create the socket
    """
  SOCKET_TYPES = {'REQ': zmq.REQ, 'REP': zmq.REP}

  def __init__(self,
               *,
               address=None,
               host=None,
               port=None,
               socket_mode,
               bind,
               context=None,
               verbose=True,
               hwm=None):
    """
        Attributes:
            address
            host
            port
            bind
            socket_mode
            socket_type
        Args:
            address: either specify address or (host and port), but not both
            host: "localhost" is translated to 127.0.0.1
                use "*" to listen to all incoming connections
            port: int, specifies which port to connect / bind to
            socket_mode: zmq.PUSH, zmq.PULL, etc., or their string names
            bind: True -> bind to address, False -> connect to address (see zmq)
            context: Zmq.Context object, if None, creates its own context
            verbose: set to True to print log messages
        """
    # Initialize them first as they are used in __del__
    self.established = False
    self._verbose = verbose

    self._context = None
    self._owns_context = False
    self._set_context(context)

    self.host = None
    self.port = None
    self.address = None
    self._set_address(host, port, address)

    if isinstance(socket_mode, str):
      socket_mode = self.SOCKET_TYPES[socket_mode.upper()]
    self.socket_mode = socket_mode
    self.bind = bind

    self._socket = self._context.socket(self.socket_mode)
    if hwm is not None:
      self._socket.set_hwm(hwm)

  def _set_context(self, context):
    if context is None:
      self._context = zmq.Context()
      self._owns_context = True
    else:
      self._context = context
      self._owns_context = False

  def _set_address(self, host, port, address):
    if address is None:
      # https://stackoverflow.com/questions/6024003/why-doesnt-zeromq-work-on-localhost
      if not ((host is not None) and (port is not None)):
        raise ValueError("either specify address or "
                         "(host and port), but not both")
      if host == 'localhost':
        host = '127.0.0.1'
      address = "{}:{}".format(host, port)
    try:
      address = str(address)
      if '://' in address:
        self.address = address
      else:  # defaults to TCP
        self.address = 'tcp://' + address
      self.host, port = self.address.split('//')[1].split(':')
      self.port = int(port)
    except Exception as e:
      raise ValueError('Cannot parse address {}. {}'.format(address, str(e)))

  def unwrap(self):
    """
        Get the raw underlying ZMQ socket
        """
    return self._socket

  def establish(self):
    """
        We want to allow subclasses to configure the socket before connecting
        """
    if self.established:
      return
    self.established = True
    if self.bind:
      if self._verbose:
        logger.infofmt('[{}] binding to {}', self.socket_type, self.address)
      self._socket.bind(self.address)
    else:
      if self._verbose:
        logger.infofmt('[{}] connecting to {}', self.socket_type, self.address)
      self._socket.connect(self.address)
    return self

  def __getattr__(self, attrname):
    """
        Delegate any unknown methods to the underlying self.socket
        """
    if attrname in dir(self):
      return object.__getattribute__(self, attrname)
    else:
      return getattr(self._socket, attrname)

  @property
  def socket_type(self):
    """
        Maps name to socket type, i.e. 'PUB' => zmq.PUB
        Returns:
            zmq.<socket_type>
        """
    reverse_map = {value: name for name, value in self.SOCKET_TYPES.items()}
    return reverse_map[self.socket_mode]


class ZmqClient:
  """
        Sends request and receives reply from ZmqServer
        Powered by a zmq REQ socket
        By default connects
    """

  def __init__(self,
               *,
               host=None,
               port=None,
               address=None,
               bind=False,
               timeout=-1,
               serializer=None,
               deserializer=None,
               callback=None,
               **kwargs):
    """
        Args:
            timeout: how long do we wait for response, in seconds,
                negative means wait indefinitely
            serializer: applied to data sent, should return bytes
                (default: {None})
            deserializer: applied to data received (default: {None})
            callback: if not None, call `callback(socket)` between
                `socket=ZmqSocket()` and `socket.establish()`
                (default: {None})
            **kwargs: Passed to `ZmqSocket.__init__`
        """
    self.timeout = timeout
    self.address = address
    self.host = host
    self.port = port
    self.bind = bind
    self.serializer = get_serializer(serializer)
    self.deserializer = get_deserializer(deserializer)
    self.callback = callback
    self.kwargs = kwargs
    self._setup()

  def _setup(self):
    self.socket = ZmqSocket(address=self.address,
                            host=self.host,
                            port=self.port,
                            socket_mode=zmq.REQ,
                            bind=self.bind,
                            **self.kwargs)
    if self.timeout >= 0:
      self.socket.setsockopt(zmq.LINGER, 0)
      self.poller = zmq.Poller()
      self.poller.register(self.socket.unwrap(), zmq.POLLIN)
    if self.callback is not None:
      self.callback(self.socket)
    self.socket.establish()

  def request(self, msg):
    """
        Send request @msg to self.address
        https://github.com/zeromq/pyzmq/issues/132
        We allow the requester to time out. When timeout happens,
        it will discard the message.
        Args:
            msg: send msg to ZmqServer to request for reply
        Returns:
            reply data from ZmqServer
        Raises:
            ZmqTimeoutError if timed out
        """
    if self.socket.closed:
      self._setup()
    msg = self.serializer(msg)
    self.socket.send(msg)
    if self.timeout >= 0:
      if self.poller.poll(self.timeout * 1000):
        rep = self.socket.recv()
        return self.deserializer(rep)
      else:
        self.socket.close()
        raise ZmqTimeoutError()
    else:
      rep = self.socket.recv()
      return self.deserializer(rep)


class ZmqServer:
  """
    Accepts requests from zmq client and replies back
    Powered by a Zmq REP socket
    By default binds
    """

  def __init__(self,
               *,
               host=None,
               port=None,
               address=None,
               bind=True,
               serializer=None,
               deserializer=None,
               callback=None,
               **kwargs):
    """
        Args:
            host, port, address, bind: See ZmqSocket for details
            serializer: applied to data sent, should return bytes
                (default: {None})
            deserializer: applied to data received (default: {None})
            callback: if not None, call `callback(socket)` between
                `socket=ZmqSocket()` and `socket.establish()`
                (default: {None})
            **kwargs: Passed to `ZmqSocket.__init__`
        """
    self.serializer = get_serializer(serializer)
    self.deserializer = get_deserializer(deserializer)
    self.socket = ZmqSocket(address=address,
                            host=host,
                            port=port,
                            socket_mode=zmq.REP,
                            bind=bind,
                            **kwargs)
    if callback is not None:
      callback(self.socket)
    self.socket.establish()
    self._thread = None
    self._next_step = 'recv'  # for error checking only
    self._stopped = False

  def recv(self):
    """
        Warnings:
            DO NOT call recv() after you start an event_loop
        """
    if self._next_step != 'recv':
      raise ValueError(
          'recv() and send() must be paired. You can only send() now')
    data = self.socket.recv()
    self._next_step = 'send'
    return self.deserializer(data)

  def send(self, msg):
    """
        Warnings:
            DO NOT call send() after you start an event_loop
        """
    if self._next_step != 'send':
      raise ValueError(
          'send() and recv() must be paired. You can only recv() now')
    msg = self.serializer(msg)
    self.socket.send(msg)
    self._next_step = 'recv'

  def stop(self):
    """
            Stop the event loop. Only safe to call if
            Either there is at least one new message
            Or
            it is called by handler
        """
    self._stopped = True

  def _loop(self, handler):
    while True:
      if self._stopped:
        return
      msg = self.recv()  # request msg from ZmqClient
      reply = handler(msg)
      self.send(reply)

  def start_loop(self, handler, blocking=False):
    """
        Args:
            handler: function that takes an incoming client message
                (deserialized) and returns a reply to client
                (which is serialized and sent)
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


class ZmqReceiver(ZmqServer):
  """
        Uses REQ / REP to send and receive data,
        i.e. a client that only expects b'ack'

        by default binds
    """

  def __init__(self,
               *,
               host=None,
               port=None,
               address=None,
               bind=True,
               deserializer=None,
               callback=None,
               **kwargs):
    """
        Args:
            host, port, address, bind: See ZmqSocket for details
            deserializer: applied to data received (default: {None})
            callback: if not None, call `callback(socket)` between
                `socket=ZmqSocket()` and `socket.establish()`
                (default: {None})
            **kwargs: Passed to `ZmqSocket.__init__`
        """
    super().__init__(host=host,
                     port=port,
                     address=address,
                     bind=bind,
                     deserializer=deserializer,
                     callback=callback,
                     **kwargs)

  def recv(self):
    """
            Block then and returns the message sent by ZmqSender

        Returns:
            data: deserialized message
        """
    data = super().recv()
    self.send(b'ack')
    return data

  def _loop(self, handler):
    while True:
      if self._stopped:
        return
      msg = self.recv()  # request msg from ZmqClient
      handler(msg)
