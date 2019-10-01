from absl import app
import argparse
import numpy as np
import os
import tensorflow as tf

from rl_app.model import Model
from rl_app.network.network import ZmqServer

parser = argparse.ArgumentParser()
parser.add_argument('--bind_port', type=int, required=True)
parser.add_argument('--n_cpu', default=4, type=int)


class Agent:

  def __init__(self, port, n_cpu):
    self.pred = None
    self.zmq_server = ZmqServer(host='*', port=port)
    self.n_cpu = n_cpu

  def serve_forever(self):
    self.zmq_server.start_loop(self._handle_requests, blocking=True)

  def _handle_request(self, req):
    req_fn, args, kwargs = req
    assert isinstance(req_fn, str)
    try:
      fn = getattr(self, req_fn)
      return fn(*args, **kwargs)
    except AttributeError:
      logging.error('Unknown request func name received: %s', req_fn)

  def register(self, env_name, n_actions, action_receiver_port):
    if self.pred:
      raise Exception(
          'Multiple registration requests received. This is not supported.')

    model_fname = os.path.join(MODEL_CACHE_DIR, ENV_TO_FNAME[env_name])

    if not os.path.isfile(model_fname):
      raise Exception(
          'Download model weights into %s before starting the agent. See Instructions for details.'
          % model_fname)

    self._frames_q = threading.Queue()
    self.pred = OfflinePredictor(
        PredictConfig(
            model=Model(),
            session_init=SmartInit(model_fname),
            input_names=['state'],
            output_names=['policy'],
            session_creator=sesscreate.NewSessionCreator(config=tf.ConfigProto(
                intra_op_parallelism_threads=self.n_cpu,
                inter_op_parallelism_threads=self.n_cpu))))

    frames_q = threading.Queue()
    actions_q = threading.Queue()
    self._frames_q = frames_q
    self._actions_q = actions_q
    self._process_thread = threading.Thread(target=self._process,
                                            args=(
                                                frames_q,
                                                actions_q,
                                            ))
    self._action_pusher_thread = threading.Thread(target=self._push_actions,
                                                  args=(actions_q, ))
    self._action_receiver = ZmqSender(host='')
    self._process_thread.start()

  def _process(self, frames_q, actions_q):
    """deques the frames and runs prediction network on them."""
    while True:
      s = frames_q.get()
      if s is None:
        return
      assert isinstance(s, np.ndarray)
      s = np.expand_dims(s, 0)  # batch
      act = self.pred(s)[0][0].argmax()
      actions_q.put(act)

  def _push_actions(self, actions_q):
    while True:
      act = actions_q.get()
      self._action_sender.


  def record_frame(self, s):
    self._frames_q.put(s)


def main(argv):
  args = parser.parse_args(argv[1:])
  agent = Agent(
      port=args.bind_port,
      n_cpu=args.n_cpu,
  )
  agent.serve_forever()


if __name__ == '__main__':
  app.run(main)
