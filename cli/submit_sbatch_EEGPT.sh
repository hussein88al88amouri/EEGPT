#!/bin/bash
. /home/linah03/scratch/EEGPT/cli/functions.sh


#----------------------------------------------------------------------#
# ON COMPUTE CANADA
RootPath=/home/linah03/scratch/WorkSpace_EEGPT/EEGPT

scriptdir=/home/linah03/scratch/WorkSpace_EEGPT/EEGPT/cli
scriptname=sbatch_EEGPT.sh

daymonth=$(date +%d%m)
RootName=results_v${daymonth}

#dataset=THUSZ
#scheme=general

outputdir_=/home/linah03/scratch/WorkSpace_EEGPT/Results_EEGPT/${RootName}/${dataset}/${scheme}
LogRootPath=/home/linah03/scratch/WorkSpace_EEGPT/Results_EEGPT/${RootName}/${dataset}/${scheme}

LogsErrorsBasePath=${LogRootPath}/EOlogs
_logdir=${LogsErrorsBasePath}/out
_errordir=${LogsErrorsBasePath}/error
mkdir -p ${_logdir}
mkdir -p ${_errordir}


#----------------------------------------------------------------------#
outputdir=${outputdir_}/EEGPT_TUSZ
logdir=${_logdir}/EEGPT_TUSZ
errordir=${_errordir}/EEGPT_TUSZ
mkdir -p ${logdir}
mkdir -p ${errordir}
label=EEGPT_TUSZ
outfile=$(find_next_run ${logdir} ${label})
f="$(basename -- $outfile)"
mkdir -p ${errordir}/${label}
errorfile=${errordir}/${label}/${f}

echo sbatch --job-name=${label} --output=${outfile}.out --error=${errorfile}.out ${scriptdir}/${scriptname}

RES=$(sbatch --job-name=${label} --output=${outfile}.out --error=${errorfile}.out ${scriptdir}/${scriptname}
echo ${RES}
[ -e ${outfile}.id ] && rm ${outfile}.id
echo ${RES##* } > ${outfile}.id
#----------------------------------------------------------------------#