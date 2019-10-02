
# quit if any command fails.
set -e
set -o pipefail

run() {

name=$1
thr=$2
rtt=$3
time=$4
rest="${@:5}"

python3 scripts/run_exp.py -- -n=$name --model_cache_dir=/home/arc/model_cache_dir/ \
--results_dir=/home/arc/results/ --rtt=$rtt --time=$time --thr=$thr --dump_video $rest
}

rtt=10
time=120

for frac in 2 10; do
  for cc in reno cubic vegas bbr; do
    sudo bash -c "echo $cc > /proc/sys/net/ipv4/tcp_congestion_control"
    for thr in 1 2 4 8 100; do
      run "${cc}_rtt_${rtt}_thr_${thr}_frac_${frac}" $thr $rtt $time --queue_size_factor=$frac
    done
  done
done

# set it back to what it was.
sudo bash -c "echo cubic > /proc/sys/net/ipv4/tcp_congestion_control"
