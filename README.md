6.829 Fall 2019 Problem Set 2
=============================

For this pset, you have the option of working in teams of up to 2 people. You may collaborate and discuss ideas with others in the class, but your solutions and presentation must be your team's own. Do not look at other teams' solutions or copy them from anywhere. Please list your collaborators on your submission.

Introduction
------------
Getting sick and tired of playing your games on a boring old PC?
Wanna play at 4K@144fps with no lag even from your smartphone?
Wanna upgrade your gaming rig to a million cores?
You've come to the right place!

In this pset, you're going to be tackle some of the challenges in deploying gaming on the cloud.
For a commercial example see: [Google Stadia](<https://store.google.com/us/product/stadia_learn?hl=en-US>)


A gaming server has been deployed on the cloud for you. Video frames from the game are being streamed to your smart phone and the actions that you take are travelling back along the same path to the server.
For the setup to be effective, the game frames must come frequently and with minimal delay. This requires the network to provide high throughput while maintaining low delay.
You are tasked to come up with a congestion control protocol that can simultaneously achieve these objectives over a cellular network.


Cellular networks experience rapidly varying link rates, which the congestion controller should track closely. If it transmits too fast, queues build up, which increases delay. Hence feedback from the server will be delayed, and the gamer could lose control of the game. If it transmits too slowly, then the gamer is missing opportunities to gain fine control over the game. A good protocol will carefully balance between the conflicting objectives.

The application _can_ report its state and receive a command from the server up to 100 times per second. Think of these as frames per second (fps). However, this may not be possible under all network conditions. When network throughput is low, the application may not send all the frames that it generates. We have provided a simple adaptation algorithm to decide when to drop a video frame at the application layer.

We've provided you with a gaming server that simulates the classic "Breakout" game from Atari.
To simulate an expert gamer we use an artificial neural network that has been trained using Reinforcement Learning to achieve high scores on Breakout.
The gameplay server is streaming the game frames on an emulated link using [mahimahi](http://mahimahi.mit.edu/).
The throughput and delay of this link are varied to simulate cellular and wide range of link conditions for evaluation.
You do not need to implement any part of the game play or emulation as it has already been provided to you along with the starter code. You can just focus on implementing a good congestion control algorithm that can achieve low delays while maintaing high throughput.

Here is demo when an oracle congestion control algorithm is used under favorable network conditions.
Click on the image below to open the demo video on youtube.

[![Breakout gameplay](http://img.youtube.com/vi/QuW4gUrAqTc/0.jpg)](http://www.youtube.com/watch?v=QuW4gUrAqTc)


Contest
-------

This problem set involves a contest. We will host a [leaderboard](http://6829fa18.csail.mit.edu) of the submissions, so you can see how well your fellow congestion control developers are doing as well as test using our link conditions. We expect every team to continuously submit to the leaderboard as they improve their algorithms!

The contest server will choose several random link configurations each day on which to evaluate every submission. The constraints are:
 - Link capacity :
   - Constant throughput: Chosen from the range of 0.25 Mbit/s to 10 Mbit/s
     - Variable throughput: Cellular traces normalized so that average throughput is between 0.25 Mbit/s and 10 Mbit/s
 - Frame rate between 20fps and 60fps
 - RTT between 2ms and 50ms
 - Test duration between 60s and 240s
 - Queue buffer between 0.25 * BDP and 4 * BDP, and such that every flow can have at least 2 packets in the queue.

Submissions are scored on the score achieved by the agent. Each submission will be run on several (usually 5) configurations, and your score is the average among all the runs. Submissions will use the team name you choose, not your ldap (see Submission Instructions below). Note that because of the randomized experiment conditions, your spot on the leaderboard may change from day to day!

Please hang tight for instructions on how to submit to the leaderboard. The leaderboard will be up and running very soon.

Setup
-----


We provide a `Vagrantfile` which you can use to configure and run a virtual machine you can use for development and testing for your congestion control algorithm. You may also mirror the instructions in the `Vagrantfile` to run it on your own Linux machine, however we only support Vagrant installations. For the final submission, we only require the code for your congestion controller. We want you to make sure that this code works with the latest version of the starter code.

To set up your environment, first clone this repository.
Then, install [Vagrant](https://www.vagrantup.com/) and [Virtualbox](https://www.virtualbox.org/) and run `vagrant up`.
The [vagrant-faster plugin](https://github.com/rdsubhas/vagrant-faster) may be useful for you.
You can now access the virtual machine with `vagrant ssh`. This repository is mounted at `/pset2-3`, which is synchronized with the folder on your host machine. After every system restart, first run `./init.sh` in `/pset2-3`, and then use `run.sh` each time you want to test changes to your algorithms.


CCP
---

This lab makes significant use of [ccp](https://ccp-project.github.io). You will be implementing a congestion control algorithm using this framework. CCP exposes both a Rust and a Python API. Documentation for the Rust API and `portus`, the CCP runtime library, is [here](https://docs.rs/portus). The Python API is undocumented but wraps the API defined in `portus`.

While we recommend using the Rust API, we will also accept Python submissions.
As a result, we leave it up to you to add to this repository your own code organization for your submission, and you must make sure that your congestion control algorithm is *running* before invoking `scripts/run_exp.py`. See `your_code/README.md` for instructions on how to start your congestion control algorithm.
You are free to modify any of the scripts here for your experimental convenience, but when we run your code we will discard all changes to current files in this repository except the `your_code` directory.

Starter Code
----
We've provided you with code to start the agent process and the real-time atari simulator with the desired rtt and throughput conditions in order to evaluate your congestion control algorithm.
All you have to do is implement your algorithm as specified in `your_code` directory and follow the below steps to evaluate your algorithm.

First, make sure that your congestion control algorithm is switched on. See `your_code/README.md` for instructions on how to start your ccp program.

Once, your congestion control algorithm is running, in another shell run the script run.sh in order to start the gameplay server, agent and mahimahi emulator. See below for invokation arguments to pass for `run.sh`

To launch a run using the name `sample_run` with
Throughput = `thr`,  RTT = `rtt`, experiment time = `t`, queue capacity of `q` packets launch the following commands in the given order:

```
./run.sh sample_run $thr $rtt $t $q
```

Please note that the following units for these arguments:
* `thr` -> Mbps
* `rtt` -> milli second
* `t` -> seconds
* `q` -> # of packets

Outputs of this command can be found under the folder `results/sample_run`.
You should be able to find the following files there on a successful run:
* `throughput.png` : Ingress, Egress, Capacity at the link in Mbps
* `game_results/ping.png` : RTTs clocked by ping application in milli second
* `game_results/cwnd.png` : cwnd reported for the bottleneck flow of the application
* `game_results/video_*/\*.mp4` : Video file showing the gameplay
* `game_results/game_stats.json` : frame by frame stats showing the delay in the action applied.
* `game_results/results.json` : Overall summary of the results.

If you would like to see the game being played in real time then pass `--render` argument at the end to `run.sh`

Submission
-----------------------

After you optionally choose a teammate, come up with a team name, and enter that name into a file called `NAME.txt`. Enter the MIT ldaps of everyone in your team into `PARTNER.txt`, one name per line. You must submit to the leaderboard at least once before the deadline.

In the `your_code` directory, commit a file `WRITEUP.md` that includes a 1-2 paragraph writeup of your approach, why you chose it, and what you tried. This is only required for your final submission, not for leaderboard submissions.

Submit a link to a *private* github.mit.edu repository (everyone must do this so we can verify teammate reciprocity). Your repository must be cloned from this starter repository. Ensure that the usernames "addanki" and "venkatar" are added as collaborators to your repository.
We will only consider commits made before the submission deadline. If you would like to use an extension day, include the string "EXTENSION-DAY" in *all* commit messages for commits made after the deadline AND contact the staff individually once you are done committing. You must submit the form (which tells us where your repository is) before the original deadline, even if you are using extension days. Extension days cannot be used for contest submissions.

Help
--------------------

If you wish to contact the course staff regarding the psets (e.g. to ask for extensions), please include the keyword '6.829-PSET2' or '6.829-PSET3' in the subject online.
