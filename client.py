import gym, atari_py

from util import NetObjects, port
import socket
import time

#env = gym.make('SpaceInvaders-v0')
env = gym.make('CartPole-v0')

# Connect to server
#sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock = socket.create_connection(('100.64.0.1', port))
net_objs = NetObjects(sock)

tot_reward = 0

observation = env.reset()
for _ in range(100):
    #env.render()

    net_objs.send_obj(list(observation))
    action = net_objs.recv_obj()

    observation, reward, done, info = env.step(action) # take a random action

    tot_reward += reward
    if done:
        observation = env.reset()
    print(reward, tot_reward)
env.close()

print(tot_reward)
