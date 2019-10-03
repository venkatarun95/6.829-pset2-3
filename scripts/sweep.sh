
# quit if any command fails.
set -e
set -o pipefail

run() {

name=$1
thr=$2
rtt=$3
time=$4
action_port=$5
frames_port=$6
rest="${@:8}"

echo "Now running...."

echo "python3 scripts/run_exp.py -- -n=$name --model_cache_dir=/home/arc/model_cache_dir/ \
--results_dir=/home/arc/results/ --rtt=$rtt --time=$time --thr=$thr --dump_video \
--action_port=${action_port} --frames_port=${frames_port} $rest"

python3 scripts/run_exp.py -- -n=$name --model_cache_dir=/home/arc/model_cache_dir/ \
--results_dir=/home/arc/results/ --rtt=$rtt --time=$time --thr=$thr --dump_video \
--action_port=${action_port} --frames_port=${frames_port} $rest
}

time=60

for cc in cubic reno vegas bbr; do
  echo 'arc' | sudo -S bash -c "echo $cc > /proc/sys/net/ipv4/tcp_congestion_control"
  for rtt in 10 20 50; do
    for frac in 2 10; do
      for thr in 1 2 4 8 100; do
        run "${cc}_rtt_${rtt}_thr_${thr}_frac_${frac}" $thr $rtt $time $action_port $frames_port --queue_size_factor=$frac
      done
    done
  done
done

# set it back to what it was.
echo 'arc' | sudo -S bash -c "echo cubic > /proc/sys/net/ipv4/tcp_congestion_control"
