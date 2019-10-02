out_dir=./

for n in 1 2 4 8 16 32 100; do
  python generate_const_mahimahi_traces.py -n $n -d 1 >$out_dir/`awk "BEGIN {print $n}"`mbps.log
done
