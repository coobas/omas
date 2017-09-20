# **OMAS** (**O**rdered **M**ultidimensional **A**rray **S**tructure)

OMAS is a set of tools that aim at simplifying the interface between third-party codes and the ITER IMAS data storage infrastructure. IMAS is a set of codes, an execution framework, a data model, a data get/put API, and a data storage infrastructure used for manipulating ITER data. The idea behind OMAS is that as long as the IMAS data model is respected, one should be able to write/read to/from the IMAS data storage infrastructure, without relying on the IMAS framework or API. 

The ability of OMAS to handle data without relying on the IMAS library itself, exempts codes from such cumbersome dependency, while always remaining IMAS compatible. Any physics code or programming language that is capable of reading/writing data using one of the many OMAS supported data formats can take advantage of the functionalities provided by OMAS.

OMAS is geared towads handling of simulation data (as opposed to experimental data), and operates under the assumption that the data it manipulates can be represented as a set of N-D labeled arrays. This is a very powerful simplification since most physics codes natively represent data in such a way.

The scheme below summarizes typical data flows that could leverage the OMAS functionality (note that arrows are bi-directional)

    1)                                          /==> IMAS
	                                 OMAS  <===|
                                                \==> Other OMAS data set formats

    2)                                          /==> IMAS
	   code <==> OMAS data set <==>  OMAS  <===|
                                                \==> Other OMAS data set formats

    3)                   OMFIT------------+     /==> IMAS
	                     | code <==> OMAS | <==|
                         +----------------+     \==> Other OMAS data set formats

1. OMAS can be used to read/write data from/to IMAS or the other supported formats (e.g. NetCDF, Json, MDS+ using the IMAS naming convention)

2. physics codes can directly read/write from/to these data formats (still using the same IMAS naming convention) and OMAS can convert data from one format to another, including IMAS.

3. An integrated modeling framework (such as [OMFIT](http://gafusion.github.io/OMFIT-source)) can act as wrappers around physics codes, mapping their outputs to OMAS, which can then read/write from/to IMAS or the other supported formats.

## OMAS data structure

One of the peculiarities of IMAS is its hierarchical data tree, where data is stored in the leaf nodes, and the branches are structures or arrays of structures. In practice this means that withn IMAS multidimensional data can be represented either as arrays of structures or as multidimensional arrays, or a combination of the two, depending on the definition of the IMAS data format. The main difference between the two storing methods is that structures within arrays of structures do not need to share the same dimensions. In IMAS the time dimension is always represented as an array of sctructures, and time-dependent quantities can be defined each based on their own unique time-basis. This unconventional way of organizing the data was perhaps dictated by the IMAS need to be very general and capable of storing both simulation as well as experimental data with the same format. This choice is however in practice quite inconvenient when working with most simulation codes.

OMAS is capable of casting the IMAS hierarchical data model into a set of N-D labeled arrays, and back. In practice this means that in OMAS the time-history of a scalar quantity is represented as a one dimensional array, a time history of a one dimensional quantity as a two dimensional array, and so on. One more simplification done in OMAS is that the time array is a dimension that is shared by all time-dependent quantities. One should note that because of these assumptions, some of the most esoteric IMAS data hierarchical structures may not be mapped to the OMAS N-D labeled arrays format without interpolation.

The idea at the base of OMAS is that as long as data is organized in a way that is consistent with the ITER IMAS data model, then the conversion from one data storage system to anoteher can be easily automated. OMAS follows the IMAS naming convention as defined in the IMAS html documentation (`$IMAS_ROOT/html_documentation.html`). The OMAS N-D labeled arrays representation is easily mapped to many storage systems. OMAS is capable of seamlessly translate data between such N-D labeled array representation and the IMAS hierarchycal representation.

Currently OMAS supports the following storage systems:

| OMAS format   | Representation  | Storage type  | Requirements  |
|:-------------:|:---------------:|:-------------:|:-------------:|
| xarray        |  N-D arrays     | Python memory | xarray library
| NetCDF        |  N-D arrays     | Binary files  | NetCDF library
| MDS+          |  N-D arrays     | Database      | MDS+ library
| Json-ND       |  N-D arrays     | ASCII files   | -
| IMAS          |  IMAS hierarchy | Database      | IMAS library
| Json-H        |  IMAS hierarchy | ASCII file    | -

### Python OMAS library
The Python `omas` class is a subclass of the `xarray.Dataset` class <http://xarray.pydata.org>, and thus it inherits its N-D labeled arrays representation. Built upon the `pandas` and `numpy` Python packages, `xarrays` is quickly becoming a de-facto standard for the representation of multidimensional labelled arrays in Python. In addition to the native `xarray.Dataset` funcionalities, the OMAS python library checks for consistency with IMAS definitions on the fly.

Translation from one OMAS storage system to another occurs by first reading the original OMAS data format to memory, organizing it into a `xarray.Dataset` within the OMAS class, and writing it from memory to the new data format.

* The Python OMAS naming convention takes the form of a string with the IMAS node-names separated by dots. We refer to this naming convention as the `opath`.

  **opath**: `equilibrium.time_slice.global_quantities.ip`

* Sample usage:

  ```python
  ods=omas()
  ods['time']=xarray.DataArray(numpy.atleast_1d([1000,2000]),
                               dims=['time'])

  ods['equilibrium.time_slice.global_quantities.ip']=xarray.DataArray(numpy.atleast_1d([1E6,1.1E6]),
                                                                      dims=['time'])
  ods['equilibrium.time_slice.global_quantities.magnetic_axis.r']=xarray.DataArray(numpy.atleast_1d([1.71,1.72]),
                                                                                   dims=['time'])
  ods['equilibrium.time_slice.global_quantities.magnetic_axis.z']=xarray.DataArray(numpy.atleast_1d([0.001,0.002]),
                                                                                   dims=['time'])

  ods['equilibrium.psin']=xarray.DataArray(numpy.atleast_1d(numpy.linspace(0.,1.,3)),
                                                            dims=['equilibrium.psin'])

  ods['equilibrium.time_slice.profiles_1d.psi']=xarray.DataArray(numpy.atleast_2d([numpy.linspace(-1,1,3)]*2),
                                                              dims=['time','equilibrium.psin'])
```

### OMAS storage to NetCDF
NetCDF is a computational standard compatible with HPC I/O, and support for dynamic loading and out-of-core parallel calculations. The OMAS Python class is natively represented as a NetCDF file via the native `xarray.Dataset` functionality.

* The OMAS NetCDF naming convention mirrors the same naming convention as the OMAS Python library `opath`.

  **opath**: `equilibrium.time_slice.global_quantities.ip`

* Sample usage:

  ```python
  from omas import *
  ods=omas_data_sample()
  
  filename='ods.Json'
  
  save_omas_nc(ods,filename)
  ods=load_omas_nc(filename)
  ```

### OMAS storage to Json-ND

Json is a ASCII file format widely used as a way to transfer data across diverse platforms. The OMAS Json-ND format saves the OMAS data as N-D arrays organized in a labeled Json dictionary.

* The OMAS Json-ND naming convention mirrors the same naming convention as the OMAS Python library `opath`.

  **opath**: `equilibrium.time_slice.global_quantities.ip`

* Sample usage:

  ```python
  from omas import *
  ods=omas_data_sample()
  
  filename='ods.json'
  
  save_omas_jsonnd(ods,filename)
  ods=load_omas_jsonnd(filename)
  ```

### OMAS storage to MDS+
MDS+ is the most-widely adopted standard for storing data in the tokamak community. OMAS dynamically creates the MDS+ tree structure. This is a break with respect to the typical MDS+ approach of using a model tree, but has several advantages: 1) data is allocated only when it is used; 2) extensible and support for different IMAS version; 3) simplified data exploration.

* The OMAS data is saved in MDS+ as a flat list of MDS+ nodes within a MDS+ tree. MDS+ limits the the maximum length of its nodes to 12 characters. Hence a shortened version of the md5sum hash of the `opath` was used for internal storage. MDS+ also requires nodes names to start with a string, hence a leading `H` in front of the hash. Conversion from/to opath and mpath can be performed with the `o2m` and `m2o` functions. We refer to this path as the `mpath`.

  **mpath**: `\\treename::TOP.equilibrium.H797B74E6973`

* Sample usage:

  ```python
  from omas import *
  ods=omas_data_sample()
  
  shot=999
  treename='test'
  
  save_omas_mds(ods, mds_server, treename, shot)
  ods=load_omas_mds(mds_server, treename, shot)
  ```

### OMAS storage to Json-H

Json is a ASCII file format for representing hierarchical data. The OMAS Json-H format saves the OMAS data as a hierarchical structure where data is stored in the leaf nodes, and the branches are structures or arrays of structures.

This format closely mirrors the IMAS hierarchical organization. Internally the OMAS methods for converting between labeled multidimensional arrays and the IMAS compatible hierarchical structure are shared by the OMAS Json-H and OMAS IMAS methods.

* The OMAS Json-H naming convention takes the form a list of strings and integers separated. We refer to this naming convention as the `jpath`.

  **jpath** `['equilibrium','time_slice',0,'global_quantities','ip']`

* Sample usage:

  ```python
  from omas import *
  ods=omas_data_sample()
  
  filename='ods.json'
  
  save_omas_json(ods,filename)
  ods=load_omas_json(filename)
  ```

### OMAS storage to IMAS

IMAS is a set of codes, an execution framework, a data model, a data get/put API, and a data storage infrastructure used for manipulating ITER data.

* OMAS uses the native IMAS naming convention for interfacing with IMAS. We refer to this naming convention as the `ipath`.

  **ipath**: `equilibrium.time_slice[0].global_quantities.ip`

* Sample usage:

  ```python
  from omas import *
  ods=omas_data_sample()
  
  user='meneghini'
  tokamak='D3D'
  imas_version=os.environ['IMAS_VERSION']
  shot=1
  run=0

  paths=save_omas_imas(ods,user,tokamak,imas_version,shot,run)
  ods=load_omas_imas(ods,user,tokamak,imas_version,shot,run,paths)
  ```

