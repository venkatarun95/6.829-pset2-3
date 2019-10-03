import queue
import time


def put_overwrite(q, item):
  """Put item into queue without blocking.
    If full, remove an item out of the queue.
    Guaranteed not to block."""
  assert q.maxsize > 0
  try:
    q.put_nowait(item)
  except queue.Full:
    # discard an item out of the queue
    try:
      q.get_nowait()
    except queue.Empty:
      pass
    q.put(item)


class Timer(object):

  def __init__(self, verbose=False):
    self.verbose = verbose
    self.elapsed = 0.0

  def __enter__(self):
    self.elapsed = 0
    self.elapsed_secs = 0
    self.start = time.clock()
    return self

  def __exit__(self, *args):
    self.elapsed_secs = time.clock() - self.start
    self.elapsed = float(self.elapsed_secs * 1000)  # millisecs
    if self.verbose:
      print('elapsed time: %f ms' % self.elapsed)

  def time(self):
    return self.elapsed_secs
