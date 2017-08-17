OMAS (Ordered Multidimensional Array Structure)

OMAS recast IMAS data structure as N-D labeled arrays and datasets
* OMAS data can always be mapped to IMAS
* IMAS data can be mapped to OMAS for many cases of general interest, but not always
* OMAS python class is based on XARRAY library
* natively represented as a NetCDF file
 - NetCDF is a computational standard compatible with HPC I/O
 - NetCDF supports dynamic loading and out-of-core parallel calculations
 - it's a file (enables share, remote io)
 - minimal dependencies (NetCDF library) allow use of OMAS anywhere
 - any code/language that can read/write NetCDF can read/write OMAS data
* can easily write plugins for storage on different systems (MDS+, IMAS, ...)
* uniform time allows ODS concatenation, slicing, interpolation
* prepend data-structure name allows mix and match of ODS
* allocate/store only what is used when it is used
* smart OMAS python class checks for consistency with IMAS definitions on the fly
* extensible: add any N-D labeled data in addition to IMAS definitions

TODO:
* add IMAS support
* add calculation of derived quantity
