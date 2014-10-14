# Adapted for numpy/ma/cdms2 by convertcdms.py
# hdseofs.py

"""Huge Data Set Empirical Orthogonal Functions

 Get EOFs without the need to load the whole data set into memory
 Thus, we can compute them for HUGE data sets. The only limiting factor
 is the time needed to iterate over the whole dataset, but this
 is usually a problem of IO, not a problem of CPU
 for Gigabyte-sized data
"""

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
#
# Jon Saenz, Jesus Fernandez, June 2001, while at GKSS

import numpy as Numeric
import numpy.linalg as LinearAlgebra
import pyclimate.tools
import pyclimate.mctest
import pyclimate.pyclimateexcpt
import pyclimate.mvarstatools

LA=LinearAlgebra
NA=Numeric.newaxis
ptools=pyclimate.tools
pmvstools=pyclimate.mvarstatools
mctest=pyclimate.mctest
pex=pyclimate.pyclimateexcpt

class HDSEOFs:
  "Base class holding the common operations for both HDSEOF constructors"
  def Eigenvalues(self,svdsolver=LA.svd):
    "Eigenvalues of the covariance (correlation) matrix"
    if not self.ready:
      self.E,self.L,c=svdsolver(self.S)
      self.ready=1
    return self.L

  def _forceReady(self):
    if not self.ready:
      c=self.Eigenvalues()

  def VarianceFraction(self,svdfunc=LA.svd):
    "Total variance fraction accounted for each principal mode"
    l=self.Eigenvalues(svdfunc)
    return l/Numeric.add.reduce(l)

  def Eigenvectors(self,Neofs,pcscaling=0,
                   svdsolver=LA.svd):
    """EOFs, the eigenvectors of the covariance (correlation) matrix

    Arguments:

      'Neofs' -- Number of EOFs to return

    Optional arguments:

      'pcscaling' -- Kind of PC scaling. Defaults to 0, orthonormal EOFs. 
                     Set this parameter to 1 to obtain variance carrying 
                     orthogonal EOFs.

      'svdsolver' -- Routine to perform the SVD underlying decomposition.
                     Defaults to LinearAlgebra's singular_value_decomposition.
    """
    if not self.ready:
      self.E,self.L,c=svdsolver(self.S)
      self.ready=1
    if pcscaling == 0:
      return ptools.deunshape(
        self.E[:,:Neofs], 
        self.originalshape+(Neofs,)
      )
    if pcscaling == 1:
      return ptools.deunshape(
        self.E[:,:Neofs] * Numeric.sqrt(self.L)[NA,:Neofs], 
        self.originalshape+(Neofs,)
      )
    else:
      raise pex.ScalingError(pcscaling) 

  def Average(self):
    "Time average of the original field"
    return ptools.deunshape(self.average,self.originalshape)

  def ScatteringMeasure(self):
    "Covariance or correlation matrix depending on the constructor"
    return self.S

  def PCs(self,Neofs,iterator,irecord,pcscaling=0):
    "Principal components"
    self._forceReady()
    anomaly=Numeric.ravel(iterator[irecord])-self.average
    if pcscaling == 0:
      return Numeric.add.reduce(anomaly[:,NA]*self.E[:,:Neofs])
    if pcscaling == 1:
      return Numeric.ravel(
        Numeric.add.reduce(anomaly[:,NA]*self.E[:,:Neofs]) /
        Numeric.sqrt(self.L)[NA,:Neofs]
      )
    else:
      raise pex.ScalingError(pcscaling)

  def WholePCs(self,Neofs,iterator,pcscaling=0):
    "Principal components for all records"
    rval=Numeric.zeros((self.records,Neofs),'d')
    for i in self.therecords:
      rval[i,:]=self.PCs(Neofs,iterator,i,pcscaling)
    return rval

  def NorthTest(self):
    "North error bars"
    factor=Numeric.sqrt(2./self.records)
    errors=Numeric.array(self.Eigenvalues())*factor
    return errors

  def MCTest(self,Neofs,iterator,subsamples,length):
    "Monte Carlo test on the congruence"
    theccoefs=Numeric.zeros((subsamples,)+(Neofs,),'d')
    for isample in xrange(subsamples):
      subslist=mctest.getrandomsubsample(length,self.records)
      he=DIHDSEOFs(iterator,therecords=subslist)
      he._forceReady()
      self._forceReady()
      theccoefs[isample,:]=pmvstools.congruence(he.E[:,:Neofs],self.E[:,:Neofs])
    return theccoefs

class SIHDSEOFs(HDSEOFs):
  """Single iteration huge data set EOFs

  Covariance matrix is obtained iterating once over the dataset.
  """
  def __init__(self,iterator,tcode='d',therecords=None,corrmatrix=0):
    """Constructor for the class 'SIHDSEOFs'

    Arguments:

      'iterator' -- Indexable object (e.g. Numpy array, nciterator object, ...)
                    to decompose into EOFs

    Optional arguments:

      'tcode' -- Numeric typecode for the internal computations. 
                 Defaults to 'float64'.

      'therecords' -- List of records to be taken. Defaults to the 
                      whole data set.

      'corrmatrix' -- Bit parameter indicating wether covariance matrix 
                      EOFs are computed (default, 0) or correlation matrix ones
                      (corrmatrix=1).
    """
    self.originalshape=iterator[0].shape
    self.ashape=Numeric.array(self.originalshape,'i')
    if not therecords:
      self.records=len(iterator)
      self.therecords=range(self.records)
    else:
      self.records=len(therecords)
      self.therecords=therecords
    self.items=Numeric.multiply.reduce(self.ashape)
    self.typecode=tcode
    self.corrmatrix=corrmatrix
    self.average=Numeric.zeros((self.items,),self.typecode)
    self.S=Numeric.zeros((self.items,self.items),self.typecode)
    for i in self.therecords:
      field=Numeric.ravel(iterator[i]) 
      Numeric.add(self.average,field,self.average)
      Numeric.add(self.S,Numeric.multiply.outer(field,field),self.S)
    ##################################################
    # Force the use of float64 in S
    #################################################
    Numeric.multiply(self.average,1.0/self.records,self.average).astype(self.typecode)
    Numeric.multiply(self.S,1.0/float(self.records),self.S)
    Numeric.add(self.S,-Numeric.multiply.outer(self.average,self.average),self.S)
    if self.corrmatrix:
      stds=Numeric.diagonal(self.S)
      stds=Numeric.sqrt(stds)
      Numeric.multiply(self.S,1./Numeric.multiply.outer(stds,stds),self.S)
    self.ready=0


class DIHDSEOFs(HDSEOFs):
  """Double iteration huge data set EOFs

  Covariance matrix is obtained iterating twice over the dataset.
  """
  def __init__(self,iterator,tcode='d',therecords=None,corrmatrix=0):
    """Constructor for the class 'DIHDSEOFs'

    Arguments:

      'iterator' -- Indexable object (e.g. Numpy array, nciterator object, ...)
                    to decompose into EOFs

    Optional arguments:

      'tcode' -- Numeric typecode for the internal computations. 
                 Defaults to 'float64'.

      'therecords' -- List of records to be taken. Defaults to the 
                      whole data set.

      'corrmatrix' -- Bit parameter indicating wether covariance matrix 
                      EOFs are computed (default, 0) or correlation matrix ones
                      (corrmatrix=1).
    """
    self.originalshape=iterator[0].shape
    self.ashape=Numeric.array(self.originalshape,'i')
    self.records=len(iterator)
    if not therecords:
      self.records=len(iterator)
      self.therecords=range(self.records)
    else:
      self.records=len(therecords)
      self.therecords=therecords
    self.items=Numeric.multiply.reduce(self.ashape)
    self.typecode=tcode
    self.corrmatrix=corrmatrix
    self.average=Numeric.zeros((self.items,),self.typecode)
    for i in self.therecords:
      self.average=self.average+Numeric.ravel(iterator[i])
    self.average=(self.average/self.records).astype(self.typecode)
    self.S=Numeric.zeros((self.items,self.items),'d')
    for i in self.therecords:
      residual=Numeric.ravel(iterator[i])-self.average
      Numeric.add(self.S,Numeric.multiply.outer(residual,residual),self.S)
    ##################################################
    # Force the use of float64 in S
    #################################################
    Numeric.multiply(self.S,1./float(self.records),self.S)
    if self.corrmatrix:
      stds=Numeric.diagonal(self.S)
      stds=Numeric.sqrt(stds)
      Numeric.multiply(self.S,1./Numeric.multiply.outer(stds,stds),self.S)
    self.ready=0

