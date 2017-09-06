import MDSplus

from omas_structure import *
from omas import omas

def write_mds_model(server, tree='test', structures=[], write=False, start_over=False, paths=None):
    if write:
        if isinstance(server,basestring):
            server=MDSplus.Connection(server)

        #wipe everyting out if requested
        if start_over:
            server.get("tcl('edit %s/shot=-1/new')"%tree)
            server.get("tcl('write')")
            server.get("tcl('close')")

    #loop over the requested structures or otherwise on all structures
    if len(structures):
        files=[]
        for structure in structures:
            files.append(imas_json_dir+os.sep+imas_version+os.sep+structure+'.json')
    else:
        files=glob.glob(imas_json_dir+os.sep+imas_version+os.sep+'*.json')
    for file in files:
        print file

        #load structure
        structure,ods=load_structure(file)

        #create actual tree structure
        for path in structure.keys():
            if path is None or path in paths:
                write_mds_node(server, tree, -1, structure[path])

def write_mds_node(server, tree, shot, meta, write_start=True, write=True, write_stop=True):
    if write_start or write or write_stop:
        if isinstance(server,basestring):
            server=MDSplus.Connection(server)

    ods=meta['full_path'].split(separator)[0]
    hash=meta['hash']

    #open the tree for edit mode
    if write_start:
        server.get("tcl('edit %s/shot=%shot')"%(tree,shot))
        server.get("tcl('add node %s /usage=subtree')"%ods)

    path=meta['full_path']
    print('%s --> %s'%(hash,path))
    if write:
        server.get("tcl('add node %s.%s /usage=structure')"%(ods,hash))
        server.get("tcl('add node %s.%s:data /usage=signal')"%(ods,hash))
        for key in meta.keys():
            if key!='hash':
                print('%s     %s:%s'%(' '*len(hash),path,key))
                server.get("tcl('add node %s.%s:%s/usage=text')"%(ods,hash,key))
                #server.get("tcl('put %s.%s:%s "$"')"%(ods,hash,key),str(meta[key])) #filling in the attributes this way does not seem to work

    #fill in the attributes
    for key in meta.keys():
        if key!='hash':
            print('%s     %s:%s [%s]'%(' '*len(hash),path,key,str(meta[key])))
            if write:
                server.put(str(":%s.%s:%s"%(ods,hash,key)),"$",str(meta[key]))

    #close the tree from edit mode
    if write_stop:
        server.get("tcl('write')")
        server.get("tcl('close')")

def create_mds_shot(server, tree, shot, clean=False):
    if isinstance(server,basestring):
        server=MDSplus.Connection(server)
    #create new shot
    if shot!=-1:
        server.get("tcl('set tree %s/shot=-1')"%tree)
        server.get("tcl('delete pulse %d /all')"%shot)
        server.get("tcl('create pulse %d')"%shot)
        if clean:
            server.get("tcl('edit %s/shot=%d/new')"%(tree,shot))
        server.get("tcl('write')")
        server.get("tcl('close')")

def xarray2mds(xarray_data):
        #generate TDI expression for writing data to MDS+
        text=[]
        args=[]
        for itemName in ['']+map(lambda k:"['%s']"%k,list(xarray_data.dims)):
            itemBaseName=itemName.strip("'[]")
            item=eval('xarray_data'+itemName)
            arg=[]
            txt='$'
            if 'units' in item.attrs:
                txt='build_with_units(%s,%s)'%(txt,item.attrs['units'])
            if any(is_uncertain(numpy.atleast_1d(item.values).flatten())):
                txt='build_with_error(%s,%s)'%(txt,txt)
                arg.extend([nominal_values(item.values),std_devs(item.values)])
            else:
                arg.append(item.values)
            args.extend(arg)
            text.append(txt)
        text='make_signal(%s,*,%s)'%(text[0],','.join(text[1:]))
        return text,args,xarray_data.dims

def save_omas_mds(ods, server, tree, shot, dynamic=True, *args, **kw):
    import MDSplus
    if isinstance(server,basestring):
        server=MDSplus.Connection(server)

    create_mds_shot(server, tree, shot, clean=dynamic)

    for item in ods.keys():
        ods=str(item.split(separator)[0])
        meta=copy.deepcopy(ods[item].attrs)
        if 'hash' in meta:
            hash=meta['hash']
        else:
            hash=md5_hasher('time')
        meta['xcoords']=str(map(u2s,ods[item].dims))
        print meta['xcoords']
        if dynamic:
            write_mds_node(server, tree, shot, meta, write_start=True, write=True, write_stop=True)
        server.openTree(tree,shot)
        text,args,dims=xarray2mds(ods[item])
        server.put(str(':%s.%s:data'%(ods,hash)),text,*args)

def mds2xarray(server, tree, shot, node):
    '''
    :return: DataArray with information from this node
    '''
    if isinstance(server,basestring):
        server=MDSplus.Connection(server)
    server.openTree(tree,shot)
    data=MDSplus.data(server.get('_s='+node))
    e=MDSplus.data(server.get('error_of(_s)'))
    if len(e) and e[0]!='':
        data=uarray(data,e)
    try:
        dims=eval(MDSplus.data(server.get(re.sub(':DATA$',':XCOORDS', node))))
    except MDSplus._mdsshr.MdsException:
        dims=map(lambda k:'dim_%d'%k,range(data.ndim))
    coords={}
    for k,c in enumerate(dims):
        coords[c]=MDSplus.data(server.get('dim_of(_s,%d)'%k))
        e=MDSplus.data(server.get('error_of(dim_of(_s,%d))'%k))
        if len(e) and e[0]!='':
            coords[c]=uarray(coords[c],e)
        units=MDSplus.data(server.get('units(_s)'))
        coords[c]=xarray.DataArray(coords[c],dims=[c],coords={c:coords[c]},attrs={'units':units})
    units=MDSplus.data(server.get('units(_s)'))
    xdata=xarray.DataArray(data,dims=dims,coords=coords,attrs={'units':units})
    return xdata

def mds2xpath(mds_path):
    ods=mds_path.split('TOP'+separator)[1].split(separator)[0].lower()
    hash=mds_path.split('TOP'+separator)[1].split(separator)[1].split(':')[0]
    meta=load_structure(ods)[1][hash]
    return meta['full_path']

def xpath2mds(tree,xpath):
    ods=xpath.split(separator)[0]
    hash=md5_hasher(xpath)
    return ('\\%s::TOP.%s.%s'%(tree,ods,hash)).upper()

def load_omas_mds(server, tree, shot):
    if isinstance(server,basestring):
        server=MDSplus.Connection(server)
    server.openTree(tree,shot)
    mds_data=sorted(map(lambda x:x.strip(),server.get('getnci("\***","FULLPATH")')))
    ds=omas()

    #identify dependencies
    dependencies=[]
    full_path_cache={}
    for item in mds_data:
        if item.endswith(':DATA'):
            full_path=MDSplus.data(server.get(re.sub(':DATA$',':FULL_PATH', item)))
            full_path_cache[item]=full_path
            try:
                coordinates=MDSplus.data(server.get(re.sub(':DATA$',':XCOORDS', item)))
            except MDSplus._mdsshr.MdsException:
                coordinates="['1...N']"
            coordinates=eval(coordinates)
            dependencies.extend(coordinates)
    dependencies=numpy.unique(dependencies)
    mds_dependencies=map(lambda x:xpath2mds(tree,x),dependencies)

    #load dependencies first
    for item in mds_data:
        if item.endswith(':DATA') and re.sub(':DATA$','',item) in mds_dependencies:
            print full_path_cache[item]
            ds[full_path_cache[item]]=mds2xarray(server, tree, shot, item)

    #load others then
    for item in mds_data:
        if item.endswith(':DATA') and not re.sub(':DATA$','',item) in mds_dependencies:
            print full_path_cache[item]
            ds[full_path_cache[item]]=mds2xarray(server, tree, shot, item)

    return ds

#------------------------------
if __name__ == '__main__':

    from omas_nc import *
    ods=load_omas_nc('test.nc')

    if False:
        #the model-data-structure approach...
        write_mds_model(mds_server, 'test', ['equilibrium'], write=True, start_over=False, paths=ods.keys())

        #add the data (this fails for entries that are user-defined)
        save_omas_mds(ods, mds_server, 'test', 999, dynamic=False)

    elif True:
        print('save to MDS+ with dynamic-data-structure approach...')
        save_omas_mds(ods, mds_server, 'test', 999)

    if True:
        print('load from MDS+')
        ods2=load_omas_mds(mds_server, 'test', 999)
        save_omas_nc(ods2,'test_mds.nc')