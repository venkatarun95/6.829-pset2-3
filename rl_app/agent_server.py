from absl import app
import argparse
import numpy as np
import os
import tensorflow as tf
from collections import deque
import queue

import gym
from tensorpack import *
from rl_app.model import Model
from rl_app.network.network import Receiver, Sender
from rl_app.gameplay import GamePlay
from scripts.download_model import MODEL_CACHE_DIR, ENV_TO_FNAME
from rl_app.util import put_overwrite

parser = argparse.ArgumentParser()
parser.add_argument('--env_name', type=str, required=True)
parser.add_argument('--frames_port', type=int, required=True)
parser.add_argument('--action_port', type=int, required=True)
parser.add_argument('--n_cpu', default=4, type=int)


def get_num_actions(env_name):
  env = gym.make(env_name)
  return env.action_space.n


class Agent:

  def __init__(self, env_name, frames_port, action_port, n_cpu):

    model_fname = os.path.join(MODEL_CACHE_DIR, ENV_TO_FNAME[env_name])
    num_actions = get_num_actions(env_name)
    if not os.path.isfile(model_fname):
      raise Exception(
          'Download model weights into %s before starting the agent. See Instructions for details.'
          % model_fname)

    self.pred = OfflinePredictor(
        PredictConfig(
            model=Model(num_actions),
            session_init=SmartInit(model_fname),
            input_names=['state'],
            output_names=['policy'],
            session_creator=sesscreate.NewSessionCreator(
                config=tf.ConfigProto(intra_op_parallelism_threads=n_cpu,
                                      inter_op_parallelism_threads=n_cpu))))

    self._frames_q = queue.Queue(1)
    self._actions_q = queue.Queue(1)
    self.n_cpu = n_cpu
    self.frames_port = frames_port
    self.action_port = action_port

  def start(self):
    self._frames_socket = Receiver(host='0.0.0.0',
                                   port=self.frames_port,
                                   bind=True)
    self._actions_socket = Sender(host='0.0.0.0',
                                  port=self.action_port,
                                  bind=True)
    self._frames_socket.start_loop(self.record_frame, blocking=False)
    self._actions_socket.start_loop(self._get_action, blocking=False)
    self._process()

  def _process(self):
    """deques the frames and runs prediction network on them."""
    while True:
      s = GamePlay.decode_obs(self._frames_q.get())
      if s is None:
        return
      assert isinstance(s, np.ndarray)
      s = np.expand_dims(s, 0)  # batch
      act = self.pred(s)[0][0].argmax()
      put_overwrite(self._actions_q, act)

  def record_frame(self, frame):
    put_overwrite(self._frames_q, frame)

  def _get_action(self):
    return self._actions_q.get()


def main(argv):
  args = parser.parse_args(argv[1:])
  agent = Agent(
      env_name=args.env_name,
      frames_port=args.frames_port,
      action_port=args.action_port,
      n_cpu=args.n_cpu,
  )
  agent.start()


if __name__ == '__main__':
  app.run(main)
