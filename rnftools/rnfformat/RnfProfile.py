class RnfProfile:
	def __init__(self,
				prefix_width=0,
				read_id_width=8,
				genome_id_width=1,
				chr_id_width=2,
				coor_width=9,
				read_name=None
			):
		self.prefix_width=prefix_width
		self.read_id_width=read_id_width
		self.genome_id_width=genome_id_width
		self.chr_id_width=chr_id_width
		self.coor_width=coor_width

		if read_name is not None:
			self.load(read_name)

	def __str__(self):
		return str(list([
				self.prefix_width,
				self.read_id_width,
				self.genome_id_width,
				self.chr_id_width,
				self.coor_width,
			]))
		#return "{{prefix_width:{},read_id_width:{},genome_id_width:{},chr_id_width:{},coor_width:{}}}".format(
		#		self.prefix_width,
		#		self.read_id_width,
		#		self.genome_id_width,
		#		self.chr_id_width,
		#		self.coor_width,
		#	)

	def combine(rnf_profile):
		self.prefix_width=max(self.prefix_width,rnf_profile.prefix_width)
		self.read_id_width=max(self.read_id_width,rnf_profile.read_id_width)
		self.genome_id_width=max(self.genome_id_width,rnf_profile.genome_id_width)
		self.chr_id_width=max(self.chr_id_width,rnf_profile.chr_id_width)
		self.coor_width=max(self.coor_width,rnf_profile.coor_width)

	def load(self,read_name):
		self.prefix_width=0
		self.read_id_width=0
		self.genome_id_width=0
		self.chr_id_width=0
		self.coor_width=0

		parts=read_name.split("__")
		self.prefix_width=len(parts[0])
		self.read_id_width=len(parts[1])

		segments=parts[2][1:-1].split("),(")
		for segment in segments:
			int_widths=list(map(len,segment.split(",")))
			self.genome_id_width=max(self.genome_id_width,int_widths[0])
			self.chr_id_width=max(self.chr_id_width,int_widths[1])
			self.coor_width=max(self.coor_width,int_widths[2],int_widths[3])

	def apply(self,read_name,read_tuple_id=None):
		parts=read_name.split("__")
		parts[0]=self._fill_right(parts[0],"-",self.prefix_width)
		if read_tuple_id is not None:
			parts[1]="{:x}".format(read_tuple_id)
		parts[1]=self._fill_left(parts[1],"0",self.read_id_width)
		return "__".join(parts)

	def check(self,read_name):
		parts=read_name.split("__")

		if len(parts[0])!= self.prefix_width or len(parts[1])!=self.read_id_width:
			return False

		segments=parts[2][1:-1].split("),(")
		for segment in segments:
			int_widths=list(map(len,segment.split(",")))
			if self.genome_id_width !=int_widths[0]:
				return False
			if self.chr_id_width != int_widths[1]:
				return False
			if self.coor_width!=int_widths[3] or self.coor_width!=int_widths[4]:
				return False

		return True

	@staticmethod
	def _fill_left(string,character,length):
		return (length-len(string))*character + string

	@staticmethod
	def _fill_right(string,character,length):
		return string + (length-len(string))*character
