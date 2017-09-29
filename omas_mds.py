from __future__ import absolute_import, print_function, division#, unicode_literals
#MDSplus package is incompatible with unicode_litterals?

from omas_structure import *
from omas import omas

def write_mds_model(server, tree='test', data_structures=[], write=False, start_over=False, write_paths=[]):
    '''
    write an entire MDS+ model tree based on the OMAS data structures .json files
    NOTE: this function overwrites the --model-- tree (ie. shot=-1)

    :param server: MDS+ server

    :param tree: MDS+ tree to write to

    :param data_structures: list of data_structures to generate.
                             All data structures are generated if `data_structures==[]`

    :param write: write to MDS+ (otherwise it is just for testing)

    :param start_over: wipe out existing MDS+ tree structure and data

    :param write_paths:
    :return:
    '''
    import MDSplus

    if write:
        if isinstance(server,basestring):
            server=MDSplus.Connection(server)

        #wipe everyting out if requested
        if start_over:
            server.get("tcl('edit %s/shot=-1/new')"%tree)
            server.get("tcl('write')")
            server.get("tcl('close')")

    #loop over the requested data_structures or otherwise on all data_structures
    if len(data_structures):
        files=[]
        for structure in data_structures:
            files.append(imas_json_dir+os.sep+imas_version+os.sep+structure+'.json')
    else:
        files=glob.glob(imas_json_dir+os.sep+imas_version+os.sep+'*.json')
    for file in files:
        printd(file,topic='mds')

        #load structure
        structure,ods=load_structure(file)

        #create actual tree structure
        for path in structure.keys():
            if path is None or path in write_paths:
                write_mds_node(server, tree, -1, structure[path])

def write_mds_node(server, tree, shot, meta, write_start=True, write=True, write_stop=True):
    '''
    create a node in the MDS+ tree

    :param server: MDS+ server

    :param tree: MDS+ tree to write to

    :param shot: MDS+ shot to write to

    :param meta:

    :param write_start: open the MDS+ tree for editing

    :param write: put to MDS+ the data for this node

    :param write_stop: actually write and close the tree

    :return:
    '''
    import MDSplus
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
    printd('%s --> %s'%(hash,path),topic='mds')
    if write:
        server.get("tcl('add node %s.%s /usage=structure')"%(ods,hash))
        server.get("tcl('add node %s.%s:data /usage=signal')"%(ods,hash))
        for key in meta.keys():
            if key!='hash':
                printd('%s     %s:%s'%(' '*len(hash),path,key),topic='mds')
                server.get("tcl('add node %s.%s:%s/usage=text')"%(ods,hash,key))
                #server.get("tcl('put %s.%s:%s "$"')"%(ods,hash,key),str(meta[key])) #filling in the attributes this way does not seem to work

    #fill in the attributes
    for key in meta.keys():
        if len(key)>12:
            raise(AttributeError('Invalid attribute `%s` for entry `%s`: MDS+ does not accept attributes longer than 12 chars'%(key,path)))
        if key!='hash':
            printd('%s     %s:%s [%s]'%(' '*len(hash),path,key,meta[key]),topic='mds')
            if write:
                server.put(str(":%s.%s:%s"%(ods,hash,key)),"$",str(meta[key]))

    #close the tree from edit mode
    if write_stop:
        server.get("tcl('write')")
        server.get("tcl('close')")

def create_mds_shot(server, tree, shot, clean=False):
    '''
    create a new MDS+ shot based on the model tree

    :param server: MDS+ server

    :param tree: MDS+ tree to write to

    :param shot: new shot to be created

    :param clean: for this shot the new MDS+ tree will be blank
    '''
    import MDSplus
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
    '''
    this function translates a DataArray into an MDS+ signal

    :param xarray_data: xarray DataArray

    :return: (text, args, xarray_data.dims)
             text is the MDS+ signal string to be used
             args is the arguments to be passed to the MDS+ signal string
             xarray_data.dims is a list of strings indicating the dimensions of the object

    '''
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

def mds2xarray(server, tree, shot, node):
    '''
    this function reads an MDS+ node and returns the information in the format of a xarray DataArray

    :param server: MDS+ server

    :param tree: MDS+ tree name

    :param shot: MDS+ shot

    :param node: MDS+ location

    :return: DataArray with information from this node
    '''
    import MDSplus
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
        attrs={}
        if len(units.strip()):
            attrs={'units':units}
        coords[c]=xarray.DataArray(coords[c],dims=[c],coords={c:coords[c]},attrs=attrs)
    units=MDSplus.data(server.get('units(_s)'))
    xdata=xarray.DataArray(data,dims=dims,coords=coords,attrs=attrs)
    return xdata

#---------------------------
# save and load OMAS to MDS+
#---------------------------
def save_omas_mds(ods, server, tree, shot, dynamic=True):
    '''
    Save a OMAS data set to MDS+

    :param ods: OMAS data set

    :param server: MDS+ server

    :param tree: MDS+ tree name

    :param shot: MDS+ shot

    :param dynamic: dynamic tree nodes generation (False: use model tree)
    '''

    printd('Saving to MDS+: %s `%s` %d'%(server, tree, shot),topic='mds')

    import MDSplus
    if isinstance(server,basestring):
        server=MDSplus.Connection(server)

    create_mds_shot(server, tree, shot, clean=dynamic)

    for item in ods.keys():
        ds=str(item.split(separator)[0])
        meta=copy.deepcopy(ods[item].attrs)
        if 'hash' in meta:
            hash=meta['hash']
        else:
            hash=md5_hasher('time')
        meta['xcoords']=str(ods[item].dims)

        if dynamic:
            write_mds_node(server, tree, shot, meta, write_start=True, write=True, write_stop=True)
        server.openTree(tree,shot)
        text,args,dims=xarray2mds(ods[item])
        server.put(str(':%s.%s:data'%(ds,hash)),text,*args)

def load_omas_mds(server, tree, shot):
    '''
    load OMAS data set from MDS+

    :param server: MDS+ server

    :param tree: MDS+ tree name

    :param shot: MDS+ shot

    :return: OMAS data set
    '''
    printd('Loading from MDS+: %s `%s` %d'%(server, tree, shot),topic='mds')

    import MDSplus
    if isinstance(server,basestring):
        server=MDSplus.Connection(server)
    server.openTree(tree,shot)
    mds_data=sorted(map(lambda x:x.strip(),server.get('getnci("\***","FULLPATH")')))

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
    dependencies=numpy.unique(dependencies).tolist()
    mds_dependencies=map(lambda x:o2m(tree,x),dependencies)

    #load dependencies first
    ods=omas()
    for item in mds_data:
        if item.endswith(':DATA') and re.sub(':DATA$','',item) in mds_dependencies:
            printd('Reading: '+full_path_cache[item],topic='mds')
            ods[full_path_cache[item]]=mds2xarray(server, tree, shot, item)

    #load others then
    for item in mds_data:
        if item.endswith(':DATA') and not re.sub(':DATA$','',item) in mds_dependencies:
            printd('Reading: '+full_path_cache[item],topic='mds')
            ods[full_path_cache[item]]=mds2xarray(server, tree, shot, item)

    return ods

def test_omas_mds(ods):
    '''
    test save and load OMAS MDS+

    :param ods: ods

    :return: ods
    '''
    treename='test'
    shot=999

    save_omas_mds(ods, mds_server, treename, shot)
    ods1=load_omas_mds(mds_server, treename, shot)
    equal_ods(ods,ods1)
    return ods1

#------------------------------
if __name__ == '__main__':

    from omas import omas_data_sample
    os.environ['OMAS_DEBUG_TOPIC']='mds'
    ods=omas_data_sample()

    ods=test_omas_mds(ods)