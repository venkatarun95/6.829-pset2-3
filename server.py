import gym
import json
import socket
import sys

from util import NetObjects, port

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind(('0.0.0.0', port))
sock.listen(1)

env = gym.make('CartPole-v0')

while True:
  # Wait for a connection
  print('waiting for a connection')
  connection, client_address = sock.accept()
  net_objs = NetObjects(connection)

  try:
    print('connection from', client_address)

    while True:
      obs = net_objs.recv_obj()
      # Compute the action and respond
      action = env.action_space.sample()
      net_objs.send_obj(action)

  finally:
    # Clean up the connection
    connection.close()
