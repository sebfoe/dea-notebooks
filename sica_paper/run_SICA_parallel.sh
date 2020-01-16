#!/bin/bash
#PBS -P r78
#PBS -l walltime=8:00:00
#PBS -l mem=3TB
#PBS -l ncpus=32
#PBS -q megamem
#PBS -m abe
#PBS -M chad.burton@ga.gov.au

cd /g/data/r78/cb3058/dea-notebooks/ICE_project/
module use /g/data/v10/public/modules/modulefiles/
module load dea
module load parallel

parallel --delay 5 -a NMDB_tiffFiles.txt python3 0_SICA_parallel.py
wait;