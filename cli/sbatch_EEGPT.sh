#!/bin/bash
#SBATCH --gpus-per-node=v100l:1
#SBATCH --mem=128G
#SBATCH --cpus-per-task=4
#SBATCH --time=120:00:00

module purge
module load cuda cudnn

echo activating and exporting python environement
# hpc machine
#source /home/linah03/scratch/WorkSpace_EEGPT/EEGPT_env/bin/activate
#export PATH=/home/linah03/scratch/WorkSpace_EEGPT/EEGPT_env/bin:$PATH
# local machine
source /home/hussein/WorSpace/LBW/EEGPT_venv/bin/activate
export PATH=/home/hussein/WorSpace/LBW/EEGPT_venv/bin:$PATH

echo 
nvidia-smi
echo

echo 
which python
echo 


#----------------------------------------------------------------------#

echo Running ...
echo '>>>'
echo
echo '>>>'
echo ''


#----------------------------------------------------------------------#

# cd /home/linah03/scratch/WorkSpace_EEGPT/EEGPT/downstream_tueg
cd /home/hussein/WorSpace/LBW/EEGPT/downstream_tueg

#----------------------------------------------------------------------#


# export MASTER_PORT=${MASTER_PORT:-12320}  # You should set the same master_port in all the nodes
export MASTER_PORT=$((12000 + $RANDOM % 20000))

# official train/test splits. valid numbers: 1, 2, 3
SPLIT=${SPLIT:-1}

N_NODES=${N_NODES:-1}  # Number of nodes
GPUS_PER_NODE=${GPUS_PER_NODE:-2}  # Number of GPUs in each node
SRUN_ARGS=${SRUN_ARGS:-""}  # Other slurm task args
PY_ARGS=${@:2}  # Other training args

output_dir="${1:-./checkpoints_TUEV/finetune_tuev_eegpt/}"
log_dir="${2:-./log/finetune_tuev_eegpt}"
finetune="${3:-../checkpoint/eegpt_mcae_58chs_4s_large4E.ckpt}"
dataset="${4:-TUEV}"

# Please refer to `run_class_finetuning_EEGPT_change_tuev.py` for the meaning of the following hyperreferences
CUDA_VISIBLE_DEVICES=4,5 OMP_NUM_THREADS=1 python -m torch.distributed.run --nproc_per_node=${GPUS_PER_NODE} \
        --master_port ${MASTER_PORT} --nnodes=${N_NODES} --node_rank=0 --master_addr="localhost" \
        run_class_finetuning_EEGPT_change_tuev.py \
        --output_dir ${output_dir} \
        --log_dir  ${log_dir} \
        --model EEGPT \
        --finetune ${finetune} \
        --weight_decay 0.05 \
        --batch_size 400\
        --lr 5e-4 \
        --update_freq 1 \
        --warmup_epochs 5 \
        --epochs 30 \
        --layer_decay 0.65 \
        --drop_path 0.2 \
        --dist_eval \
        --save_ckpt_freq 5 \
        --disable_rel_pos_bias \
        --abs_pos_emb \
        --dataset ${dataset} \
        --enable_deepspeed \
        --seed 0
        
#----------------------------------------------------------------------#