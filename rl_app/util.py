import queue
import time


def put_overwrite(q, item, key=''):
  """Put item into queue without blocking.
    If full, remove an item out of the queue.
    Guaranteed not to block."""
  try:
    q.put_nowait(item)
  except queue.Full:
    # discard an item out of the queue
    try:
      q.get_nowait()
    except queue.Empty:
      pass
    q.put_nowait(item)


class Timer(object):

  def __init__(self, verbose=False):
    self.verbose = verbose
    self.elapsed_secs = 0

  def __enter__(self):
    self.elapsed_secs = 0
    self.start = time.time()
    return self

  def __exit__(self, *args):
    self.elapsed_secs = time.time() - self.start
    if self.verbose:
      print('elapsed time: %f s' % self.elapsed_secs)

  def time(self):
    return self.elapsed_secs


class Clock:

  def __init__(self):
    self.start_t = None

  def reset(self):
    self.start_t = time.time()

  def time_elapsed(self):
    return time.time() - self.start_t
