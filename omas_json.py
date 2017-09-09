from __future__ import absolute_import, print_function, division, unicode_literals

from omas_structure import *
from omas import omas

def gethdata(hierarchy, path):
    '''
    get data from path in json hierarchy

    :param hierarchy: json hierarchy

    :param path: path in the json hierarchy

    :return: data at path in json hierarchy
    '''
    h=hierarchy
    for step in path:
        h=h[step]
    return h

def htraverse(hierarchy, paths=[], dests=[], mapper={}, dims=[]):
    '''
    traverse the json hierarchy and returns its info

    :param hierarchy: json hierarchy

    :param paths: json paths in the hierarchy

    :param dests: json paths skipping the arrays

    :param mapper: mapper dictionary that tells for each of the entries in `dests` what are the corresponding entries in `paths`

    :param dims: all of the fundamental dimensions in the json hierarchy
                 this is used internally and should always be an empty list when called by the user

    :return: paths_out, dests_out, mapper
    '''
    paths_in=paths
    paths_out=[]

    dests_in=dests
    dests_out=[]

    dims_in=dims

    #handle dict
    if isinstance(hierarchy,dict):
        for kid in hierarchy.keys():
            if not kid.startswith('__'):
                paths=paths_in+[kid]
                dests=dests_in+[kid]
                dims=dims_in
                tmp=htraverse(hierarchy[kid],paths,dests,mapper,dims)
                paths_out.extend( tmp[0] )
                dests_out.extend( tmp[1] )
                mapper.update(    tmp[2] )
            elif kid.startswith('__data__'):
                paths_out.append(paths)
                dests_out.append(dests)
                dims=copy.deepcopy(dims_in)
                dims.extend( hierarchy['__dims__'] )
                mapper.setdefault(separator.join(dests),{'path':[],'dims':dims})
                mapper[separator.join(dests)]['path'].append(paths)

    #handle list
    elif isinstance(hierarchy,list) and len(hierarchy):
        for k in range(len(hierarchy)):
            paths=paths_in+[k]
            dests=dests_in
            dims=copy.deepcopy(dims_in)
            dims.extend(info_node(separator.join(dests_in))['coordinates'])
            tmp=htraverse(hierarchy[k],paths,dests,mapper,dims)
            paths_out.extend( tmp[0] )
            dests_out.extend( tmp[1] )
            mapper.update(    tmp[2] )

    return paths_out, dests_out, mapper

def xarray_to_dict(xarray_data):
    '''
    Convert xarray DataArray to a dictionary for use in OMAS

    :param xarray_data: input xarray.DataArray to operate on

    :return: json dictionary
    '''
    fmt='__%s__'
    d={ fmt%'data':xarray_data.values.tolist(),
        fmt%'dims':xarray_data.dims,
        fmt%'coordinates':eval(xarray_data.attrs.get('coordinates',"'[1...N]'"))}

    return d

def j_data_filler(hierarchy, path, data):
    '''
    save data in the json hierarchy given an OMAS path and the xarray.DataArray data to save

    :param hierarchy: json hierarchy

    :param path: OMAS path

    :param data: xarray.DataArray
    '''
    if isinstance(path,basestring):
        path=path.split(separator)
    step=path[0]
    #print len(path),step
    #if reached the end of the path then assign data
    if len(path)==1:
        hierarchy[step]=xarray_to_dict(data)
        return
    #traverse structures
    if isinstance(hierarchy[step],dict):
        j_data_filler(hierarchy[step], path[1:], data)
    #traverse list of structures (slicing according to data dimensions)
    elif isinstance(hierarchy[step],list):
        dim=data.dims[0]
        for k,d in enumerate(data[dim].values):
            slice=data.isel(**{dim:k})
            if dim=='time' and 'time' not in hierarchy[step][k]:
                hierarchy[step][k]['time']={}
                j_data_filler(hierarchy[step][k], ['time'], slice['time'])
            j_data_filler(hierarchy[step][k], path[1:], slice)

def ods_to_json(ods):
    '''
    transforms an OMAS data set into a hierarchical data structure

    :param ods: OMAS data set

    :return: hierarchical data structure
    '''

    #generate empty hierarchical data structure
    struct_array={}
    hierarchy={}
    tr=[]
    for key in map(str,sorted(ods.keys()))[::-1]:
        if key=='time':
            hierarchy['time']={}
            continue
        data_structure=key.split(separator)[0]
        path=key.split(separator)
        structure=ods._structure['structure_'+data_structure]
        h=hierarchy.setdefault(data_structure,{})
        for k,step in list(enumerate(path))[1:]:
            location=separator.join(path[:k+1])
            tr.append(location)
            if location in structure:
                s=structure[location]
                if 'struct_array' in s['data_type']:
                    struct_array[location]=len(ods[s['coordinates'][-1]])
            h=h.setdefault(step,{})
    tr=sorted(numpy.unique(tr))

    #replicate data structures based on data dimensions
    for key in tr[::-1]:
        if key in struct_array:
            h=h0=hierarchy
            for step in key.split(separator):
                h0=h
                h=h[step]
            #make actual copies
            h0[step]=[]
            for rep in range(struct_array[key]):
                h0[step].append(copy.deepcopy(h))

    #fill data
    for key in map(str,sorted(ods.keys())):
        # print '*'*20
        # print key,ods[key].dims
        j_data_filler(hierarchy,key,ods[key])

    # print '*'*20
    # pprint(hierarchy)

    return hierarchy

#---------------------------
# save and load OMAS to Json
#---------------------------
def save_omas_json(ods, path, *args, **kw):
    hierarchy=ods_to_json(ods)
    json_string=json.dumps(hierarchy, default=json_dumper, indent=1, separators=(',',': '))
    open(path,'w').write(json_string)

def load_omas_json(filename_or_obj, *args, **kw):
    if isinstance(filename_or_obj,basestring):
        filename_or_obj=open(filename_or_obj,'r')
    hierarchy=json.loads(filename_or_obj.read(),object_pairs_hook=json_loader)

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
            path=mapper[item]['path'][0]
            node=gethdata(hierarchy,path)
            ods[item]=xarray.DataArray(node['__data__'],dims=mapper[item]['dims'])

    #load others then
    for item in mapper:
        if item not in dependencies:
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

#------------------------------
if __name__ == '__main__':

    from omas_nc import *
    ods=load_omas_nc('test.nc')

    save_omas_json(ods,'test.json')
    ods1=load_omas_json('test.json')
    save_omas_nc(ods1,'test_json.nc')

    save_omas_json(ods,'test1.json')
    ods2=load_omas_json('test1.json')
    save_omas_nc(ods2,'test1_json.nc')
