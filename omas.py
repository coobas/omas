__all__=['omas', 'save_omas_nc', 'load_omas_nc']

import xarray
import os
import sys
import glob
import json
from pprint import pprint
from hashlib import md5
import uncertainties

imas_json_dir=os.path.abspath(str(os.path.dirname(unicode(__file__, sys.getfilesystemencoding())))+'/imas_json/')

fix={}
fix['ic.surface_current.n_pol']='ic.surface_current.n_tor'
fix['waveform.value.time']='waveform.time'
fix['unit.beamlets_group.beamlets.positions.R']='unit.beamlets_group.beamlets.positions.r'

separator='.'

def u2s(x):
    if isinstance(x,unicode):
        #convert unicode to string if unicode encoding is unecessary
        xs=x.encode('utf-8')
        if xs==x: return xs
    elif isinstance(x,dict):
        return json_loader(x.items())
    return x

def json_dumper(obj):
    if isinstance(obj, numpy.ndarray):
        if 'complex' in str(obj.dtype).lower():
            return dict(__ndarray_tolist_real__ = obj.real.tolist(),
                        __ndarray_tolist_imag__ = obj.imag.tolist(),
                        dtype=str(obj.dtype),
                        shape=obj.shape)

        else:
            return dict(__ndarray_tolist__=obj.tolist(),
                        dtype=str(obj.dtype),
                        shape=obj.shape)
    elif isinstance(obj, numpy.generic):
        return numpy.asscalar(obj)
    elif isinstance(obj, complex):
        return dict(__complex__=True,real=obj.real,imag=obj.imag)
    try:
        return obj.toJSON()
    except Exception:
        return obj.__dict__

def json_loader(object_pairs):
    object_pairs=map(lambda o:(u2s(o[0]),u2s(o[1])),object_pairs)
    dct=dict((x,y) for x,y in object_pairs)
    if '__ndarray_tolist__' in dct:
        return array(dct['__ndarray_tolist__'],dtype=dct['dtype']).reshape(dct['shape'])
    elif ('__ndarray_tolist_real__' in dct and
          '__ndarray_tolist_imag__' in dct):
          return (array(dct['__ndarray_tolist_real__'],dtype=dct['dtype']).reshape(dct['shape'])+
                  array(dct['__ndarray_tolist_imag__'],dtype=dct['dtype']).reshape(dct['shape'])*1j)
    elif '__ndarray__' in dct:
        data = base64.b64decode(dct['__ndarray__'])
        return np.frombuffer(data, dct['dtype']).reshape(dct['shape'])
    elif '__complex__' in dct:
        return complex(dct['real'],dct['imag'])
    return dct

def set_type(dt):
    if any(array([k.lower() in dt.lower() for k in ['FLT','FLOAT','DBL','DOUBLE']])):
        return float
    if any(array([k.lower() in dt.lower() for k in ['INT','INTEGER']])):
        return int
    if any(array([k.lower() in dt.lower() for k in ['CMPLX','COMPLEX']])):
        return complex
    if any(array([k.lower() in dt.lower() for k in ['STR','STRING']])):
        return str
    else:
        return None

def remove_parentheses(inv):
    k=0
    lp=''
    out=''
    for c in inv:
        if c=='(':
            k+=1
            lp=c
        elif c==')':
            k-=1
            lp+=c
        elif k==0:
            out+=c
        elif k==1:
            lp+=c
    if inv.endswith(')'):
        out+=('_'+lp[1:-1])
    return out

def aggregate_html_docs(imas_html_dir, imas_version):
    from bs4 import BeautifulSoup

    files=glob.glob(imas_html_dir+'/*.html')

    line='<table><tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr></table>'

    tables=[line%('Full path name','Description','Data Type','Coordinates')]
    for file in files:
        print file
        if os.path.split(file)[1] in ['html_documentation.html','clean.html','dd_versions.html']:
            continue
        html_doc=open(file).read()
        soup = BeautifulSoup(html_doc, ['lxml','html.parser'][0])
        tables.append( line%('---BREAK---',os.path.splitext(os.path.split(file)[1])[0],'','') )
        tables.append( soup.table.prettify() )

    if not os.path.exists(imas_json_dir+os.sep+imas_version):
        os.makedirs(imas_json_dir+os.sep+imas_version)
    clean=os.path.abspath(os.sep.join([imas_json_dir,imas_version,'clean']))
    open(clean+'.html','w').write( '\n\n\n'.join(tables).encode('utf-8').decode('ascii',errors='ignore') )

    print('')
    print('Manual steps:')
    print('1. open %s in EXCEL'%(clean+'.html'))
    print('2. un-merge all cells in EXCEL')
    print('3. save excel document as %s'%(clean+'.xls'))

def create_json_structure(imas_version, data_structures=None):
    #read xls file
    clean=os.path.abspath(os.sep.join([imas_json_dir,imas_version,'clean']))
    data=pandas.read_excel(clean+'.xls','Sheet1')
    data.rename(columns={'Full path name': 'full_path', 'Description':'description', 'Data Type': 'data_type', 'Coordinates':'coordinates'}, inplace=True)

    cols=[str(col) for col in data if not col.startswith('Unnamed')]

    #split clean.xls into sections
    sections=OrderedDict()
    tbl=None
    for k in range(len(data[cols[0]])):
        if isinstance(data['full_path'][k],basestring) and '---BREAK---' in data['full_path'][k]:
            tbl=data['description'][k]
            sections[tbl]=k
    sections[None]=len(data)
    datas={}
    for k,(start,stop) in enumerate(zip(sections.values()[:-1],sections.values()[1:])):
        datas[sections.keys()[k]]=data[start+2:stop].reset_index()

    #data structures
    if data_structures is None:
        data_structures=sorted(datas.keys())

    #loop over the data structures
    structures={}
    for section in data_structures:
        print('- %s'%section)
        data=datas[section]
        structure=structures[section]={}

        #squash rows with nans
        entries={}
        cols=[str(col) for col in data if not col.startswith('Unnamed') and col!='index']
        for k in range(len(data[cols[0]])):
            if isinstance(data['full_path'][k],basestring) and not data['full_path'][k].startswith('Lifecycle'):
                entry=entries[k]={}
            for col in cols:
                entry.setdefault(col,[])
                if isinstance(data[col][k],basestring):
                    entry[col].append( str( data[col][k].encode('utf-8').decode('ascii',errors='ignore') ) )

        #remove obsolescent entries and content of each cell
        for k in sorted(entries.keys()):
            if k not in entries.keys():
                continue

            if 'obsolescent' in '\n'.join(entries[k]['full_path']):
                basepath='\n'.join(entries[k]['full_path']).strip().split('\n')[0]
                for k1 in entries.keys():
                    if basepath in '\n'.join(entries[k1]['full_path']):
                        del entries[k1]
            else:

                for col in cols:
                    if col=='full_path':
                        entries[k][col]='\n'.join(entries[k][col]).strip().split('\n')[0]
                        entries[k][col]=re.sub(r'\([^)]*\)','',entries[k][col])
                        entries[k][col]=fix.get(entries[k][col],entries[k][col])
                    elif col=='coordinates':
                        entries[k][col]=map(lambda x:re.sub('^[0-9]+- ','',x),entries[k][col])
                        entries[k][col]=map(lambda x:remove_parentheses(x),entries[k][col])
                        entries[k][col]=map(lambda x:fix.get(x,x),entries[k][col])
                        entries[k][col]=map(lambda x:x.split(' OR ')[0],entries[k][col])
                        entries[k][col]=map(lambda x:x.split('IDS:')[-1],entries[k][col])
                    elif col=='data_type':
                        entries[k][col]='\n'.join(entries[k][col])
                        if entries[k][col]=='int_type':
                            entries[k][col]='INT_0D'
                        elif entries[k][col]=='flt_type':
                            entries[k][col]='INT_0D'
                    else:
                        entries[k][col]='\n'.join(entries[k][col])

        #convert to flat dictionary
        for k in entries:
            structure[entries[k]['full_path']]={}
            for col in cols:
                if col!='full_path':
                    structure[entries[k]['full_path']][col]=entries[k][col]

        # #concatenate descriptions
        # lmax=max(map(len,'/'.join(structure.keys()).split('/')))
        # for key in structure.keys():
        #     path='* '+key.split('/')[-1].ljust(lmax)
        #     structure[key]['description']=path+': '+structure[key]['description']
        # for key in structure.keys():
        #     if '/' in key:
        #         basepath='/'.join(key.split('/')[:-1])
        #         basedesc=structure[basepath]['description']
        #         structure[key]['description']=basedesc+'\n'+structure[key]['description']
        # for key in structure.keys():
        #     structure[key]['description']=structure[key]['description']

        #handle arrays of structures
        struct_array=[]
        for key in sorted(structure.keys()):
            for k in struct_array[::-1]:
                if k not in key:
                    struct_array.pop()
            if 'struct_array' in structure[key]['data_type']:
                for k,c in enumerate(structure[key]['coordinates']):
                    struct_array.append(key)
                    if not c.startswith('1...'): #add a dimension to this coordinate
                        structure[c]['coordinates'].append('1...N')
            else:
                for k in struct_array[::-1]:
                    if key not in structure[k]['coordinates']:
                        structure[key]['coordinates']=structure[k]['coordinates']+structure[key]['coordinates']

        #find fundamental coordinates
        base_coords=[]
        for key in structure.keys():
            coords=structure[key]['coordinates']
            d=structure[key]['data_type']
            for c in coords:
                if c.startswith('1...') and 'struct' not in d:
                    base_coords.append( re.sub('(_error_upper|_error_lower|_error_index)$','',key) )
                    structure[ re.sub('(_error_upper|_error_lower|_error_index)$','',key) ]['base_coord']=True
        base_coords=numpy.unique(base_coords).tolist()

        #make sure all coordinates exist
        for key in structure.keys():
            if 'base_coord' in structure[key] and len(structure[key]['coordinates'])==1:
                #structure[key]['independent_coordinate']=True
                continue
            coords=structure[key]['coordinates']
            if not len(coords):
                continue
            else:
                for k,c in enumerate(coords):
                    if c.startswith('1...') and len(re.findall('(_error_upper|_error_lower|_error_index)$',key)):
                        coords[k]=re.sub('(_error_upper|_error_lower|_error_index)$','',key)
                    elif c.startswith('1...'):
                        pass
                    elif c not in structure:
                        print('  %s not defined -- adding'%c)
                        base_coords.append(c)
                        structure[c]={}
                        structure[c]['description']='imas missing dimension'
                        structure[c]['coordinates']=['1...N']
                        structure[c]['data_type']='INT_1D'
                        structure[c]['base_coord']=True

        #prepend structure name to all entries
        for key in structure.keys():
            for k,c in enumerate(structure[key]['coordinates']):
                if c.startswith('1...'):
                    continue
                structure[key]['coordinates'][k]=section+'/'+c
            structure[section+'/'+key]=structure[key]
            del structure[key]

        #unify time dimensions
        for key in structure.keys():
            if key.endswith('/time'):
                del structure[key]
            else:
                coords=structure[key]['coordinates']
                for k,c in enumerate(coords):
                    if c.endswith('/time'):
                        coords[k]='time'

        #convert separator
        for key in structure.keys():
            for k,c in enumerate(structure[key]['coordinates']):
                structure[key]['coordinates'][k]=re.sub('/',separator,structure[key]['coordinates'][k])
            structure[re.sub('/',separator,key)]=structure[key]
            del structure[key]

        #save full_path_name and hash as part of json structure
        for key in structure.keys():
            structure[key]['hash']='H'+md5(key).hexdigest()[:11]
            structure[key]['full_path']=key

        #deploy imas structures as json
        json_string=json.dumps(structure, default=json_dumper, indent=1, separators=(',',': '))
        open(imas_json_dir+os.sep+imas_version+os.sep+section+'.json','w').write(json_string)

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
            structure=json.loads(open(imas_json_dir+os.sep+self.attrs['imas_version']+os.sep+data_structure+'.json','r').read(),object_pairs_hook=json_loader)
            self._structure[data_structure]=structure
            self.attrs['structure_'+data_structure]=repr(self._structure[data_structure])

        #consistency checks
        structure=self._structure[data_structure]

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

        if key!='time':
            data_structure=key.split(separator)[0]

            structure=self._structure[data_structure]

            if key in structure:
                if not (len(value.dims)==1 and value.dims[0]==key):
                    coords_dict={c:self[c] for c in value.dims}
                    value=xarray.DataArray(value.values,dims=value.dims,coords=coords_dict)
                value.attrs['description']='\n'+structure[key]['description']

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

def _traverse(me, path=''):
    paths=[]
    for kid in me:
        paths.append(separator.join([path,kid]).lstrip(separator))
        if isinstance(me[kid],dict):
            paths.extend( _traverse(me[kid],paths[-1]) )
    return paths

def save_omas_nc(ods, path, *args, **kw):
    ods.to_netcdf(path=path, *args, **kw)

def load_omas_nc(filename_or_obj, *args, **kw):
    data = xarray.open_dataset(filename_or_obj,*args,**kw)
    data.__class__=omas
    data._initialized=False
    data._structure={}
    data._initialized=True
    for item in [item for item in data.attrs if item.startswith('structure_')]:
        data._structure[item]=eval(data.attrs[item])
    return data

def write_mds_model(server, tree='test', structures=[], write=False, start_over=False):
    if write:
        import MDSplus
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
        structure=json.loads(open(file,'r').read(),object_pairs_hook=json_loader)
        ids=os.path.splitext(os.path.split(file)[1])[0][:12]

        #open the tree in edit mode
        if write:
            server.get("tcl('edit %s/shot=-1')"%tree)
            server.get("tcl('add node %s /usage=subtree')"%ids)

        #create actual tree structure
        for path in structure.keys():
            print('%s --> %s'%(structure[path]['hash'],path))
            if write:
                server.get("tcl('add node %s.%s /usage=structure')"%(ids,structure[path]['hash']))
                server.get("tcl('add node %s.%s:data /usage=signal')"%(ids,structure[path]['hash']))
                for key in structure[path].keys():
                    if key!='hash':
                        print('%s     %s:%s'%(' '*len(structure[path]['hash']),path,key))
                        server.get("tcl('add node %s.%s:%s/usage=text')"%(ids,structure[path]['hash'],key))
                        #server.get("tcl('put %s.%s:%s "$"')"%(ids,structure[path]['hash'],key),str(structure[path][key])) #filling in the attributes this way does not seem to work

        #close the tree from edit mode
        if write:
            server.get("tcl('write')")
            server.get("tcl('close')")
            server.openTree('test',-1)

        #fill in the attributes
        for path in structure.keys():
            print('%s >>> %s'%(structure[path]['hash'],path))
            if write:
                for key in structure[path].keys():
                    if key!='hash':
                        print('%s     %s:%s [%s]'%(' '*len(structure[path]['hash']),path,key,str(structure[path][key])))
                        server.put(str(":%s.%s:%s"%(ids,structure[path]['hash'],key)),"$",str(structure[path][key]))

def create_mds_shot(server, tree, shot, clean=False):
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

def is_uncertain(var):
    '''return True if variable is instance of uncertainties'''
    def uncertain_check(x):
        return isinstance(x,uncertainties.Variable) or isinstance(x,uncertainties.AffineScalarFunc)
    if numpy.iterable(var):
        return numpy.reshape(numpy.array(map(uncertain_check,numpy.array(var).flat)),numpy.array(var).shape)
    else:
        return uncertain_check(var)

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
            if any(is_uncertain(item.values)):
                txt='build_with_error(%s,%s)'%(txt,txt)
                arg.extend([nominal_values(item.values),std_devs(item.values)])
            else:
                arg.append(item.values)
            args.extend(arg)
            text.append(txt)
        text='make_signal(%s,*,%s)'%(text[0],','.join(text[1:]))
        return text,args

#------------------------------
if __name__ == '__main__':

    import pandas
    from collections import OrderedDict
    import re
    import numpy

    if 'IMAS_VERSION' in os.environ:
        imas_version=os.environ['IMAS_VERSION']
    else:
        imas_version='3.10.1'
    if 'IMAS_PREFIX' in os.environ:
        imas_html_dir=os.environ['IMAS_PREFIX']+'/share/doc/imas/'
    else:
        imas_html_dir='/Users/meneghini/tmp/imas'
    imas_html_dir=os.path.abspath(imas_html_dir)

    mds_server=['atlas.gat.com','127.0.0.1:63555'][0]

    #stage #1 must be run to generate necessary .json files
    stage=4

    if stage==0:
        aggregate_html_docs(imas_html_dir,imas_version)

    elif stage==1:
        create_json_structure(imas_version)

    elif stage==2:
        ods=omas()
        ods['time']=xarray.DataArray(numpy.atleast_1d([1000,2000]),
                              dims=['time'])

        ods['equilibrium.time_slice.global_quantities.ip']=xarray.DataArray(numpy.atleast_1d([1E6,1.1E6]),
                                                             dims=['time'])
        ods['equilibrium.time_slice.global_quantities.magnetic_axis.r']=xarray.DataArray(numpy.atleast_1d([1.71,1.72]),
                                                             dims=['time'])

        ods['equilibrium.time_slice.profiles_1d.psin']=xarray.DataArray(numpy.atleast_1d(numpy.linspace(0.,1.,3)),
                                                        dims=['equilibrium.time_slice.profiles_1d.psin'])

        ods['equilibrium.time_slice.profiles_1d.psi']=xarray.DataArray(numpy.atleast_2d([numpy.linspace(-1,1,3)]*2),
                                                        dims=['time',
                                                              'equilibrium.time_slice.profiles_1d.psin'])

        save_omas_nc(ods,'test.nc')
        print('Saved OMAS data to netCDF')

        ods1=load_omas_nc('test.nc')
        print('Load OMAS data from netCDF')

    elif stage==3:
        write_mds_model(mds_server, 'test', ['actuator'], write=True, start_over=True)
        create_mds_shot(mds_server,'test',999)#, True)

    elif stage==4:
        ods1=load_omas_nc('test.nc')
        print('Load OMAS data from netCDF')

        time=xarray.DataArray(numpy.atleast_1d([1000,2000]),
                              dims=['time'])

        actuator_power=xarray.DataArray(numpy.atleast_1d([1E6,1.1E6]),
                                        dims=['time'])

        text,args=xarray2mds(actuator_power)

        import MDSplus
        server=MDSplus.Connection(mds_server)
        server.openTree('test',999)
        server.put(':actuator.H653094c8e51:data',text,*args)

        print server.get('\\TEST::TOP.ACTUATOR.H653094C8E51.DATA')

    elif stage==5:
        ods1=load_omas_nc('test.nc')
        print('Load OMAS data from netCDF')
        #print ods1

        ods1.to_imas()