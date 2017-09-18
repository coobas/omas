from __future__ import absolute_import, print_function, division, unicode_literals

from omas_structure import *
from omas import omas

#-----------------------------
# save and load OMAS to NetCDF
#-----------------------------

def save_omas_nc(ods, filename, **kw):
    '''
    Save an OMAS data set to NetCDF

    :param ods: OMAS data set

    :param filename:

    :param kw: arguments passed to the xarray dataset to_netcdf method
    '''
    kw['path']=filename
    return ods.to_netcdf(**kw)

def load_omas_nc(filename, **kw):
    '''
    Load an OMAS data set from NetCDF

    :param filename: filename to load from

    :param kw: arguments passed to the xarray dataset to_netcdf method

    :return: OMAS data set
    '''
    kw['filename_or_obj']=filename
    data = xarray.open_dataset(**kw)
    data.__class__=omas
    data._initialized=False
    data._structure={}
    data._initialized=True
    for item in [item for item in data.attrs if item.startswith('structure_')]:
        data._structure[re.sub('^structure_','',item)]=eval(data.attrs[item])
    return data

#------------------------------
if __name__ == '__main__':

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
                                                    dims=['time',
                                                          'equilibrium.psin'])

    save_omas_nc(ods,'test.nc')
    print('Saved OMAS data to netCDF')

    ods1=load_omas_nc('test.nc')
    print('Load OMAS data from netCDF')