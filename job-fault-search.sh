#!/bin/bash
#PBS -N fault_search
#PBS -A NCGD0011
#PBS -l walltime=01:00:00
#PBS -q regular
#PBS -j oe
#PBS -k eod
#PBS -l select=1:ncpus=18

export TMPDIR=/glade/scratch/$USER/temp
mkdir -p $TMPDIR


source /glade/u/home/altuntas/.bash_profile
source /glade/u/home/altuntas/.bashrc

conda activate visualCaseGen
time python ./faulty_config_detector.py
