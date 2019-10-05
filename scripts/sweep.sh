
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
frac=$7
rest="${@:8}"

echo "Now running...."

echo "python3 scripts/run_exp.py -n=$name --model_cache_dir=/home/ubuntu/model_cache_dir/ \
--results_dir=/home/ubuntu/results/ --rtt=$rtt --time=$time --thr=$thr --dump_video \
--action_port=${action_port} --frames_port=${frames_port} --queue_size=$frac $rest"

python3 scripts/run_exp.py -n=$name --model_cache_dir=/home/ubuntu/model_cache_dir/ \
--results_dir=/home/ubuntu/results/ --rtt=$rtt --time=$time --thr=$thr --dump_video \
--action_port=${action_port} --frames_port=${frames_port} --queue_size=$frac $rest
}

time=180
frames_port=10000
action_port=10001

for cc in cubic ; do
  echo 'arc' | sudo -S bash -c "echo $cc > /proc/sys/net/ipv4/tcp_congestion_control"
  for rtt in 4 10; do
    for frac in 2 10; do
      for thr in 2 4; do
        run "${cc}_rtt_${rtt}_thr_${thr}_frac_${frac}" $thr $rtt $time $action_port $frames_port $frac --sps=60 &
        (( frames_port = frames_port + 2 ))
        (( action_port = action_port + 2 ))
      done
    done
    wait
  done
done

cc=ccp
echo 'arc' | sudo -S bash -c "echo ccp> /proc/sys/net/ipv4/tcp_congestion_control"
sudo python3 cc.py --cwnd=8000 &

for rtt in 4 10; do
  for frac in 2 10; do
    for thr in 2 4; do
      run "${cc}_rtt_${rtt}_thr_${thr}_frac_${frac}" $thr $rtt $time $action_port $frames_port $frac --sps=60 &
      (( frames_port = frames_port + 2 ))
      (( action_port = action_port + 2 ))
    done
  done
  wait
done

# set it back to what it was.
echo 'arc' | sudo -S bash -c "echo cubic > /proc/sys/net/ipv4/tcp_congestion_control"
