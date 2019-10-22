# add any other args to the
name=$1
thr=$2
rtt=$3
time=$4
queue=$5
rest="${@:6}"

action_port=10000
frames_port=10001


# First check if the path to add is already part of the variable:
[[ ":$PYTHONPATH:" != *":`pwd`:"* ]] && PYTHONPATH="${PYTHONPATH}:`pwd`"

echo "Now running...."
sleep .1
echo "python3 scripts/run_exp.py -n=$name \
--results_dir=./results/ --rtt=$rtt --time=$time --thr=$thr --dump_video \
--action_port=${action_port} --frames_port=${frames_port} --queue_size=$queue $rest"

python3 scripts/run_exp.py -n=$name --results_dir=./results/ \
--rtt=$rtt --time=$time --thr=$thr --dump_video \
--action_port=${action_port} --frames_port=${frames_port} --queue_size=$queue $rest
