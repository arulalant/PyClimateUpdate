# Adapted for numpy/ma/cdms2 by convertcdms.py
# analog.py 

"""Euclidean analog search

  This module looks for analog patterns in a library dataset. Analogs are
  selected according to a minimal Euclidean distance in the search space.
  Two different search spaces have been implemented to date. There are 
  classes to search for analogs in a PCA truncated space and in a CCA
  truncated one. Further details can be found in

  J. Fernandez and J. Saenz 
  *Analog search in CCA space*.
  (Submitted to Climate Research)

  *Contact the authors for a draft copy.*
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

# jff20010621

import numpy
import pyclimate.tools
import pyclimate.mvarstatools
import pyclimate.svdeofs
import pyclimate.bpcca
import pyclimate.pyclimateexcpt
import math, os

ptools = pyclimate.tools
pmvstools = pyclimate.mvarstatools
pex = pyclimate.pyclimateexcpt
def mm(array1,array2):
  return numpy.matrix(array1)*numpy.matrix(array2)
NA = numpy.newaxis

def get_weights(distarray,weightexp):
  """Returns the weight values for each analog 

  The weights are normalized so the sum of them all is 1. The
  weights are inversely proportional to the 'weightexp' power 
  of the distance.
  
  Arguments:

    'distarray' -- Array with the distances to the 'smoothing' (see the class
                   'ANALOGSelector') nearest analogs

    'weightexp' -- The exponent of the weights.
  """
  rval = distarray ** weightexp
  rval = 1./rval
  rval = rval / numpy.add.reduce(rval,1)[:,NA]
  return rval 

class __ANALOG:            
  """Base class for the analog search. It cannot be instanciated!

  Any class derived from this one _MUST_ define at least the
  following attributes:

  'dataset' -- The dataset into which the analog is to be searched.

  'originalshape' -- The original shape of the dataset.

  'P' -- Coordinates in a given metric (say Euclidean-EOF-space) of the dataset.

  and the method:

  'getCoords(pattern)' -- which gives the coordinates of 'pattern' in a given metric. 
  """       
  def findAnalogRecord(self, field):
    "Returns the index in 'dataset' of the analog for the field 'field'"
    thecoords = self.getCoords(field) 
    sqres = thecoords[NA,:] - self.P
    sqres = sqres * sqres
    sqres = numpy.add.reduce(sqres,1)
    theindex = numpy.argmin(sqres)
    self.sqres = sqres[theindex]
    return theindex

  def findNAnalogRecords(self, field, n):
    "Returns the 'n' indices in 'dataset' of the 'n' nearest analogs for 'field'"
    thecoords = self.getCoords(field) 
    sqres = thecoords[NA,:] - self.P
    sqres = sqres * sqres
    sqres = numpy.add.reduce(sqres,1)
    theindices = numpy.argsort(sqres).tolist()[:n] 
    self.sqres = numpy.array(numpy.take(sqres, theindices))
    return theindices

  def __len__(self):
    "Number of records in the library 'dataset'"
    return len(self.dataset)

  def __getitem__(self, i):
    "Slide access to the library 'dataset'"
    return self.dataset[i]

class EOFANALOG(__ANALOG):
  "Analog search in the PCA space"
  def __init__(self, dataset, neofs=None, pcscaling=1):
    """Constructor for a PCA-space search

    Arguments:

      'dataset' -- NumPy array with the library dataset 
                   (time is _first_ dimension)

      'neofs' -- Number of EOFs to retain. This sets the degrees of 
                 freedom of the search space. Defaults to the number of
                 EOFs accounting for a 70% of the total variance.

      'pcscaling' -- Set the scaling of the EOFs. 0 means orthonormal EOFs.
                     1 means standardized PCs. Defaults to 1.
    """
    self.dataset = dataset
    self.originalshape = dataset[0].shape
    self.pcscaling = pcscaling
    self.EOFobj = pyclimate.svdeofs.SVDEOFs(self.dataset)
    self.neofs = neofs or ptools.getneofs(self.EOFobj.lambdas)
    self.P = self.EOFobj.pcs(self.pcscaling)[:,:self.neofs]
    self.L = self.EOFobj.lambdas[:self.neofs]
    self.E = self.EOFobj.eofs(self.pcscaling)[...,:self.neofs]
    self.flatE = numpy.array(self.E[...,:])
    self.flatE.shape = (self.EOFobj.channels, self.neofs)

  def getCoords(self, field):
    "Returns the coordinates of 'field' in the PCA space"
    if field.shape != self.originalshape:
      raise pex.ANALOGNoMatchingShape(field.shape, self.originalshape)
    field = numpy.ravel(field)
    field.shape = (1, len(field))
    if self.pcscaling == 0:
      return numpy.ravel(mm(field, self.flatE)) 
    elif self.pcscaling == 1:
      inverseEtranspose = self.flatE / self.L[NA,:]
      return numpy.ravel(mm(field, inverseEtranspose))
#######################################
# Backward compatibility definitions  #
# Do not use!                         #
#######################################
  eofCoords = getCoords               #
#######################################
 
class CCAANALOG(__ANALOG):
  "Analog search in the CCA space"
  def __init__(self, dataset, theotherdataset, neofs=None, spherized=1):
    """Constructor for a CCA-space search

    Arguments:

      'dataset' -- NumPy array with the library dataset 
                   (time is _first_ dimension)

      'theotherdataset' -- Another array with the complementary field. This is
                           actually the target field to be reconstructed.

      'neofs' -- Tuple with the number of EOFs to retain in each field in the 
                 PCA prefilter for the CCA. This sets the degrees of 
                 freedom of the search space (these are the minimum of this tuple). 
                 Defaults to the number of EOFs accounting for a 70% of the 
                 total variance in each field.
      'spherized' -- Bit indicating if the search in performed in an 
                     spherized space (1) or an inverse correlation scaled
                     one (0). Default: 1
    """
    self.dataset = dataset
    self.originalshape = dataset[0].shape
    self.CCAobj = pyclimate.bpcca.BPCCA(self.dataset, theotherdataset, neofs)
    self.P = self.CCAobj.leftExpCoeffs()
    self.spherized = spherized
    if not self.spherized:
      self.P = self.P * (self.CCAobj.corr**2)[NA,:]
    self.retainedeofs = (self.CCAobj.n1,self.CCAobj.n2)

  def getCoords(self, field):
    "Returns the coordinates of 'field' in the CCA space"
    if field.shape != self.originalshape:
      raise pex.ANALOGNoMatchingShape(field.shape, self.originalshape)
    rval = numpy.ravel(field)
    rval.shape = (1, len(rval))
    rval = numpy.ravel(mm(rval, self.CCAobj.p_adjoint))
    if not self.spherized:
      rval = rval * self.CCAobj.corr**2
    return rval

class ANALOGSelector:
  "Reconstructs a field averaging over several analog patterns"
  def __init__(self,ANALOGobj,patterns,smoothing=1,weightexp=2.0,report=""):
    """Constructor for the ANALOGSelector class

    Arguments:

      'ANALOGobj' -- An instance of an analog class ('EOFANALOG' or 
                     'CCAANALOG')

      'patterns' -- Base patterns (along the _first_ axis) for which the 
                    analogs are searched

    Optional arguments:

      'smoothing' -- The number of analogs to average. Defaults to 1 (i.e. 
                     single analog search)

      'weightexp' -- In the weighted averages sets the power to raise the 
                     inverse euclidean distance in the weights. Defaults
                     to 2 (inverse squared distance weights).

      'report' -- Filename where to dump a detailed report of the search.
                  The default behavior is not to dump any report.
    """
    if patterns.shape[1:] != ANALOGobj.originalshape:
      raise pex.ANALOGNoMatchingShape(
        patterns.shape[1:],
        ANALOGobj.originalshape
      ) 
    self.ANALOGobj = ANALOGobj
    self.patterns = patterns
    self.patternlenght = len(self.patterns)
    self.smoothing = smoothing
    self.analogrecords = []
    distances = numpy.zeros((self.patternlenght,self.smoothing), 'd')
    self.weights = numpy.zeros((self.patternlenght,self.smoothing), 'd')
    for irec in range(len(self.patterns)):
      analogidx = ANALOGobj.findNAnalogRecords(
        self.patterns[irec], 
        self.smoothing
      )
      distances[irec] = numpy.sqrt(ANALOGobj.sqres)
      self.analogrecords = self.analogrecords + analogidx
    self.weights = get_weights(distances, weightexp)
    if report: 
      freport = open(report,"w")
      freport.write("Analog report\n")
      freport.write(os.popen("date").read()+"\n")
      freport.write("%s\n" % ((3+20*smoothing)*"-",))
      freport.write("idx distance[weight](analogidx)\n")
      freport.write("%s\n" % ((3+20*smoothing)*"-",))
      for irec in range(len(self.patterns)):
        freport.write("%3d" % (irec+1,))
        for i in range(smoothing):
          freport.write(" %7.3f[%5.3f](%3d)" % (
            distances[irec,i],
            self.weights[irec,i],
            self.analogrecords[self.smoothing*irec+i] + 1
          ))
        freport.write("\n")
      freport.close()
  
  def returnAverage(self, field=None):
    """Returns the average reconstructed field

    Optional argument:

      'field' -- To reconstruct the analogs in a field different from the
                 library dataset. The first axis dimension must match that
                 of the library dataset.

    """
    if not field: field = self.ANALOGobj.dataset 
    aanalogrecords = numpy.array(self.analogrecords)
    ave = numpy.zeros((self.patternlenght,)+field.shape[1:], 'd')
    for i in range(self.smoothing):
      ave = ave + numpy.take(field,aanalogrecords[i::self.smoothing])
    return ave / float(self.smoothing)

  def returnWeightedAverage(self, field=None):
    """Returns the weighted average reconstructed field

    Optional argument:

      'field' -- To reconstruct the analogs in a field different from the
                 library dataset. The first axis dimension must match that
                 of the library dataset.

    """
    field = field or self.ANALOGobj.dataset 
    aanalogrecords = numpy.array(self.analogrecords)
    ave = numpy.zeros((self.patternlenght,)+field.shape[1:], 'd')
    for i in range(self.smoothing):
      ave = (ave + 
        numpy.take(field,aanalogrecords[i::self.smoothing],0) *
        numpy.reshape(self.weights[:,i], (self.patternlenght,)+len(field.shape[1:])*(1,))
      )
    return ave 
   
  def returnAnalogs(self, field=None):
    """Returns the single analog (smoothing=1) reconstructed field 

    The output is exactly the same as that of the method 'returnAverage()'
    It's just a notation matter. There is no need to use this specific
    method for the case 'smoothing=1' if you are, for instante, into a loop
    over several smoothing factors.

    Optional argument:

      'field' -- To reconstruct the analogs in a field different from the
                 library dataset. The first axis dimension must match that
                 of the library dataset.

    """
    field = field or self.ANALOGobj.dataset
    if len(field) != len(self.ANALOGobj.dataset):
      raise pex.ANALOGNoMatchingLength(len(field),len(self.ANALOGobj.dataset))
    return numpy.take(field,self.analogrecords)
  
  def __getitem__(self, idx):
    "Slide access to the analog record indices"
    return self.analogrecords[idx*self.smoothing:(idx+1)*self.smoothing]

#######################################
# Backward compatibility definitions. #
# Do NOT use!!                        #
#######################################
ANALOG = EOFANALOG                    #
ANALOGAverager = ANALOGSelector       #
#######################################

if __name__ == "__main__":
  dataset = numpy.array(
    [[1.2, 3.4, 5.7, 9.0],
     [6.8, 9.7,-4.8, 7.2],
     [6.9, 4.7, 2.8, 1.2],
     [2.8, 3.7,-0.8, 9.2],
     [5.8, 9.7,-5.8, 0.2],
     [9.8, 9.3, 4.8, 1.2],
     [1.1,-8.8, 0.9, 6.3]]
  )
#  dataset.shape = (3,2,2)
#  field = numpy.array([1.2,-9.8, 1.1, 7.3])
  field = pmvstools.center(dataset)
  field = field[2]
  field = numpy.ravel(field)
  A = ANALOG(dataset,3)
  print "dataset\n======\n", A.dataset
  print "originalshape\n======\n", A.originalshape
  print "P\n======\n", A.P
  print "L\n======\n", A.L
  print "E\n======\n", A.E
  print "flatE\n======\n", A.flatE
  print "field\n======\n", field
  print "the analog\n======\n", A.findNAnalogRecords(field, 3)
