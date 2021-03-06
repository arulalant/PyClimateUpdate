/****************

		 anumhist.c

    Array of numerical histograms in C. It allows a fast determination of 
    the bounds for a two-tailed Monte Carlo test. 

    Copyright (C) Jon Saenz, June, 2001.

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

    Jon Saenz and Jesus Fernandez
    Dept. de Fisica Aplicada II/Dept. de Fisica de la Materia Condensada
    Facultad de Ciencias
    Universidad del Pais Vasco
    Apdo. 644
    48080 - Bilbao
    Spain
    jsaenz@wm.lc.ehu.es

***************/
#include "Python.h"
#include "numpy/arrayobject.h"

#include <math.h>
#include <stdlib.h>

/*

#define MYDBG 0
#undef MYDBG

*/

#ifdef MYDBG
#include <assert.h>
#include <time.h>
FILE *logfile;

void myinitfunction(void)
{
  time_t now;
  FILE *logfile=fopen("pepe.log","w");
  assert(logfile);
  time(&now);
  fprintf(logfile,"%s\n",ctime(&now));
  fclose(logfile);
}

#endif


/* Some declarations which will be needed soon */

/* Forward declaration of the prototypes needed in the method
initialization table */
static PyObject *CreateNHArray( PyObject *self , PyObject *args );
static PyObject *FreeNHArray( PyObject *self , PyObject *args );
static PyObject *UpdateNHArray( PyObject *self , PyObject *args );
static PyObject *GetXRange( PyObject *self , PyObject *args );
static PyObject *GetDeltaX( PyObject *self , PyObject *args );

/***
Initialize the module and allow access from Python to some functions
 **/
static PyMethodDef ANHMethods[]={
  {"CreateNHArray",CreateNHArray,METH_VARARGS},
  {"FreeNHArray",FreeNHArray,METH_VARARGS},
  {"UpdateNHArray",UpdateNHArray,METH_VARARGS},
  {"GetXRange",GetXRange,METH_VARARGS},
  {"GetDeltaX",GetDeltaX,METH_VARARGS},
  {NULL,NULL} /* Last entry */
};

void initanumhist( void )
{
  PyObject *m, *d;

  /* Initialize the Python Module */
  m=Py_InitModule("anumhist",ANHMethods);
  /* Give access to numpy Arrays */
  import_array();
  /* Intialize the dictionary */
  d=PyModule_GetDict(m);
#ifdef MYDBG
  myinitfunction();
#endif
}

typedef struct {
  double xl;
  double xu;
  int nbins;
  int nbinsm1;
  double deltax;
  int elems;
  double *dbuffer; 
  int normalized;
} NHArray, *NHArrayPtr;

static PyObject *FreeNHArray(PyObject *self,PyObject *args)
{
  char *str;
  int bytes;
  NHArrayPtr nhp;

  if(!PyArg_ParseTuple(args,"s#",&str,&bytes))
    return NULL;
  nhp=(NHArrayPtr) str;
  if (nhp->dbuffer)
    free((void*)nhp->dbuffer);
  /* free((void*)nhp); */
  return Py_BuildValue("");
}

static PyObject *CreateNHArray( PyObject *self , PyObject *args )
{
  double xl,xu;
  int nbins;
  int elems;
  NHArrayPtr nharray;
  PyObject *retval;

  if(!PyArg_ParseTuple(args,"ddii",&xl,&xu,&nbins,&elems))
    return NULL;
  nharray=(NHArrayPtr)malloc(sizeof(NHArray));
  if(!nharray)
    return PyErr_NoMemory();
  nharray->elems=elems;
  nharray->xl=xl;
  nharray->xu=xu;
  nharray->nbins=nbins;
  nharray->nbinsm1=nbins-1;
  nharray->deltax=(xu-xl)/(nbins-1);
  nharray->dbuffer=(double*)calloc(elems*nbins,sizeof(double));
  nharray->normalized=0;
  if(!nharray->dbuffer)
    return PyErr_NoMemory();
  retval=(PyObject*)Py_BuildValue("s#",(char*)nharray,sizeof(NHArray));
  /* it is already under Python's garbage collection control */
  free((void*)nharray);
#ifdef MYDBG
  {
    FILE *logfile=fopen("pepe.log","a");
    assert(logfile);
    fprintf(logfile,"Created instance of NHArray\n");
    fclose(logfile);
  }
#endif
  return retval;
}

static double *getpdfptr( NHArrayPtr nhp , int ielems )
{
  return nhp->dbuffer+ielems*nhp->nbins;
}

static void updatevalue( NHArrayPtr nhp, int i , double val )
{
  double *thepdf;
  int nbin;
#ifdef MYDBG
  FILE *logfile=fopen("pepe.log","a");
  assert(logfile);
  fprintf(logfile,"deltax: %g\n",nhp->deltax);
#endif

  thepdf=getpdfptr(nhp,i);
  nbin=(int)rint((val-nhp->xl)/nhp->deltax);
  nbin=(nbin<0)?0:nbin;
  nbin=(nbin>nhp->nbinsm1)?nhp->nbinsm1:nbin;
  thepdf[nbin]++;
#ifdef MYDBG
  fprintf(logfile,"%g -> %d -> %g\n",val,nbin,thepdf[nbin]);
  fclose(logfile);
#endif
}

static void normalizepdf( NHArrayPtr nhp, int i )
{
  double *thepdf;
  int nbin;
  int Nx=0;
#ifdef MYDBG
  FILE *logfile=fopen("pepe.log","a");
  assert(logfile);
  fprintf(logfile,"Normalization\n");
#endif

  thepdf=getpdfptr(nhp,i);
  for(nbin=0;nbin<nhp->nbins;nbin++)
    Nx+=thepdf[nbin];
  for(nbin=0;nbin<nhp->nbins;nbin++)
    thepdf[nbin]=thepdf[nbin]/Nx;
  nhp->normalized=1;
#ifdef MYDBG
  fprintf(logfile,"Normalized with:%d points\n",Nx);
  fclose(logfile);
#endif
}

static void getrange(NHArrayPtr nhp, int i, double pl, double pu,
		     double *xl, double *xu)
{
  double *pdf;
  int nbin, gotlow=0;
  double p=0.0;

  pdf=getpdfptr(nhp,i);
  for(nbin=0;nbin<nhp->nbins;nbin++){
    p+=pdf[nbin];
    if((p>pl) && (!gotlow)){
      /* Got low boundary (BE CONSERVATIVE!! => -1) */
      *xl=nhp->xl+nhp->deltax*(nbin-1);
      gotlow=1;
    }
    if(p>pu){
      *xu=nhp->xl+nhp->deltax*nbin;
      break;
    }
  }
}



static PyObject *UpdateNHArray( PyObject *self , PyObject *args )
{
  char *str;
  int bytes;
  NHArrayPtr nhp;
  PyObject *po;
  PyArrayObject *a;
  int ipt;
  double *where;

  if(!PyArg_ParseTuple(args,"s#O",&str,&bytes,&po))
    return NULL;
  nhp=(NHArrayPtr) str;
  if (nhp->normalized){
    PyErr_SetString(PyExc_ValueError,"The histogram array has already been normalized, you can not update it");
    return NULL;
  }
  a=(PyArrayObject*) po;
  if (a->nd!=1){
    PyErr_SetString(PyExc_ValueError,"Input array must be linear.");
    return NULL;
  }
  if(a->dimensions[0]!=nhp->elems){
#ifdef MYDBG
    {
      FILE *logfile=fopen("pepe.log","a");
      assert(logfile);
      fprintf(logfile,"%d %d %d\n",a->nd,a->dimensions[0],nhp->elems);
      fflush(logfile);
      fclose(logfile);
    }
#endif
    PyErr_SetString(PyExc_ValueError,"Input array dimensions and NHArray dimensions do not match.");
    return NULL;
  }
  for(ipt=0;ipt<nhp->elems;ipt++){
    where=(double*) (a->data+a->strides[0]*ipt);
    updatevalue(nhp,ipt,*where);
  }
  return Py_BuildValue("");
}

static PyObject *GetXRange( PyObject *self , PyObject *args )
{
  char *str;
  int bytes;
  int ielem;
  NHArrayPtr nhp;
  double prob,pl,pu,xl,xu;
  int dims[2];
  PyArrayObject *rarray;
  double *where;

  if(!PyArg_ParseTuple(args,"s#d",&str,&bytes,&prob))
    return NULL;
  nhp=(NHArrayPtr) str;
  /* First, normalize the pdfs */
  if (!nhp->normalized){
    for(ielem=0;ielem<nhp->elems;ielem++)
      normalizepdf(nhp,ielem);
    nhp->normalized=1;
  }
  dims[0]=nhp->elems;
  dims[1]=2;
  rarray=(PyArrayObject*)PyArray_FromDims(2,dims,PyArray_DOUBLE);
  if (!rarray)
    PyErr_NoMemory();

  /* Get the probabilities */
  pl=prob/2.;
  pu=1.-pl;
  for(ielem=0;ielem<nhp->elems;ielem++){
    getrange(nhp,ielem,pl,pu,&xl,&xu);
    where=(double*)(rarray->data+ielem*rarray->strides[0]);
    *where=xl;
    where=(double*)(rarray->data+ielem*rarray->strides[0]+rarray->strides[1]);
    *where=xu;
  }
  return (PyObject*)PyArray_Return(rarray);
}

static PyObject *GetDeltaX( PyObject *self , PyObject *args )
{
  char *str;
  int bytes;
  NHArrayPtr nhp;

  if(!PyArg_ParseTuple(args,"s#",&str,&bytes))
    return NULL;
  nhp=(NHArrayPtr) str;
  return Py_BuildValue("d",nhp->deltax);
}
