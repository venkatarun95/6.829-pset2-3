## Mahimahi traces

We use [mahimahi](http://mahimahi.mit.edu/) as our network emulator for this pset.

In order to emulate a constant capacity link using mahimahi, we need to first create a throughput trace file.
This trace file should be created according to the following format:

```
Each line gives a timestamp in milliseconds (from the beginning of the
trace) and represents an opportunity for one 1500-byte packet to be
drained from the bottleneck queue and cross the link. If more than one
MTU-sized packet can be transmitted in a particular millisecond, the
same timestamp is repeated on multiple lines.

A fixed-rate link may also be represented a trace file. For example, a
link that can pass one MTU-sized packet per millisecond (12 Mbps) can
be represented by a file that contains just "1". By default, mm-link
will repeat the trace file when it reaches the end, so this trace
would represent one packet per millisecond.
```

We've provided you with a simple script in `generate_const_mahimahi_trace.py` that
can automatically generate mahimahi trace files for a given constant throughput value.

If your throughput value is `$x` Mbit/sec where x is an integer, then simply run the following command
to generate the desired trace.
```python3 generate_const_mahimahi_trace.py -n $x```

On the other hand if `$x` is rational number with the reduced form `x = p/q` then use the following command:
```python3 generate_const_mahimahi_trace.py -n $p -d $q```

The above script dumps the trace to stdout. Redirect that to a file named `$xmbps.log` in the `mm_trace` directory.
