# **OMAS** (**O**rdered **M**ultidimensional **A**rray **S**tructure)

IMAS data storage system is (will be) the standard for storing/retrieving ITER data.

OMAS lets each code write the data in the format that they prefer, but hadering to the IMAS naming convention. The OMAS library takes care of translating from one data storage to another, including the IMAS data storage system. To make things simpler, the OMAS library assumes that the data can be represented as a set of N-D labeled arrays. This is a very powerful simplification, which poses very little constraints on physics codes, since most of them already naturally represent their data in such a way.

As a result OMAS enables physics codes to read/write data from/to IMAS while keeping them independent of the details of the IMAS implementation (e.g. access layer (UAL, IDAM) or backend (HDF5, MDS+)), and thus not breaking current workflows.

The scheme below summarizes the typical data flow tha leverages the OMAS functionality (note that arrows are bi-directional)

    1)                                           /==> IMAS
	                                  OMAS  <===|
                                                 \==> Other OMAS data set formats

    2)                                           /==> IMAS
	   code  <==> OMAS data set <==>  OMAS  <===|
                                                 \==> Other OMAS data set formats

    3)                    OMFIT------------+     /==> IMAS
	                      | code <==> OMAS | <==|
                          +----------------+     \==> Other OMAS data set formats

1. OMAS can read/write data from/to IMAS or the other supported formats (e.g. NetCDF, Json, MDS+ using the IMAS naming convention)
2. physics codes can directly read/write from/to these data formats (still using the same IMAS naming convention) and OMAS can convert data from one format to another, including IMAS.
3. An integrated modeling framework (such as [OMFIT](http://gafusion.github.io/OMFIT-source)) can act as wrappers around physics codes, mapping their outputs to OMAS, which can then read/write from/to IMAS or the other supported formats.

## OMAS data structure


OMAS casts the IMAS data structures into N-D labeled arrays and datasets
* OMAS N-D arrays can always be mapped to IMAS hierarchical structure
* uses a single time array definition, which allows ODS concatenation, slicing, interpolation
* prepending of data-structure name allows mix and match of ODS
* IMAS data hierarchical structure can be mapped to OMAS for most cases of practical interest, but not always
* OMAS supports multiple formats
  - NetCDF
  - Json
  - MDS+
  - IMAS
  - flat list of N-D labeled arrays easily maps to many data-formats (HADOOP...)

### Python OMAS library
The Python `omas` class is a derived class of the xarray.Dataset class,
and thus it inherits the capabilitites: xarray.pydata.org
OMAS follows the naming IMAS naming convention, as defined in the IMAS html
documentation. The OMAS python library checks for consistency with IMAS
definitions on the fly.

* opath
  'equilibrium.time_slice.global_quantities.ip'

### OMAS storage to NetCDF
OMAS data sets are stored in NetCDF files as a flat set of entries.

* Python xarray.Dataset are natively represented as a NetCDF file
* NetCDF is a computational standard compatible with HPC I/O
* NetCDF supports dynamic loading and out-of-core parallel calculations
* it's a file (enables share, remote io)
* minimal dependencies (NetCDF library) allow use of OMAS anywhere
* any code/language that can read/write NetCDF can read/write OMAS data
* possible to use with object-store systems
* extensible: add any N-D labeled data in addition to IMAS definitions
* allocate/store only what is used when it is used
* opath
  - `equilibrium.time_slice.global_quantities.ip`

### OMAS storage to Json Data Array

* Python xarray.Dataset are natively represented as a NetCDF file
* opath
  - `equilibrium.time_slice.global_quantities.ip`

### OMAS storage to MDS+
OMAS data sets can be stored directly to MDS+, which is the most-widely adopted standard for storing data in the tokamak community.

The OMAS data is saved in MDS+ as a flat list of MDS+ nodes within a MDS+ tree.
Although a hierarchical storage of the data, following that follows the same
`opath` naming convention would have been more natural, one has to face
the MDS+ limitation that limits the the maximum length of a node string
to 12 characters. Hence a shortened version of the md5sum hash of
the `opath` was used. We refer to this path as the `mpath`.
MDS+ also requires that the nodes names starts with a string,
hence the leading `H` in front of the hash.

* OMAS dynamically creates the MDS+ tree structure. This is a break with respect to the typical MDS+ approach of using a model tree, but it has several advantages.
* allocate/store only what is used when it is used
* support for different IMAS version
* extensible: add any N-D labeled data in addition to IMAS definitions
* mpath
  - `\\treename::TOP.equilibrium.H797B74E6973`
  - conversion from/to opath and mpath can be performed with the `o2m` and `m2o` functions

### OMAS storage to Json Hierarchy

* OMAS methods to convert from/to labeled multidimensional arrays to hierarchical structures
* json is a standard ASCII format for representing hierarchical data
* using same hierarchical structure of IMAS
* jpath:
  - `['equilibrium','time_slice',0,'global_quantities','ip']`

### OMAS storage to IMAS

* shares OMAS Json Hierarchy methods to convert from/to labeled multidimensional arrays to hierarchical structures
* jpath:
  - `equilibrium.time_slice[0].global_quantities.ip`
