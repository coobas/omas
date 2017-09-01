**OMAS** (**O**rdered **M**ultidimensional **A**rray **S**tructure)
===================================================================

OMAS casts IMAS data structure as N-D labeled arrays and datasets:
* OMAS data can always be mapped to IMAS
* IMAS data can be mapped to OMAS for many cases of general interest, but not always
* OMAS python class is based on XARRAY library
* XARRAY natively represented as a NetCDF file
  - NetCDF is a computational standard compatible with HPC I/O
  - NetCDF supports dynamic loading and out-of-core parallel calculations
  - it's a file (enables share, remote io)
  - minimal dependencies (NetCDF library) allow use of OMAS anywhere
  - any code/language that can read/write NetCDF can read/write OMAS data
  - possible to use object-store systems
* added XARRAY support for MDS+
  - MDS+ is a standard in the tokamak community
  - dynamic creation of the MDS+ tree structure
* can easily write plugins for storage on different systems (IMAS, HADOOP...)
  - distinction between data-organization and data-storage
  - flat list of multidimensional arrays easily maps to many data-formats
* uniform time allows ODS concatenation, slicing, interpolation
* prepend data-structure name allows mix and match of ODS
* allocate/store only what is used when it is used
* smart OMAS python class checks for consistency with IMAS definitions on the fly
* extensible: add any N-D labeled data in addition to IMAS definitions

TODO:
* add IMAS support
* add calculation of derived quantity
