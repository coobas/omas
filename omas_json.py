from omas_structure import *
from omas import omas

def save_omas_json(ods, path, *args, **kw):
    x2h(ods)

def load_omas_json(filename_or_obj, *args, **kw):
    pass

def x2h(ods):
    #generate empty hierarchical data structure
    struct_array={}
    hierarchy={}
    tr=[]
    for key in map(str,sorted(ods.keys()))[::-1]:
        if key=='time': continue
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
        h['__xcoords__']=map(u2s,ods[key].dims)
    tr=sorted(numpy.unique(tr))

    #replicate data structures based on data dimensions
    for key in tr[::-1]:
        if key in struct_array:
            h=h0=hierarchy
            for step in key.split(separator):
                h0=h
                h=h[step]
            h0[step]=[h]*struct_array[key]

    pprint(hierarchy)

    return hierarchy

#------------------------------
if __name__ == '__main__':

    from omas_nc import *
    ods=load_omas_nc('test.nc')

    save_omas_json(ods,'test.nc')