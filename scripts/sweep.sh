
# quit if any command fails.
set -e
set -o pipefail

run() {

name=$1
thr=$2
rtt=$3
time=$4
rest="${@:5}"

echo "Now running...."

echo "python3 scripts/run_exp.py -- -n=$name --model_cache_dir=/home/arc/model_cache_dir/ \
--results_dir=/home/arc/results/ --rtt=$rtt --time=$time --thr=$thr --dump_video $rest"

python3 scripts/run_exp.py -- -n=$name --model_cache_dir=/home/arc/model_cache_dir/ \
--results_dir=/home/arc/results/ --rtt=$rtt --time=$time --thr=$thr --dump_video $rest
}

time=60

for rtt in 10 20 50; do
  for frac in 2 10; do
    for cc in cubic reno vegas bbr; do
      echo 'arc' | sudo -S bash -c "echo $cc > /proc/sys/net/ipv4/tcp_congestion_control"
      for thr in 1 2 4 8 100; do
        run "${cc}_rtt_${rtt}_thr_${thr}_frac_${frac}" $thr $rtt $time --queue_size_factor=$frac
      done
    done
  done
done

# set it back to what it was.
echo 'arc' | sudo -S bash -c "echo cubic > /proc/sys/net/ipv4/tcp_congestion_control"
