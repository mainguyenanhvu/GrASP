#!/bin/bash
#SBATCH -N 1
#SBATCH --ntasks-per-node=15
#SBATCH -p RM-small
#SBATCH -t 1:00:00
#SBATCH --job-name="scPDB Metrics Community Detection holo4k"
#SBATCH --mail-user=strobelm@umd.edu
#SBATCH --mail-type=ALL


module load anaconda3
conda activate # source /opt/packages/anaconda3/etc/profile.d/conda.sh
module load cuda/10.2
conda activate ../../pytorch_env
python3 multisite_metrics_quantile_test.py coach420 coach420/trained_model_1655980641.2358317/epoch_49 
