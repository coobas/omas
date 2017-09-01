__all__=['omas', 'save_omas_nc', 'load_omas_nc']

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

        return

        if key not in structure:
            if len(value.dims)==1 and value.dims[0]==key:
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

    def to_imas(self):
        #generate emphy hierarchical data structure
        struct_array={}
        imas_ids={}
        tr=[]
        for key in sorted(self.keys())[::-1]:
            if key=='time': continue
            data_structure=key.split(separator)[0]
            path=key.split(separator)
            structure=self._structure['structure_'+data_structure]
            h=imas_ids.setdefault(data_structure,{})
            for k,step in list(enumerate(path))[1:]:
                location=separator.join(path[:k+1])
                if location not in structure:
                    break
                tr.append(location)
                s=structure[location]
                if 'struct_array' in s['data_type']:
                    struct_array[location]=len(self[s['coordinates'][-1]])
                h=h.setdefault(step,{})
        tr=sorted(numpy.unique(tr))

        #replicate data structures based on data dimensions
        for key in tr[::-1]:
            if key in struct_array:
                h=h0=imas_ids
                for step in key.split(separator):
                    h0=h
                    h=h[step]
                h0[step]=[h]*struct_array[key]

        pprint(imas_ids)

        return imas_ids

from omas_json import *
from omas_mds import *
from omas_nc import *

#------------------------------
if __name__ == '__main__':

    if False:
        write_mds_model(mds_server, 'test', ['equilibrium'], write=True, start_over=True)
        create_mds_shot(mds_server,'test',999)#, True)

    elif False:
        ods1=load_omas_nc('test.nc')
        print('Load OMAS data from netCDF')

        text,args=xarray2mds(ods1['equilibrium.time_slice.profiles_1d.psi'])

        import MDSplus
        server=MDSplus.Connection(mds_server)
        server.openTree('test',999)
        server.put(':equilibrium.He5bdc700a22:data',text,*args)

        print server.get('\\TEST::TOP.equilibrium.He5bdc700a22.DATA')

    elif stage==5:
        ods1=load_omas_nc('test.nc')
        print('Load OMAS data from netCDF')

        save_omas_mds(ods1, mds_server, 'test', 999)

    elif stage==6:
        ods1=load_omas_nc('test.nc')
        print('Load OMAS data from netCDF')
        #print ods1

        ods1.to_imas()