import argparse
import os
import sys
import time
from collections import deque
from threading import Thread

import gym
import numpy as np
import queue
import tensorflow as tf
from absl import app
from rl_app.gameplay import GamePlay
from rl_app.model import Model
from rl_app.network.network import Receiver, Sender
from rl_app.util import Timer, put_overwrite
from scripts.download_model import ENV_TO_FNAME, MODEL_CACHE_DIR
from tensorpack import *

parser = argparse.ArgumentParser()
parser.add_argument('--env_name', type=str, required=True)
parser.add_argument('--frames_port', type=int, required=True)
parser.add_argument('--action_port', type=int, required=True)
parser.add_argument('--n_cpu', default=4, type=int)
parser.add_argument('--model_fname',
                    type=str,
                    default=None,
                    help='Optional string to specify the model weights')
parser.add_argument('--time', type=int, default=60)


def get_num_actions(env_name):
  env = gym.make(env_name)
  return env.action_space.n


class Agent:

  def __init__(self, env_name, frames_port, action_port, n_cpu, model_fname,
               total_time):

    model_fname = model_fname or os.path.join(MODEL_CACHE_DIR,
                                              ENV_TO_FNAME[env_name])
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
    self.total_time = total_time
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
    self._process_thread = Thread(target=self._process)
    self._process_thread.daemon = True
    self._process_thread.start()
    while not self._frames_socket.connected:
      time.sleep(.1)
    time.sleep(self.total_time)

  def _process(self):
    """deques the frames and runs prediction network on them."""
    while True:
      s = GamePlay.decode_obs(self._frames_q.get())
      if s is None:
        return
      assert isinstance(s, np.ndarray)
      with Timer() as agent_timer:
        s = np.expand_dims(s, 0)  # batch
        act = self.pred(s)[0][0].argmax()
      put_overwrite(self._actions_q, act)

      print('.', end='', flush=True)
      # print('Avg agent neural net eval time: %.3f' % agent_timer.time())

  def record_frame(self, frame):
    put_overwrite(self._frames_q, frame)

  def _get_action(self):
    return self._actions_q.get()


def main(argv):
  args = parser.parse_args(argv[1:])
  agent = Agent(env_name=args.env_name,
                frames_port=args.frames_port,
                action_port=args.action_port,
                n_cpu=args.n_cpu,
                model_fname=args.model_fname,
                total_time=args.time + 5)
  agent.start()


if __name__ == '__main__':
  app.run(main)
