import argparse
import os
import sys
import time
from collections import deque
from threading import Thread, Lock

import gym
import numpy as np
import queue
import tensorflow as tf
from absl import app
from rl_app.gameplay import GamePlay
from rl_app.model import Model, STATE_SHAPE, FRAME_HISTORY
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
parser.add_argument('--time', required=True, type=int)
parser.add_argument('--verbose', dest='verbose', action='store_true')


def get_num_actions(env_name):
  env = gym.make(env_name)
  return env.action_space.n


class Agent:

  def __init__(self,
               env_name,
               frames_port,
               action_port,
               n_cpu,
               model_fname,
               time,
               verbose=False):

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
    # self._latest_frame = None
    self.verbose = verbose
    self._actions_q = queue.Queue(1)
    self.n_cpu = n_cpu
    self.frames_port = frames_port
    self.action_port = action_port
    self._gameover_q = queue.Queue(1)
    self.frames_started = False
    self.time = time
    self.lock = Lock()

  def start(self):
    self._warmup()
    self._frames_socket = Receiver(host='0.0.0.0',
                                   port=self.frames_port,
                                   bind=True,
                                   verbose=self.verbose)
    self._actions_socket = Sender(host='0.0.0.0',
                                  port=self.action_port,
                                  bind=True)
    self._frames_socket.start_loop(
        self.record_frame,
        new_connection_callback=self._traffic_frames_started,
        blocking=False)
    self._actions_socket.start_loop(self._put_action, blocking=False)
    self._process_thread = Thread(target=self._process)
    self._process_thread.daemon = True
    self._process_thread.start()
    start_t = time.time()
    while time.time() < start_t + self.time:
      if self.frames_started and self._frames_socket.connected:
        try:
          self._gameover_q.get_nowait()
          break
        except queue.Empty:
          pass
      time.sleep(.5)

  def _warmup(self):
    # warmup tensorflow
    s = np.zeros(((1, ) + STATE_SHAPE + (FRAME_HISTORY, )), dtype=np.float32)
    self.pred(s)[0][0].argmax()

  def _traffic_frames_started(self, *args):
    self.frames_started = True

  def _wrap_action(self, act, frame_metadata):
    act = dict(action=act, **frame_metadata)
    return act

  def _unwrap_frame(self, frame):
    obs = GamePlay.decode_obs(frame['encoded_obs'])
    del frame['encoded_obs']
    return obs, frame

  def _process(self):
    """deques the frames and runs prediction network on them."""
    while True:
      with Timer() as data_timer:
        frame = self._frames_q.get()

      with Timer() as agent_timer:
        s, frame_metadata = self._unwrap_frame(frame)
        s = np.expand_dims(s, 0)  # batch
        act = self.pred(s)[0][0].argmax()
        put_overwrite(self._actions_q, self._wrap_action(act, frame_metadata))

      if self.verbose:
        print('.', end='', flush=True)
        print('Avg data wait time: %.3f' % data_timer.time())
        print('Avg agent neural net eval time: %.3f' % agent_timer.time())

  def record_frame(self, frame):
    if frame is None:
      self._gameover_q.put(1)
      return
    # with self.lock:
    #   self._latest_frame = frame
    put_overwrite(self._frames_q, frame, key='frame_q')

  def _put_action(self):
    return self._actions_q.get()


def main(argv):
  args = parser.parse_args(argv[1:])
  agent = Agent(env_name=args.env_name,
                frames_port=args.frames_port,
                action_port=args.action_port,
                n_cpu=args.n_cpu,
                model_fname=args.model_fname,
                time=args.time,
                verbose=args.verbose)
  agent.start()


if __name__ == '__main__':
  app.run(main)
