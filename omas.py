__all__=['omas',
         'save_omas_nc',   'load_omas_nc',
         'save_omas_mds',  'load_omas_mds',
         'save_omas_json', 'load_omas_json',
         ]

import xarray

class omas(xarray.Dataset):

    def __init__(self, imas_version=None, *args,**kw):
        xarray.Dataset.__init__(self)

        if imas_version is None:
            imas_version=os.path.split(sorted(glob.glob(imas_json_dir+os.sep+'*'))[-1])[-1]
        self.attrs['imas_version']=imas_version

        self._initialized=False
        self._structure={}
        self._initialized=True

    def consistency_check(self, key, value):
        if key=='time':
            return

        data_structure=key.split(separator)[0]

        #load the data_structure information if not available
        if data_structure not in self._structure:
            structure=load_structure(imas_json_dir+os.sep+self.attrs['imas_version']+os.sep+data_structure+'.json')[0]
            self._structure[data_structure]=structure
            self.attrs['structure_'+data_structure]=repr(self._structure[data_structure])

        #consistency checks
        structure=self._structure[data_structure]

        if key not in structure:
            if len(value.dims)==1 and value.dims[0]==key or key.endswith('.time'):
                return
            raise(Exception('Entry `%s` is not part of the `%s` data structure'%(key,data_structure)))

        if 'base_coord' in structure[key]:
            return

        coords=structure[key]['coordinates']
        for k,c in enumerate(coords):
            if c.startswith('1...'):
                continue
            elif value.dims[k]==c:
                continue
            elif c not in value and c not in self:
                raise(Exception('Must define `%s` as part of the `%s` data structure'%(c,data_structure)))

    def __setitem__(self, key, value):
        self.consistency_check(key, value)

        if key=='time':
            for item in structure_time:
                value.attrs[item]=str(u2s(structure_time[item]))
        else:
            data_structure=key.split(separator)[0]
            structure=self._structure[data_structure]

            if key in structure:
                if not (len(value.dims)==1 and value.dims[0]==key):
                    coords_dict={c:self[c] for c in value.dims}
                    value=xarray.DataArray(value.values,dims=value.dims,coords=coords_dict)
                for item in structure[key]:
                    value.attrs[item]=str(u2s(structure[key][item]))
            else:
                value.attrs['full_path']=key
                value.attrs['hash']=md5_hasher(key)

        tmp=xarray.Dataset.__setitem__(self, key, value)
        return tmp

from omas_structure import *
from omas_mds import *
from omas_nc import *
