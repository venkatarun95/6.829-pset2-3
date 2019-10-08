import argparse
import glob
import numpy as np
import os
import random
import shutil
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--run', dest='run', action='store_true')
parser.add_argument('--upload', dest='upload', action='store_true')
parser.add_argument('--results_dir', default='eval_results/', type=str)
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

    # Get all the trace files
    tracefiles = glob.glob('/usr/share/mahimahi/traces/*.up')
    # Remove the .up
    tracefiles = [x[:-3] for x in tracefiles]

    # So we can find 'rl_app' module
    os.environ['PYTHONPATH'] = os.getcwd()

    # Pick some random configurations and run them
    random.seed(1)
    for _ in range(2):
        tracefile = tracefiles[random.randint(0, len(tracefiles))]
        # In mbps
        avg_tpt = 0.5 + 1.5 * random.random()
        # In ms
        rtt = 2 * int(2.5 + 5 * random.random())
        # queue =  queue_size_factor * BDP
        queue_size_factor = 1 + 50 * random.random()
        queue = int(queue_size_factor * (1.0e6 * avg_tpt / (1500. * 8)) * (rtt / 1000.))
        name = "%s-%.2f-%.2f-%d" % (os.path.basename('tracefile'), avg_tpt, rtt, queue)

        # Create a renormalized trace file
        renormalize_trace_file(tracefile + '.up', '/tmp/trace.up', avg_tpt)

        # Run
        cmd = 'python3 scripts/run_exp.py -n {name} --results_dir {results_dir} -r {rtt} -t /tmp/trace.up --queue_size {queue}'\
        .format(
            name=name, results_dir=args.results_dir, rtt=rtt, queue=queue
        )
        print(cmd)
        subprocess.run(cmd, shell=True)

if args.run:
    run()
