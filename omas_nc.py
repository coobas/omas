from omas_structure import *
from omas import omas

def save_omas_nc(ods, path, *args, **kw):
    ods.to_netcdf(path=path, *args, **kw)

def load_omas_nc(filename_or_obj, *args, **kw):
    data = xarray.open_dataset(filename_or_obj,*args,**kw)
    data.__class__=omas
    data._initialized=False
    data._structure={}
    data._initialized=True
    for item in [item for item in data.attrs if item.startswith('structure_')]:
        data._structure[item]=eval(data.attrs[item])
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

    ods['equilibrium.psin']=xarray.DataArray(numpy.atleast_1d(numpy.linspace(0.,1.,3)),
                            dims=['equilibrium.psin'])

    ods['equilibrium.time_slice.profiles_1d.psi']=xarray.DataArray(numpy.atleast_2d([numpy.linspace(-1,1,3)]*2),
                                                    dims=['time',
                                                          'equilibrium.psin'])

    save_omas_nc(ods,'test.nc')
    print('Saved OMAS data to netCDF')

    ods1=load_omas_nc('test.nc')
    print('Load OMAS data from netCDF')