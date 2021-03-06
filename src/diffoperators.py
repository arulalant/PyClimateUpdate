# Adapted for numpy/ma/cdms2 by convertcdms.py
# diffoperators.py

"""Differential operators on the sphere

"""
# 
# Copyright (C) 2000, Jon Saenz, Jesus Fernandez and Juan Zubillaga
# 
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation, version 2.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
 
import numpy
import math,sys

def deg2rad(d):
	"Converts degrees to radians"
	return math.pi*d/180.
 
# Gradient of a scalar 2-D horizontal field
class HGRADIENT:
	"Horizontal gradient operator"
	def __init__(self,lats,lons,asdegrees=1,PBlon=0):
		"""Constructor for the class HGRADIENT

		Arguments:

			'lats' -- Array of latitudes

			'lons' -- Array of longitudes

		Optional Arguments:

			'asdegrees' -- Bit parameter indicating wether
				'lats' and 'lons' are passed as degrees
				(default, 1) or not (radians, 0).

			'PBlon' -- Bit parameter indicating the
				use of periodic boundary conditions in
				longitude. Defaults to 0 (no PB).
		"""
		# These are the latitude/longitude increments
		if asdegrees:
			self.dlon=deg2rad(lons[1]-lons[0])
			self.dlat=deg2rad(lats[1]-lats[0])
			# This array holds the cosine of the latitudes
			self.clats=numpy.cos(deg2rad(lats))
		else:
			self.dlon=lons[1]-lons[0]
			self.dlat=lats[1]-lats[0]
			# This array holds the cosine of the latitudes
			self.clats=numpy.cos(lats)
		# Periodic boundaries in latitude/longitude
		self.PBlon=PBlon

	def hgradient(self,phi,R=6.37e6):
		"""Horizontal gradient

		Arguments:

			'phi' -- A field (NumPy array) defined in 'lats', 
				'lons'

		Optional Arguments:

			'R' -- The radius of the sphere. (Defaults to the
				radius of the Earth 6.37e6)
		"""
		# Centered differences for each of the fields
		u=numpy.zeros(phi.shape,numpy.float64)
		v=numpy.zeros(phi.shape,numpy.float64)
		# Longitudinal directions
		u[...,1:-1]=phi[...,2:]-phi[...,:-2]
		if not self.PBlon:
			u[...,0]=2*(phi[...,1]-phi[...,0])
			u[...,-1]=2*(phi[...,-1]-phi[...,-2])
		else:
			u[...,0]=(phi[...,1]-phi[...,-1])
			u[...,-1]=(phi[...,0]-phi[...,-2])
		# Meridional directions
		v[...,1:-1,:]=phi[...,2:,:]-phi[...,:-2,:]
		v[...,0,:]=2*(phi[...,1,:]-phi[...,0,:])
		v[...,-1,:]=2*(phi[...,-1,:]-phi[...,-2,:])
		# Divide by the increments
		u=u/(2.*self.dlon*R)
		v=v/(2.*self.dlat*R)
		# Now, divide u by cos(lat)
		u=u/self.clats[:,numpy.newaxis]
		return (u,v)


# Get the divergence of a vectorial 2-D field
class HDIVERGENCE:
	"Divergence operator"
	def __init__(self,lats,lons,asdegrees=1,PBlon=0):
		"""Constructor for the class HDIVERGENCE

		Arguments:

			'lats' -- Array of latitudes

			'lons' -- Array of longitudes

		Optional Arguments:

			'asdegrees' -- Bit parameter indicating wether
				'lats' and 'lons' are passed as degrees
				(default, 1) or not (radians, 0).

			'PBlon' -- Bit parameter indicating the
				use of periodic boundary conditions in
				longitude. Defaults to 0 (no PB).
                """
		# These are the latitude/longitude increments
		if asdegrees:
			self.dlon=deg2rad(lons[1]-lons[0])
			self.dlat=deg2rad(lats[1]-lats[0])
			# This array holds the cosine of the latitudes
			self.clats=numpy.cos(deg2rad(lats))
		else:
			self.dlon=lons[1]-lons[0]
			self.dlat=lats[1]-lats[0]
			# This array holds the cosine of the latitudes
			self.clats=numpy.cos(lats)
		# Periodic boundaries in latitude/longitude
		self.PBlon=PBlon

	def hdivergence(self,u,v,R=6.37e6):
		"""Horizontal field divergence 

		Arguments:

			'u' -- X component of a field (NumPy array) defined 
				in 'lats', 'lons'

			'v' -- Y component of a field (NumPy array) defined 
				in 'lats', 'lons'

		Optional Arguments:

			'R' -- The radius of the sphere. (Defaults to the
				radius of the Earth 6.37e6)
		"""
		# Multiply each row of the v component by cosine(lat)
		dummy=numpy.array(v)*self.clats[:,numpy.newaxis]
		# Centered differences for each of the fields
		cdifu=numpy.zeros(u.shape,numpy.float64)
		cdifv=numpy.zeros(v.shape,numpy.float64)
		# Longitudinal directions
		cdifu[...,1:-1]=u[...,2:]-u[...,:-2]
		if not self.PBlon:
			cdifu[...,0]=2*(u[...,1]-u[...,0])
			cdifu[...,-1]=2*(u[...,-1]-u[...,-2])
		else:
			cdifu[...,0]=(u[...,1]-u[...,-1])
			cdifu[...,-1]=(u[...,0]-u[...,-2])
		# Meridional directions
		cdifv[...,1:-1,:]=dummy[...,2:,:]-dummy[...,:-2,:]
		cdifv[...,0,:]=2*(dummy[...,1,:]-dummy[...,0,:])
		cdifv[...,-1,:]=2*(dummy[...,-1,:]-dummy[...,-2,:])
		# Divide by the increments
		cdifu=cdifu/2./self.dlon
		cdifv=cdifv/2./self.dlat
		# Now, divide by R*cos(lat)
		dummy=cdifu+cdifv
		dummy=dummy/self.clats[:,numpy.newaxis]
		dummy=dummy/R
		return dummy

class VCURL:
	"Vertical component of the curl vector"
	def __init__(self,lats,lons,asdegrees=1,PBlon=0):
		"""Constructor for the class VCURL 

		Arguments:

			'lats' -- Array of latitudes

			'lons' -- Array of longitudes

		Optional Arguments:

			'asdegrees' -- Bit parameter indicating wether
				'lats' and 'lons' are passed as degrees
				(default, 1) or not (radians, 0).

			'PBlon' -- Bit parameter indicating the
				use of periodic boundary conditions in
				longitude. Defaults to 0 (no PB).
                """
		# These are the latitude/longitude increments
		if asdegrees:
			self.dlon=deg2rad(lons[1]-lons[0])
			self.dlat=deg2rad(lats[1]-lats[0])
			# This array holds the cosine of the latitudes
			self.clats=numpy.cos(deg2rad(lats))
		else:
			self.dlon=lons[1]-lons[0]
			self.dlat=lats[1]-lats[0]
			# This array holds the cosine of the latitudes
			self.clats=numpy.cos(lats)
		# Periodic boundaries in latitude/longitude
		self.PBlon=PBlon

	def vcurl(self,u,v,R=6.37e6):
		"""Vertical component of the curl verctor 

		Arguments:

			'u' -- X component of a field (NumPy array) defined 
				in 'lats', 'lons'

			'v' -- Y component of a field (NumPy array) defined 
				in 'lats', 'lons'

		Optional Arguments:

			'R' -- The radius of the sphere. (Defaults to the
				radius of the Earth 6.37e6)
		"""
		# Multiply each row of the U component by cosine(lat)
		dummy=numpy.array(u)*self.clats[:,numpy.newaxis]
		# Centered differences for each of the fields
		cdifu=numpy.zeros(u.shape,numpy.float64)
		cdifv=numpy.zeros(v.shape,numpy.float64)
		# Longitudinal directions
		cdifv[...,1:-1]=v[...,2:]-v[...,:-2]
		if not self.PBlon:
			cdifv[...,0]=2*(v[...,1]-v[...,0])
			cdifv[...,-1]=2*(v[...,-1]-v[...,-2])
		else:
			cdifv[...,0]=(v[...,1]-v[...,-1])
			cdifv[...,-1]=(v[...,0]-v[...,-2])
		# Meridional directions
		cdifu[...,1:-1,:]=dummy[...,2:,:]-dummy[...,:-2,:]
		cdifu[...,0,:]=2*(dummy[...,1,:]-dummy[...,0,:])
		cdifu[...,-1,:]=2*(dummy[...,-1,:]-dummy[...,-2,:])
		# Divide by the increments
		cdifu=cdifu/2./self.dlat
		cdifv=cdifv/2./self.dlon
		# Now, divide by R*cos(lat)
		dummy=cdifv-cdifu
		dummy=dummy/self.clats[:,numpy.newaxis]
		dummy=dummy/R
		return dummy
