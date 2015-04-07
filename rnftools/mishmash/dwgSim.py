import rnftools
from .source import Source

import os
import smbl
import snakemake
import re

#
# AUXILIARY FUNCTIONS
#

# TODO
# - check parameters
#
#

#
# THERE IS A BUG IN DWGSIM DOCUMENTATION -- it is 1-based
#
#

class DwgSim(Source):
	"""Class for DwgSim.

	Single-end reads and pair-end reads simulations are supported. For pair-end simulations,
	ends can have different lengths.

	Format of read names produced by DwgSim
	^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

	.. code-block::

		(.*)_([0-9]+)_([0-9]+)_([01])_([01])_([01])_([01])_([0-9]+):([0-9]+):([0-9]+)_([0-9]+):([0-9]+):([0-9]+)_(([0-9abcdef])+)


	1)  contig name (chromsome name)
	2)  start end 1 (one-based)
	3)  start end 2 (one-based)
	4)  strand end 1 (0 - forward, 1 - reverse)
	5)  strand end 2 (0 - forward, 1 - reverse)
	6)  random read end 1 (0 - from the mutated reference, 1 - random)
	7)  random read end 2 (0 - from the mutated reference, 1 - random)
	8)  number of sequencing errors end 1 (color errors for colorspace)
	9)  number of SNPs end 1
	10) number of indels end 1
	11) number of sequencing errors end 2 (color errors for colorspace)
	12) number of SNPs end 2
	13) number of indels end 2
	14) read number (unique within a given contig/chromsome)

	Args:
		fa (str): File name of the genome from which reads are created (FASTA file).
		coverage (float): Average coverage of the genome (if number_of_reads specified, then it must be equal to zero).
		number_of_reads (int): Number of reads (if coverage specified, then it must be equal to zero).
		read_length_1 (int): Length of the first read.
		read_length_2 (int): Length of the second read (if zero, then single-end reads are created).
		other_params (str): Other parameters which are used on commandline.
		distance (int): Mean inner distance between ends.
		distance_deviation (int): Deviation of inner distances between ends.
		rng_seed (int): Seed for simulator's random number generator.
		haploid_mode (bools): Simulate reads in haploid mode.
		error_rate_1 (float): Base error rate in the first read (sequencing errors).
		error_rate_2 (float): Base error rate in the second read (sequencing errors).
		mutation_rate (float): Mutation rate.
		indels (float): Rate of indels in mutations.
		prob_indel_ext (float): Probability that an indel is extended.

	Raises:
		ValueError
	"""

	#TODO:estimate_unknown_values=False,
	def __init__(self,
				fasta,
				coverage=0,
				number_of_reads=0,
				read_length_1=100,
				read_length_2=0,
				other_params="",
				distance=500,
				distance_deviation=50.0,
				rng_seed=1,
				haploid_mode=False,
				error_rate_1=0.020,
				error_rate_2=0.020,
				mutation_rate=0.001,
				indels=0.15,
				prob_indel_ext=0.3,
			):

		if read_length_2==0:
			ends = 1
		else:
			ends = 2
			self.distance=distance
			self.distance_deviation=distance_deviation
		
		super().__init__(
				fasta=fasta,
				reads_in_tuple=ends,
				rng_seed=rng_seed,
			)

		self.read_length_1=read_length_1
		self.read_length_2=read_length_2
		self.other_params=other_params

		if coverage*number_of_reads!=0:
			smbl.messages.error("coverage or number_of_reads must be equal to zero",program="RNFtools",subprogram="MIShmash",exception=ValueError)

		self.number_of_reads=number_of_reads
		self.coverage=coverage

		self.haploid_mode=haploid_mode
		self.error_rate_1=error_rate_1
		self.error_rate_2=error_rate_2
		self.mutation_rate=mutation_rate
		self.indels=indels
		self.prob_indel_ext=prob_indel_ext

		self.dwg_prefix=os.path.join(
			self.get_dir(),
			"tmp.{}".format(self.source_id)
		)


	def get_input(self):
		return [
				smbl.prog.DWGSIM,
				self._fa_fn,
				self._fai_fn,
			]

	def get_output(self):
		return 	[
				self.dwg_prefix+".bwa.read1.fastq",
				self.dwg_prefix+".bwa.read2.fastq",
				self.dwg_prefix+".bfast.fastq",
				self.dwg_prefix+".mutations.vcf",
				self.dwg_prefix+".mutations.txt",
				self._fq_fn
			]

	def create_fq(self):
		if self.number_of_reads == 0:
			genome_size=os.stat(self._fa_fn).st_size
			self.number_of_reads=int(self.coverage*genome_size/(self.read_length_1+self.read_length_2))


		if self._reads_in_tuple==2:
			paired_params="-d {dist} -s {dist_dev}".format(
					dist=self.distance,
					dist_dev=self.distance_deviation,
				)
		else:
			paired_params=""

		snakemake.shell("""
				"{dwgsim}" \
				-1 {rlen1} \
				-2 {rlen2} \
				-z {rng_seed} \
				-y 0 \
				-N {nb} \
				-e {error_rate_1} \
				-E {error_rate_2} \
				-r {mutation_rate} \
				-R {indels} \
				-X {prob_indel_ext} \
				{haploid} \
				{paired_params} \
				{other_params} \
				"{fa}" \
				"{pref}" \
				> /dev/null
			""".format(
				dwgsim=smbl.prog.DWGSIM,
				fa=self._fa_fn,
				pref=self.dwg_prefix,
				nb=self.number_of_reads,
				rlen1=self.read_length_1,
				rlen2=self.read_length_2,
				other_params=self.other_params,
				paired_params=paired_params,
				rng_seed=self._rng_seed,
				haploid="-h" if self.haploid_mode else "",
				error_rate_1=self.error_rate_1,
				error_rate_2=self.error_rate_2,
				mutation_rate=self.mutation_rate,
				indels=self.indels,
				prob_indel_ext=self.prob_indel_ext,
			)
		)
		self.recode_dwgsim_reads(
			old_fq=self.dwg_prefix+".bfast.fastq",
		)

	def recode_dwgsim_reads(self,old_fq,number_of_reads=10**9):
		dwgsim_pattern = re.compile('@(.*)_([0-9]+)_([0-9]+)_([01])_([01])_([01])_([01])_([0-9]+):([0-9]+):([0-9]+)_([0-9]+):([0-9]+):([0-9]+)_(([0-9abcdef])+)')
		"""
			DWGSIM read name format

		1)  contig name (chromsome name)
		2)  start end 1 (one-based)
		3)  start end 2 (one-based)
		4)  strand end 1 (0 - forward, 1 - reverse)
		5)  strand end 2 (0 - forward, 1 - reverse)
		6)  random read end 1 (0 - from the mutated reference, 1 - random)
		7)  random read end 2 (0 - from the mutated reference, 1 - random)
		8)  number of sequencing errors end 1 (color errors for colorspace)
		9)  number of SNPs end 1
		10) number of indels end 1
		11) number of sequencing errors end 2 (color errors for colorspace)
		12) number of SNPs end 2
		13) number of indels end 2
		14) read number (unique within a given contig/chromsome)
		"""
		
		max_seq_len=0

		self.load_fai()
		id_str_size=len(format(number_of_reads,'x'))

		rn_formatter = rnftools.rnfformat.RnFormatter(
				id_str_size=id_str_size,
				source_str_size=2,
				chr_str_size=self.chr_str_size,
				pos_str_size=self.pos_str_size
			)

		#one or two ends?
		single_end=os.stat(self.dwg_prefix+".bwa.read2.fastq").st_size==0

		# parsing FQ file
		last_new_read_name=""
		read_id=0
		with open(old_fq,"r+") as f1:
			with open(self._fq_fn,"w+") as f2:
				i=0
				for line in f1:
					if i%4==0:
						(line1,line2,line3,line4)=("","","","")

						m = dwgsim_pattern.search(line)
						if m is None:
							smbl.messages.error("Read '{}' was not by DwgSim.".format(line[1:]),program="RNFtools",subprogram="MIShmash",exception=ValueError)

						contig_name     = m.group(1)
						start_1         = int(m.group(2))
						start_2         = int(m.group(3))
						direction_1     = "F" if int(m.group(4))==0 else "R"
						direction_2     = "F" if int(m.group(5))==0 else "R"
						random_1        = bool(m.group(6))
						random_2        = bool(m.group(7))
						seq_err_1       = int(m.group(8))
						snp_1           = int(m.group(9))
						indels_1        = int(m.group(10))
						seq_err_2       = int(m.group(11))
						snp_2           = int(m.group(12))
						indels_2        = int(m.group(13))
						read_id_dwg     = int(m.group(14),16)

						chr_id = self.dict_chr_ids[contig_name] if self.dict_chr_ids!={} else "0"

					elif i%4==1:
						line2=line
						read_length=len(line2.strip())

						segment1=rnftools.rnfformat.Segment(
								source=self.source_id,
								chr=chr_id,
								direction=direction_1,
								left=start_1,
								right=0
							)

						segment2=rnftools.rnfformat.Segment(
								source=self.source_id,
								chr=chr_id,
								direction=direction_2,
								left=start_2,
								right=0
							)
						
						if single_end:
							read = rnftools.rnfformat.Read(segments=[segment1],read_id=read_id+1,suffix="[single-end,dwgsim]")
						else:
							read = rnftools.rnfformat.Read(segments=[segment1,segment2],read_id=read_id+1,suffix="[pair-end,dwgsim]")
						new_read_name = rn_formatter.process_read(read)

						if single_end:
							ends_suffix=""
							read_id+=1
						else:
							if last_new_read_name!=new_read_name:
								ends_suffix="/1"
							else:
								ends_suffix="/2"
								read_id+=1

						line1="".join(["@",new_read_name,ends_suffix,os.linesep])
						last_new_read_name=new_read_name

					elif i%4==2:
						line3=line

					else:
						line4=line

						f2.write(line1)
						f2.write(line2)
						f2.write(line3)
						f2.write(line4)

					i+=1
