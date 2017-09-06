from omas_structure import *
from omas import omas

def save_omas_json(ods, path, *args, **kw):
    hierarchy=d2h(ods)
    json_string=json.dumps(hierarchy, default=json_dumper, indent=1, separators=(',',': '))
    open(path,'w').write(json_string)

def traverse(self, string=[], join_paths=True):
    string_in=string
    string_out=[]
    #handle dict
    if isinstance(self,dict):
        for kid in self.keys():
            if not kid.startswith('__'):
                string=string_in+[kid]
                string_out.append(string)
                string_out.extend( traverse(self[kid],string,False) )
    #handle list
    elif isinstance(self,list) and len(self):
        string_out.extend( traverse(self[0],string,False) )
    #build full paths
    for k,item in enumerate(string_out):
        if not isinstance(item,basestring):
            string_out[k]=separator.join(item)
            print string_out[k]
    return string_out

def load_omas_json(filename_or_obj, *args, **kw):
    if isinstance(filename_or_obj,basestring):
        filename_or_obj=open(filename_or_obj,'r')
    hierarchy=json.loads(filename_or_obj.read(),object_pairs_hook=json_loader)

    paths=traverse(hierarchy)

#    ods=omas()

    return hierarchy

def x2j(xarray_data):
    '''
    Convert xarray to a dictionary for use in omas (based on xarray.DataArray.to_dict() function)

    :param xarray_data: input xarray.DataArray to operate on

    :return: json dictionary
    '''
    fmt='__%s__'
    d={ fmt%'data':xarray_data.values.tolist(),
        fmt%'dims':xarray_data.dims,
        fmt%'coordinates':eval(xarray_data.attrs.get('coordinates',"'[1...N]'"))}

    return u2s(d)

def j_data_filler(hierarchy, path, data):
    if isinstance(path,basestring):
        path=path.split(separator)
    step=path[0]
    print len(path),step
    #if reached the end of the path then assign data
    if len(path)==1:
        hierarchy[step]=x2j(data)
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
                j_data_filler(hierarchy[step][k], ['time'], slice)
            j_data_filler(hierarchy[step][k], path[1:], slice)

def d2h(ods):
    '''
    transforms an omas xarray.Dataset into a hierarchical data structure

    :param ods: omas data set

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
        print '*'*20
        print key,ods[key].dims
        j_data_filler(hierarchy,key,ods[key])

    print '*'*20
    pprint(hierarchy)

    return hierarchy

#------------------------------
if __name__ == '__main__':

    #from omas_nc import *
    #ods=load_omas_nc('test.nc')

    #save_omas_json(ods,'test.json')

    hierarchy=load_omas_json('test.json')
    #pprint(hierarchy)