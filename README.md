6.829 Fall 2018 Problem Set 2
=============================

You have the option of working in teams of up to 2 people. You may collaborate and discuss ideas with others in the class, but your solutions and presentation must be your team's own. Do not look at other teams' solutions or copy them from anywhere. Please list your collaborators on your submission.

Introduction
------------

You are tasked with creating a walking robot (in simulation of course). Unfortunately, the robot doesn't have enough compute resources to be able to run its control algorithm locally. Instead, it uses a cellular connection to send its state to a remote server, which responds with commands to control its motors. For remote control to be effective, the commands must come frequently and with minimal delay. This requires the network to provide high throughput while maintaining low queuing delay. You are hired to come up with a congestion control protocol that can simultaneously achieve these objectives over a cellular network.

Cellular networks experience rapidly varying link rates, which the congestion controller should track closely. If it transmits too fast, queues build up, which increases delay. Hence feedback from the server will be delayed, and the robot will fall. If it transmits too slowly, then the server is missing opportunities to gain fine control over the robot. A good protocol will carefully balance between the conflicting objectives.

The application _can_ report its state and receive a command from the server 30 times per second. Think of these as frames per second (fps). However, this may not be possible under all network conditions. When network throughput is low, the application may reduce its fps to adapt to the available link rate. For pset 2, we have provided a simple fps adaptation algorithm. In pset3, you will be able to modify this algorithm to get better performance.

Setup
-----

As you have become familiar with network emulation from Lab 1, we do not require you to do this again for Lab 2. We provide a `Vagrantfile` which you can use to configure and run a virtual machine you can use for development and testing for your congestion control algorithm. You may also mirror the instructions in the `Vagrantfile` to run it on your own Linux machine, however we only support Vagrant installations. For the final submission, we only require the code for your congestion controller.

To set up your environment, first clone this repository.
Then, install [Vagrant](https://www.vagrantup.com/) and [Virtualbox](https://www.virtualbox.org/) and run `vagrant up`.
The [vagrant-faster plugin](https://github.com/rdsubhas/vagrant-faster) may be useful for you.
You can now access the virtual machine with `vagrant ssh`. This repository is mounted at `/pset2-3`, which is synchronized with the folder on your host machine. To get baseline results, first run `./init.sh` in `/pset2-3`, and then run `run.sh` each time you want to test changes to your algorithms.

Contest
-------

This problem set involves a contest. We will host a [leaderboard](http://6829fa18.csail.mit.edu) of the submissions, so you can see how well your fellow congestion control developers are doing as well as test using our link conditions. To submit to the leaderboard, commit your work and run `make submit`. We expect every team to continuously submit to the leaderboard as they improve their algorithms!

The contest server will choose several random link configurations each day on which to evaluate every submission. The constraints are:
 - Link capacity between 1 Mbit/s and 96 Mbit/s
 - RTT between 2ms and 100ms
 - Test duration between 30s and 60s
 - k (number of connections to emulate) between 1 and 10
 - Queue buffer between 0.25 * BDP and 4 * BDP, and such that every flow can have at least 2 packets in the queue.

Submissions are scored on how well your robot performs. Each submission will be run on several (usually 5) configurations, and your score is the average among all the runs. Submissions will use the team name you choose, not your ldap (see Submission Instructions). Note that because of the randomized experiment conditions, your spot on the leaderboard may change from day to day!

CCP
---

This lab makes significant use of [ccp](https://ccp-project.github.io). You will be implementing a congestion control algorithm using this framework. CCP exposes both a Rust and a Python API. Documentation for the Rust API and `portus`, the CCP runtime library, is [here](https://docs.rs/portus). The Python API is undocumented but wraps the API defined in `portus`.

While we recommend using the Rust API, we will also accept Python submissions. As a result, we leave it up to you to add to this repository your own code organization for your submission, and you must modify `scripts/algs.py` and the `your_code` directory to produce results for your algorithm when `scripts/run_exp.py` is run.
You are free to modify any of the scripts here for your experimental convenience, but when we run your code we will discard all changes to current files in this repository except `scripts/algs.py` and the `your_code` directory.


Submission Instructions
-----------------------

After you optionally choose a teammate, come up with a team name, and enter that name into a file called `NAME.txt`. Enter the MIT ldaps of everyone in your team into `PARTNER.txt`, one name per line. You must submit to the leaderboard at least once before the deadline.

In the `your_code` directory, commit a file `README.md` that includes a 1-2 paragraph writeup of your approach, why you chose it, and what you tried. This is only required for your final submission, not for leaderboard submissions.

Submit a link to a *private* github.mit.edu repository (everyone must do this so we can verify teammate reciprocity). Your repository must be cloned from this starter repository. Ensure that the usernames "addanki" and "venkatar" are added as collaborators to your repository.
We will only consider commits made before the submission deadline. If you would like to use an extension day, include the string "EXTENSION-DAY" in *all* commit messages for commits made after the deadline AND contact the staff individually once you are done committing. You must submit the form (which tells us where your repository is) before the original deadline, even if you are using extension days. Extension days cannot be used for contest submissions.

Contact Instructions
--------------------

If you wish to contact the course staff regarding the psets (e.g. to ask for extensions), please include the keyword '6.829-PSET2' or '6.829-PSET3' in the subject online.

# Useful commands
# for xdisplay from ssh
export DISPLAY=localhost:10.0
