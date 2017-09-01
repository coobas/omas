from omas_setup import *

def u2s(x):
    if isinstance(x,unicode):
        #convert unicode to string if unicode encoding is unecessary
        xs=x.encode('utf-8')
        if xs==x: return xs
    if isinstance(x,list):
        return map(lambda x:u2s(x),x)
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

def is_uncertain(var):
    '''return True if variable is instance of uncertainties'''
    def uncertain_check(x):
        return isinstance(x,uncertainties.Variable) or isinstance(x,uncertainties.AffineScalarFunc)
    if numpy.iterable(var):
        return numpy.reshape(numpy.array(map(uncertain_check,numpy.array(var).flat)),numpy.array(var).shape)
    else:
        return uncertain_check(var)

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

def md5_hasher(inv):
    return str('H'+md5(inv).hexdigest()[:11]).upper()

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

structure_time={}
structure_time['description']='common time basis'
structure_time['coordinates']=['1...N']
structure_time['data_type']='INT_1D'
structure_time['base_coord']=True
structure_time['hash']=md5_hasher('time')
structure_time['full_path']='time'

fix={}
fix['ic.surface_current.n_pol']='ic.surface_current.n_tor'
fix['waveform.value.time']='waveform.time'
fix['unit.beamlets_group.beamlets.positions.R']='unit.beamlets_group.beamlets.positions.r'

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
        structure['time']=structure_time

        #convert separator
        for key in structure.keys():
            for k,c in enumerate(structure[key]['coordinates']):
                structure[key]['coordinates'][k]=re.sub('/',separator,structure[key]['coordinates'][k])
            tmp=structure[key]
            del structure[key]
            structure[re.sub('/',separator,key)]=tmp

        #save full_path_name and hash as part of json structure
        for key in structure.keys():
            structure[key]['hash']=md5_hasher(key)
            structure[key]['full_path']=key

        #deploy imas structures as json
        #pprint(structure)
        json_string=json.dumps(structure, default=json_dumper, indent=1, separators=(',',': '))
        open(imas_json_dir+os.sep+imas_version+os.sep+section+'.json','w').write(json_string)

_structures={}
_structures_by_hash={}
def load_structure(file):
    if os.sep not in file:
        file=glob.glob(imas_json_dir+os.sep+imas_version+os.sep+file+'*'+'.json')[0]
    if file not in _structures:
        _structures[file]=json.loads(open(file,'r').read(),object_pairs_hook=json_loader)
        _structures_by_hash[file]={}
        for item in _structures[file]:
            _structures_by_hash[_structures[file][item]['hash']]=_structures[file][item]
    ids=_structures[file].keys()[0].split(separator)[0]
    return _structures[file],_structures_by_hash,ids

#----------------------------------------------
# must be run to generate necessary .json files
#----------------------------------------------
if __name__ == '__main__' and os.path.exists(imas_html_dir):

    if not os.path.exists(os.sep.join([imas_json_dir,imas_version,'clean.xls'])):
        aggregate_html_docs(imas_html_dir,imas_version)

    create_json_structure(imas_version)