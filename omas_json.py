from omas_structure import *
from omas import omas

def save_omas_json(ods, path, *args, **kw):
    x2h(ods)

def load_omas_json(filename_or_obj, *args, **kw):
    pass

def data_filler(hierarchy, path, data):
    if isinstance(path,basestring):
        path=path.split(separator)
    step=path[0]
    print len(path),step
    #if reached the end of the path then assign data
    if len(path)==1:
        hierarchy[step]=data.values
        return
    #traverse structures
    if isinstance(hierarchy[step],dict):
        data_filler(hierarchy[step], path[1:], data)
    #traverse list of structures (slicing according to data dimensions)
    elif isinstance(hierarchy[step],list):
        dim=data.dims[0]
        for k,d in enumerate(data[dim].values):
            slice=data.isel(**{dim:k})
            if dim=='time' and 'time' not in hierarchy[step][k]:
                hierarchy[step][k]['time']={}
                data_filler(hierarchy[step][k], ['time'], slice)
            data_filler(hierarchy[step][k], path[1:], slice)

def x2h(ods):
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
        print '*'*20
        print key,ods[key].dims
        data_filler(hierarchy,key,ods[key])

    print '*'*20
    pprint(hierarchy)

    return hierarchy

#------------------------------
if __name__ == '__main__':

    from omas_nc import *
    ods=load_omas_nc('test.nc')

    save_omas_json(ods,'test.nc')