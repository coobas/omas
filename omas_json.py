from __future__ import absolute_import, print_function, division, unicode_literals

from omas_structure import *
from omas import omas, load_omas_hierarchy

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
    #print(len(path),step)
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
        structure=ods._structure[data_structure]
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
def save_omas_json(ods, filename, **kw):
    '''
    Save an OMAS data set to Json-H

    :param ods: OMAS data set

    :param filename: filename to save to

    :param kw: arguments passed to the json.dumps method
    '''

    printd('Saving OMAS data to Json-H: %s'%filename, topic=['json-h','json'])

    hierarchy=ods_to_json(ods)
    json_string=json.dumps(hierarchy, default=json_dumper, indent=1, separators=(',',': '), **kw)
    open(filename,'w').write(json_string)

def load_omas_json(filename, **kw):
    '''
    Load an OMAS data set from Json-H

    :param filename: filename to load from

    :param kw: arguments passed to the json.loads mehtod

    :return: OMAS data set
    '''

    printd('Loading OMAS data to Json-H: %s'%filename, topic=['json-h','json'])

    if isinstance(filename,basestring):
        filename=open(filename,'r')
    hierarchy=json.loads(filename.read(),object_pairs_hook=json_loader, **kw)

    return load_omas_hierarchy(hierarchy)

def test_omas_json(ods):
    '''
    test save and load OMAS Json-H

    :param ods: ods

    :return: ods
    '''
    filename='test.json'
    save_omas_json(ods,filename)
    ods=load_omas_json(filename)
    return ods

def save_omas_jsonnd(ods, filename, **kw):
    '''
    Save an OMAS data set to Json-ND

    :param ods: OMAS data set

    :param filename: filename to save to

    :param kw: arguments passed to the json.dumps method
    '''

    printd('Saving OMAS data to Json-ND: %s'%filename, topic=['json-nd','json'])

    ds={}
    for d in ods:
        ds[d]=xarray_to_dict(ods[d])
    json_string=json.dumps(ds, default=json_dumper, indent=1, separators=(',',': '), **kw)
    open(filename,'w').write(json_string)

def load_omas_jsonnd(filename, **kw):
    '''
    Load an OMAS data set from Json-ND

    :param filename: filename to load from

    :param kw: arguments passed to the json.loads mehtod

    :return: OMAS data set
    '''

    printd('Loading OMAS data to Json-ND: %s'%filename, topic=['json-nd','json'])

    if isinstance(filename,basestring):
        filename=open(filename,'r')
    ds=json.loads(filename.read(),object_pairs_hook=json_loader, **kw)

    #identify dependencies
    dependencies=[]
    for item in ds:
        dependencies.extend(ds[item]['__dims__'])
    dependencies=numpy.unique(dependencies).tolist()
    #pprint(dependencies)

    #load dependencies first
    ods=omas()
    for item in ds:
        if item in dependencies:
            node=ds[item]
            ods[item]=xarray.DataArray(node['__data__'],dims=node['__dims__'])

    #load others then
    for item in ds:
        if item not in dependencies:
            node=ds[item]
            coords={c:ods[c] for c in node['__dims__']}
            ods[item]=xarray.DataArray(node['__data__'],dims=node['__dims__'],coords=coords)

    return ods

def test_omas_jsonnd(ods):
    '''
    test save and load OMAS Json-ND

    :param ods: ods

    :return: ods
    '''
    filename='test.json_nd'
    save_omas_jsonnd(ods,filename)
    ods=load_omas_jsonnd(filename)
    return ods

#------------------------------
if __name__ == '__main__':

    from omas import omas_data_sample
    os.environ['OMAS_DEBUG_TOPIC']='json'
    ods=omas_data_sample()

    ods=test_omas_json(ods)

#    ods=test_omas_json(ods)
