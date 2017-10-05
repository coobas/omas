from __future__ import absolute_import, print_function, division, unicode_literals
from omas_utils import *

#--------------------------------------------
# generation of the imas structure json files
#--------------------------------------------
def aggregate_imas_html_docs(imas_html_dir, imas_version):
    '''
    this function aggregates all of the IMAS html documentation pages
    into a single clean.html page that is stored under the imas_structures folder.
        omas/imas_structures/<imas_version>/clean.html

    This clean.html page is then --MANUALLY--:
    1. opened in EXCEL
    2. in EXCEL all cells are un-merged
    3. the EXCEL document is finally saved as clean.xls
        omas/imas_structures/<imas_version>/clean.xls

    :param imas_html_dir: directory where the IMAS html documentation is stored

    :param imas_version: IMAS version
    '''
    from bs4 import BeautifulSoup

    files=glob.glob(imas_html_dir+'/*.html')

    line='<table><tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr></table>'

    tables=[line%('Full path name','Description','Data Type','Coordinates')]
    for file in files:
        print(file)
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
structure_time['imas_coords']=['1...N']
structure_time['data_type']='INT_1D'
structure_time['base_coord']=True
structure_time['hash']=md5_hasher('time')
structure_time['full_path']='time'

fix={}
fix['ic/surface_current/n_pol']='ic/surface_current/n_tor'
fix['waveform/value.time']='waveform/time'
fix['unit/beamlets_group/beamlets/positions/R']='unit/beamlets_group/beamlets/positions/r'
fix['grid/rho_tor_norm']='distribution/profiles_1d/grid/rho_tor_norm'
fix['distribution/grid/rho_tor_norm']='distribution/profiles_1d/grid/rho_tor_norm'
fix['distribution/profiles_2d/grid/grid/rho_tor_norm']='distribution/profiles_1d/grid/rho_tor_norm'
fix['grid/theta_straight']='distribution/profiles_2d/grid/theta_straight'
fix['distribution/profiles_2d/grid/grid/grid/theta_straight']='distribution/profiles_2d/grid/theta_straight'

def create_json_structure(imas_version, data_structures=[]):
    '''
    This function generates the OMAS structures .json files
    after the clean.xml file is been manually generated.
        omas/imas_structures/<imas_version>/clean.html

    :param imas_version: IMAS version

    :param data_structures: list of data_structures to generate.
                             All data structures are generated if `data_structures==[]`
    '''
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
    if not len(data_structures):
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
                        for k1 in range(len(entries[k][col])):
                            if entries[k][col][k1].startswith('1...N_'):
                                entries[k][col][k1]=re.sub('1...N_(.*)s',r'\1_index',entries[k][col][k1]).lower()
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
            structure[entries[k]['full_path']]['imas_coords']=copy.deepcopy(entries[k]['coordinates'])

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
                struct_array[:]=struct_array+[key]
                if structure[key]['coordinates'][0].startswith('1...'):
                    structure[key]['coordinates'][0]=key
            else:
                for k in struct_array[::-1]:
                    if key not in structure[k]['coordinates']:
                        structure[key]['coordinates']=structure[k]['coordinates']+structure[key]['coordinates']

        #find base coordinates
        base_coords=[]
        for key in structure.keys():
            coords=structure[key]['coordinates']
            d=structure[key]['data_type']
            for c in coords:
                if c.startswith('1...') and 'struct' not in d:
                    base_coords.append( re.sub('(_error_upper|_error_lower|_error_index)$','',key) )
                    structure[ re.sub('(_error_upper|_error_lower|_error_index)$','',key) ]['base_coord']=True
        base_coords=numpy.unique(base_coords).tolist()

        #find independent coordinates
        for key in structure.keys():
            if 'base_coord' in structure[key]:
                if len(structure[key]['coordinates'])==1:
                    structure[key]['independent_coordinate']=True
                else:
                    key_c=key+'_coordinate'
                    structure[key_c]={}
                    structure[key_c]['description']='imas missing dimension'
                    structure[key_c]['coordinates']=['1...N']
                    structure[key_c]['imas_coords']=['1...N']
                    structure[key_c]['data_type']='INT_1D'
                    structure[key_c]['base_coord']=True
                    structure[key_c]['independent_coordinate']=True
                    structure[key]['coordinates'][-1]=key_c
                    for key1 in structure.keys():
                        for k,c in enumerate(structure[key1]['coordinates']):
                            if c==key:
                                structure[key1]['coordinates'][k]=key_c

        #make sure all coordinates exist
        for key in structure.keys():
            if 'base_coord' in structure[key] and len(structure[key]['coordinates'])==1:
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
                        structure[c]['imas_coords']=['1...N']
                        structure[c]['data_type']='INT_1D'
                        structure[c]['base_coord']=True

        #prepend structure name to all entries
        for key in structure.keys():
            for what in ['coordinates','imas_coords']:
                for k,c in enumerate(structure[key][what]):
                    if c.startswith('1...'):
                        continue
                    structure[key][what][k]=section+'/'+c
            structure[section+'/'+key]=structure[key]
            del structure[key]

        #unify time dimensions
        for key in structure.keys():
            if key.endswith('/time'):
                del structure[key]
            else:
                for what in ['coordinates','imas_coords']:
                    coords=structure[key][what]
                    for k,c in enumerate(coords):
                        if c.endswith('/time'):
                            coords[k]='time'
        structure['time']=structure_time

        #convert separator
        for key in structure.keys():
            for item in ['coordinates','imas_coords']:
                for k,c in enumerate(structure[key][item]):
                    structure[key][item][k]=re.sub('/',separator,structure[key][item][k])
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

def create_html_documentation(imas_version):
    filename=os.path.abspath(os.sep.join([imas_json_dir,imas_version,'omas_doc.html']))

    rows={}
    for structure_file in load_structure():
        print('Adding to html documentation: '+os.path.splitext(os.path.split(structure_file)[1])[0])
        structure=load_structure(structure_file)[0]
        for item in structure:
            if not any([ item.endswith(k) for k in ['_error_index','_error_lower','_error_upper']]):
                rows[item]="<tr><td><p>{item}</p></td><td><p>{coordinates}</p></td><td><p>{data_type}</p></td><td><p>{description}</p></td></tr>".format(
                    item=item,
                    coordinates=re.sub(',',',<br>',str(map(str,structure[item]['coordinates']))),
                    description=structure[item]['description'],
                    data_type=structure[item]['data_type']#type_mapper(structure[item]['data_type']),
                )

    lines=[]
    lines.append("<table border=1, width='100%'>")
    lines.append("<tr><th>OMAS name</th><th>OMAS dimensions</th><th>Type</th><th>Description</th></tr>")
    for row in sorted(rows.keys()):
        lines.append(rows[row])
    lines.append('</table>')

    with open(filename,'w') as f:
        f.write('\n'.join(lines))

#----------------------------------------------
# must be run to generate necessary .json files
#----------------------------------------------
if __name__ == '__main__' and os.path.exists(imas_html_dir):

    if not os.path.exists(os.sep.join([imas_json_dir,imas_version,'clean.xls'])):
        aggregate_imas_html_docs(imas_html_dir, imas_version)

    create_json_structure(imas_version,['equilibrium'])

    create_html_documentation(imas_version)