from __future__ import absolute_import, print_function, division, unicode_literals

__all__=['omas',              'ods_sample',
         'save_omas_nc',      'load_omas_nc',      'test_omas_nc',
         'save_omas_s3',      'load_omas_s3',      'test_omas_s3',
         'save_omas_mds',     'load_omas_mds',     'test_omas_mds',    'o2m', 'm2o',
         'save_omas_json',    'load_omas_json',    'test_omas_json',
         'save_omas_jsonnd',  'load_omas_jsonnd',  'test_omas_jsonnd',
         'save_omas_asciind', 'load_omas_asciind', 'test_omas_asciind',
         'save_omas_imas'
         ]

import xarray

class omas(xarray.Dataset):

    '''
    OMAS data set class
    '''

    def __init__(self, imas_version=None):
        '''
        :param imas_version: IMAS version to use as a constrain for the nodes names
        '''
        xarray.Dataset.__init__(self)

        if imas_version is None:
            imas_version=os.path.split(sorted(glob.glob(imas_json_dir+os.sep+'*'))[-1])[-1]
        self.attrs['imas_version']=imas_version

        self._initialized=False
        self._structure={}
        self._initialized=True

    def consistency_check(self, opath, data_array):
        '''
        check that the opath and the data array dimensions are consistent with IMAS data structure

        :param opath: OMAS path

        :param data_array: xarray.DataArray

        :return: True/False depending on result of consistency check
        '''
        if opath=='time':
            return

        data_structure=opath.split(separator)[0]

        #load the data_structure information if not available
        if data_structure not in self._structure:
            structure=load_structure(imas_json_dir+os.sep+self.attrs['imas_version']+os.sep+data_structure+'.json')[0]
            self._structure[data_structure]=structure
            self.attrs['structure_'+data_structure]=repr(self._structure[data_structure])

        #consistency checks
        structure=self._structure[data_structure]

        if opath not in structure:
            if len(data_array.dims)==1 and data_array.dims[0]==opath or opath.endswith('.time'):
                return
            raise(Exception('Entry `%s` with dimensions `%s` is not part of the `%s` data structure'%(opath,str(data_array.dims),data_structure)))

        if 'base_coord' in structure[opath]:
            return

        coords=structure[opath]['coordinates']
        for k,c in enumerate(coords):
            if c.startswith('1...'):
                continue
            elif data_array.dims[k]==c:
                continue
            elif c not in data_array and c not in self:
                raise(Exception('Must define `%s` as part of the `%s` data structure'%(c,data_structure)))

    def __setitem__(self, opath, data_array):
        '''
        assign a xarray.DataArray to the opath in the OMAS data set
        Note that the opath and the data array dimensions will be checked for consistent with IMAS data structure

        :param opath: OMAS path

        :param data_array: xarray.DataArray

        :return: assigned xarray.DataArray
        '''
        self.consistency_check(opath, data_array)

        if opath=='time':
            for item in structure_time:
                data_array.attrs[item]=str(structure_time[item])
        else:
            data_structure=opath.split(separator)[0]
            structure=self._structure[data_structure]

            if opath in structure:
                if not (len(data_array.dims)==1 and data_array.dims[0]==opath):
                    coords_dict={c:self[c] for c in data_array.dims}
                    data_array=xarray.DataArray(data_array.values,dims=data_array.dims,coords=coords_dict)
                for item in structure[opath]:
                    data_array.attrs[item]=str(structure[opath][item])
            else:
                data_array.attrs['full_path']=opath
                data_array.attrs['hash']=md5_hasher(opath)

        tmp=xarray.Dataset.__setitem__(self, opath, data_array)
        return tmp

def load_omas_hierarchy(hierarchy, **kw):
    '''
    Load an OMAS data set from Json-H

    :param filename: filename to load from

    :param kw: arguments passed to the json.loads mehtod

    :return: OMAS data set
    '''

    #create mapper dictionary to rebuild xarray structure
    paths,dests,mapper=htraverse(hierarchy)
    #pprint(mapper)

    #identify dependencies
    dependencies=[]
    for item in mapper:
        dependencies.extend(mapper[item]['dims'])
    dependencies=numpy.unique(dependencies).tolist()
    # pprint(dependencies)

    #load dependencies first
    ods=omas()
    for item in mapper:
        if item in dependencies:
            #print('dependency:',item)
            path=mapper[item]['path'][0]
            node=gethdata(hierarchy,path)
            ods[item]=xarray.DataArray(node['__data__'],dims=mapper[item]['dims'])

    #load others then
    for item in mapper:
        if item not in dependencies and not item.endswith('.time'):
            #print('others:',item)
            #create empty data of the right size
            ods[item]=data=xarray.DataArray(numpy.nan+numpy.zeros(map(lambda node:ods[node].size,mapper[item]['dims'])),dims=mapper[item]['dims'])
            #fill in the actual data
            coords={}
            for path in mapper[item]['path']:
                node=gethdata(hierarchy,path)
                #figure out dimensions of the slice
                islice=filter(lambda x:not isinstance(x,basestring), path )
                slice=numpy.array(node['__data__'])
                dslice={}
                for d in range(len(mapper[item]['dims'])-len(slice.shape)):
                    dim=mapper[item]['dims'][d]
                    dslice[ dim ]=islice[d]
                    coords[dim]=ods[dim].values
                #enter the data
                if len(data.shape)==1:
                    data.values[islice[0]]=slice
                else:
                    data.isel(**dslice).values[:]=slice
            #update coordinates
            data.coords.update(coords)

    return ods

def ods_sample():

    printd('Creating sample OMAS data structure',topic='*')

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
    return ods

from omas_structure import *
from omas_mds import *
from omas_nc import *
from omas_json import *
from omas_imas import *
from omas_asciind import *

#------------------------------
if __name__ == '__main__':

    os.environ['OMAS_DEBUG_TOPIC']=''
    ods=ods_sample()

    tests=['json','jsonnd','nc','asciind','s3','mds','imas']
    results=numpy.zeros((len(tests),len(tests)))

    for k1,t1 in enumerate(tests):
        try:
            ods1=locals()['test_omas_'+t1](ods)
        except Exception as _excp:
            printe(repr(_excp))
        for k2,t2 in enumerate(tests):
            try:
                print(t1,t2)
                ods2=locals()['test_omas_'+t2](ods1)
                if equal_ods(ods1,ods2):
                    results[k1,k2]=1.0
                else:
                    results[k1,k2]=-1.0
            except Exception as _excp:
                printe(repr(_excp))

    print(results.astype(int))