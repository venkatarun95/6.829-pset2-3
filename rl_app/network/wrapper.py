from caraml.zmq import ZmqClient
import inspect


class RemoteClient:

  def __init__(self,
               host,
               port,
               addr=None,
               serializer='pyarrow',
               deserializer='pyarrow',
               timeout=-1):
    self._host = host
    self._port = port
    self._addr = addr
    self._socket_kwargs = dict(serializer=serializer,
                               deserializer=deserializer,
                               timeout=timeout)
    self._zmq_client = None

  def _get_client(self):
    if self._zmq_client: return self._zmq_client

    self._zmq_client = ZmqClient(host=self._host,
                                 port=self._port,
                                 address=self._addr,
                                 bind=False,
                                 **self._socket_kwargs)
    return self._zmq_client

  def delegate_to_server(self, func_name, args, kwargs):
    return self._get_client().request([func_name, args, kwargs])


def iter_methods(obj, *, exclude=None, include=None):
  if exclude is None:
    exclude = []
  if include is None:
    include = dir(obj)

  for fname in dir(obj):
    func = getattr(obj, fname)
    if (callable(func) and fname in include and not fname.startswith('_')
        and not fname in exclude):
      yield fname, func


def delegate_methods(*,
                     target_obj,
                     src_obj,
                     wrapper,
                     doc_signature,
                     include=None,
                     exclude=None):
  """
    Args:
        target_obj: class or instance to be transformed
        src_obj: class or instance that gives the original method
        wrapper: takes (fname, func) and returns the new one (with `self`)
        doc_signature: if True, prepend the signature of the old func to docstring
        exclude_methods:
    """
  assert callable(wrapper)
  for fname, func in iter_methods(src_obj, include=include, exclude=exclude):
    new_func = wrapper(target_obj, fname, func)
    new_func.__name__ = func.__name__
    doc = inspect.getdoc(func)
    if doc is not None and doc_signature:
      sig = str(inspect.signature(func)).replace('(self, ', '(')
      new_func.__doc__ = 'signature: ' + sig + '\n' + doc
    else:
      new_func.__doc__ = doc
    setattr(target_obj, fname, new_func)


def test_bind(func, *args, **kwargs):
  sig = inspect.signature(func)
  try:
    sig.bind(*args, **kwargs)
    return True
  except TypeError:
    return False


def wrapper_fn(self, func_name, old_method):
  """Return new_func which will be set as attr to target obj."""

  def f(*args, **kwargs):
    assert isinstance(self, RemoteClient)
    # Check if args and kwargs match old_method signature
    if not test_bind(old_method, self, *args, **kwargs):
      raise TypeError(
          'Server does not accept the provided args and kwargs for func %s.' %
          func_name)
    return self.delegate_to_server(func_name, args, kwargs)

  return f


def get_remote_client(cls,
                      host=None,
                      port=None,
                      addr=None,
                      timeout=-1,
                      include=None,
                      exclude=None):
  """
    Creates a remote client object and wraps it with
    methods of the remote class.
    If cls has a function f(i, j) then
    calling remote_client.f(i, j) would lead to a remote client request
    and a corresponding fetch.
  """
  rc = RemoteClient(host, port, addr, timeout=timeout)
  delegate_methods(target_obj=rc,
                   src_obj=cls,
                   wrapper=wrapper_fn,
                   doc_signature=False,
                   include=include,
                   exclude=exclude)
  return rc
