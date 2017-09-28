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

    :param filename: filename to save to

    :param kw: arguments passed to the xarray dataset.to_netcdf method
    '''

    printd('Saving OMAS data to netCDF: %s'%filename, topic='nc')

    kw['path']=filename
    return ods.to_netcdf(**kw)

def load_omas_nc(filename, dynaLoad=True, **kw):
    '''
    Load an OMAS data set from NetCDF

    :param filename: filename to load from

    :param dynaLoad: If True, do not load data in memory by default.
                     Loading the data is only done at the execution time if needed.
                     Use False when working with many file objects on disk or want to over-write files.

    :param kw: arguments passed to the xarray dataset.open_dataset method

    :return: OMAS data set
    '''

    printd('Loading OMAS data to netCDF: %s'%filename, topic='nc')

    kw['filename_or_obj']=filename
    ods = xarray.open_dataset(**kw)
    ods.__class__=omas
    ods._initialized=False
    ods._structure={}
    ods._initialized=True
    if not dynaLoad:
        for item in ods:
            ods[item].load()
        ods.close()
    for item in [item for item in ods.attrs if item.startswith('structure_')]:
        ods._structure[re.sub('^structure_','',item)]=eval(ods.attrs[item])
    return ods

def test_omas_nc(ods):
    '''
    test save and load NetCDF

    :param ods: ods

    :return: ods
    '''
    filename='test.nc'
    save_omas_nc(ods,filename)
    ods=load_omas_nc(filename, dynaLoad=False)
    return ods

#------------------------------
if __name__ == '__main__':

    from omas import omas_data_sample
    os.environ['OMAS_DEBUG_TOPIC']='nc'
    ods=omas_data_sample()

    ods=test_omas_nc(ods)