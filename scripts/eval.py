import argparse
import glob
import numpy as np
import os
import random
import shutil
import subprocess
import tarfile

parser = argparse.ArgumentParser()
parser.add_argument('--run', dest='run', action='store_true')
parser.add_argument('--upload', dest='upload', action='store_true')
parser.add_argument('--results_dir', help='Directory to store results in/upload results from', default='eval_results/', type=str)
parser.add_argument('--team', help='Registered team name', default='', type=str)
parser.add_argument('--seed', default=1, type=int, help='Pick a different seed for evaluation. Note, you should upload only experiments with the default seed to the leaderboard')
args = parser.parse_args()

def renormalize_trace_file(ifname, ofname, tpt):
    ''' Read trace file `ifname` and output to `ofname` a trace file with an
    average of `tpt` Mbit/s '''

    # Read the file
    trace = []
    with open(ifname, 'r') as f:
        for line in f.readlines():
            trace.append(int(line))
    trace = np.asarray(trace, dtype=np.float64)

    # Average throughput of the input trace file (in bits/s)
    in_tpt = 1500 * 8 * len(trace) / (1e-3 * trace[-1])

    # Renormalize
    trace *= in_tpt / (tpt * 1e6)

    # Output into new trace file
    with open(ofname, 'w') as f:
        for t in trace:
            f.write(str(int(t)) + '\n')

def run():
    # Check if the results directory is already there
    if os.path.exists(args.results_dir):
        print("File/directory '%s' already exists. Overwrite (y/n)?" % args.results_dir)
        if input() != 'y':
            exit(1)
        # Delete
        shutil.rmtree(args.results_dir)
    os.mkdir(args.results_dir)

    # List of all the trace files (without the .up)
    tracefiles = ["ATT-LTE-driving-2016", "ATT-LTE-driving",
    "TMobile-LTE-driving", "TMobile-LTE-short", "TMobile-UMTS-driving",
    "Verizon-EVDO-driving", "Verizon-LTE-driving", "Verizon-LTE-short"]

    # So we can find 'rl_app' module
    os.environ['PYTHONPATH'] = os.getcwd()

    # Pick some random configurations and run them
    random.seed(args.seed)
    for _ in range(5):
        tracefile = "/usr/share/mahimahi/traces/" + tracefiles[random.randint(0, len(tracefiles)-1)]
        # In mbps
        avg_tpt = 0.5 + 1.5 * random.random()
        # In ms
        rtt = 2 * int(2.5 + 5 * random.random())
        # queue =  queue_size_factor * BDP
        queue_size_factor = 1 + 50 * random.random()
        queue = int(queue_size_factor * (1.0e6 * avg_tpt / (1500. * 8)) * (rtt / 1000.))
        name = "%s-%.2f-%.2f-%d" % (os.path.basename(tracefile), avg_tpt, rtt, queue)

        # Create a renormalized trace file
        renormalize_trace_file(tracefile + '.up', '/tmp/trace.up', avg_tpt)

        # Run
        cmd = 'python3 scripts/run_exp.py -n {name} --results_dir {results_dir} -r {rtt} -T /tmp/trace.up --queue_size {queue}'\
        .format(
            name=name, results_dir=args.results_dir, rtt=rtt, queue=queue
        )
        print(cmd)
        subprocess.run(cmd, shell=True)

def upload():
    import requests

    # Check if the results directory is there
    if not os.path.exists(args.results_dir):
        print("Results directory '%s' doesn't exist. Run the experiment to create directory")
        return

    if args.team == '':
        print("Please specify team name using '--team'")
        return

    # If the tarball already exists, delete
    tfname = os.path.join(args.results_dir, 'results.tar.gz')
    if os.path.exists(tfname):
        os.remove(tfname)

    # Put folder into a tarball
    print("Writing tarfile...")
    tar = tarfile.open(tfname, 'x:gz')
    tar.add(args.results_dir)
    tar.close()

    with open(tfname, 'rb') as f:
        files = {"results": f}
        data = {"team": args.team}
        r = requests.post('http://6829fa18.csail.mit.edu/upload_file', data=data, files=files)
        print(r.content.decode())

    # Example using curl
    # curl localhost:8888/upload_file -Fteam=myteam2 -Fresults='@eval_results/results.tar.gz'

if args.run:
    run()
if args.upload:
    upload()
