#! /usr/bin/env bash

set -eux
set -o pipefail

eval FA="~/.smbl/fa/Mycobacterium_tuberculosis.fa"
eval WGSIM="~/.smbl/bin/wgsim"

$WGSIM \
	-N 100 \
	-1 100 \
	-2 100 \
	$FA wgsim_1.fq wgsim_2.fq \
	> /dev/null


# 1) SE test, no contamination
rnftools wgsim2rnf \
	--fasta-index ${FA}.fai \
	--wgsim-fastq-1 wgsim_1.fq \
	--fastq _wgsim_rnf_se.fq \


# 2) PE test, no contamination
rnftools wgsim2rnf \
	--fasta-index ${FA}.fai \
	--wgsim-fastq-1 wgsim_1.fq \
	--wgsim-fastq-2 wgsim_2.fq \
	--fastq _wgsim_rnf_pe.fq \
