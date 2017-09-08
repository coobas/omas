**OMAS** (**O**rdered **M**ultidimensional **A**rray **S**tructure)
===================================================================

* OMAS casts the IMAS data structures into N-D labeled arrays and datasets
  - OMAS N-D arrays can always be mapped to IMAS hierarchical structure
  - IMAS data hierarchical structure can be mapped to OMAS for most cases of practical interest, but not always

* OMAS supports multiple formats
  - NetCDF
  - Json
  - MDS+
  - IMAS
  - flat list of N-D labeled arrays easily maps to many data-formats (HADOOP...)

* OMAS python class is based on XARRAY library
  - OMAS python class checks for consistency with IMAS definitions on the fly
  - OMAS uses a single time array definition, which allows ODS concatenation, slicing, interpolation
  - prepending of data-structure name allows mix and match of ODS
  - extensible: add any N-D labeled data in addition to IMAS definitions
  - OMAS allocates/stores only what is used when it is used

* OMAS python class is based on XARRAY library
  - XARRAY natively represented as a NetCDF file
  - NetCDF is a computational standard compatible with HPC I/O
  - NetCDF supports dynamic loading and out-of-core parallel calculations
  - it's a file (enables share, remote io)
  - minimal dependencies (NetCDF library) allow use of OMAS anywhere
  - any code/language that can read/write NetCDF can read/write OMAS data
  - possible to use with object-store systems

* OMAS interface to MDS+
  - MDS+ is a standard in the tokamak community
  - dynamic creation of the MDS+ tree structure

* OMAS interface to Json
  - json is a standard ASCII format for representing hierarchical data
  - using same hierarchical structure of IMAS

TODO:
* add calculation of derived quantity
