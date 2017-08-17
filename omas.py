__all__=['omas', 'save_omas_nc', 'load_omas_nc']

import xarray
import os
import sys
import glob
import json

imas_json_dir=str(os.path.abspath(os.path.dirname(unicode(__file__, sys.getfilesystemencoding()))))+'/imas_json/'

fix={}
fix['ic.surface_current.n_pol']='ic.surface_current.n_tor'
fix['waveform.value.time']='waveform.time'
fix['unit.beamlets_group.beamlets.positions.R']='unit.beamlets_group.beamlets.positions.r'

separator='.'

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

    cols=[str(col) for col in data if not col.startswith('Unnamed')]

    #split clean.xls into sections
    sections=OrderedDict()
    tbl=None
    for k in range(len(data[cols[0]])):
        if isinstance(data['Full path name'][k],basestring) and '---BREAK---' in data['Full path name'][k]:
            tbl=data['Description'][k]
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
            if isinstance(data['Full path name'][k],basestring) and not data['Full path name'][k].startswith('Lifecycle'):
                entry=entries[k]={}
            for col in cols:
                entry.setdefault(col,[])
                if isinstance(data[col][k],basestring):
                    entry[col].append( str( data[col][k].encode('utf-8').decode('ascii',errors='ignore') ) )

        #remove obsolescent entries and content of each cell
        for k in sorted(entries.keys()):
            if k not in entries.keys():
                continue

            if 'obsolescent' in '\n'.join(entries[k]['Full path name']):
                basepath='\n'.join(entries[k]['Full path name']).strip().split('\n')[0]
                for k1 in entries.keys():
                    if basepath in '\n'.join(entries[k1]['Full path name']):
                        del entries[k1]
            else:

                for col in cols:
                    if col=='Full path name':
                        entries[k][col]='\n'.join(entries[k][col]).strip().split('\n')[0]
                        entries[k][col]=re.sub(r'\([^)]*\)','',entries[k][col])
                        entries[k][col]=fix.get(entries[k][col],entries[k][col])
                    elif col=='Coordinates':
                        entries[k][col]=map(lambda x:re.sub('^[0-9]+- ','',x),entries[k][col])
                        entries[k][col]=map(lambda x:remove_parentheses(x),entries[k][col])
                        entries[k][col]=map(lambda x:fix.get(x,x),entries[k][col])
                        entries[k][col]=map(lambda x:x.split(' OR ')[0],entries[k][col])
                        entries[k][col]=map(lambda x:x.split('IDS:')[-1],entries[k][col])
                    elif col=='Data Type':
                        entries[k][col]='\n'.join(entries[k][col])
                        if entries[k][col]=='int_type':
                            entries[k][col]='INT_0D'
                        elif entries[k][col]=='flt_type':
                            entries[k][col]='INT_0D'
                    else:
                        entries[k][col]='\n'.join(entries[k][col])

        #convert to flat dictionary
        for k in entries:
            structure[entries[k]['Full path name']]={}
            for col in cols:
                if col!='Full path name':
                    structure[entries[k]['Full path name']][col]=entries[k][col]

        #concatenate descriptions
        lmax=max(map(len,'/'.join(structure.keys()).split('/')))
        for key in structure.keys():
            path='* '+key.split('/')[-1].ljust(lmax)
            structure[key]['Description']=path+': '+structure[key]['Description']
        for key in structure.keys():
            if '/' in key:
                basepath='/'.join(key.split('/')[:-1])
                basedesc=structure[basepath]['Description']
                structure[key]['Description']=basedesc+'\n'+structure[key]['Description']
        for key in structure.keys():
            structure[key]['Description']=structure[key]['Description']

        #handle arrays of structures
        struct_array=[]
        for key in sorted(structure.keys()):
            for k in struct_array[::-1]:
                if k not in key:
                    struct_array.pop()
            if 'struct_array' in structure[key]['Data Type']:
                for k,c in enumerate(structure[key]['Coordinates']):
                    struct_array.append(key)
                    if not c.startswith('1...'): #add a dimension to this coordinate
                        structure[c]['Coordinates'].append('1...N')
            else:
                for k in struct_array[::-1]:
                    if key not in structure[k]['Coordinates']:
                        structure[key]['Coordinates']=structure[k]['Coordinates']+structure[key]['Coordinates']

        #find fundamental coordinates
        base_coords=[]
        for key in structure.keys():
            coords=structure[key]['Coordinates']
            d=structure[key]['Data Type']
            for c in coords:
                if c.startswith('1...') and 'struct' not in d:
                    base_coords.append( re.sub('(_error_upper|_error_lower|_error_index)$','',key) )
                    structure[ re.sub('(_error_upper|_error_lower|_error_index)$','',key) ]['base_coordinate']=True
        base_coords=numpy.unique(base_coords).tolist()

        #make sure all coordinates exist
        for key in structure.keys():
            if 'base_coordinate' in structure[key] and len(structure[key]['Coordinates'])==1:
                #structure[key]['independent_coordinate']=True
                continue
            coords=structure[key]['Coordinates']
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
                        structure[c]['Description']='imas missing dimension'
                        structure[c]['Coordinates']=['1...N']
                        structure[c]['Data Type']='INT_1D'
                        structure[c]['base_coordinate']=True

        #prepend structure name to all entries
        for key in structure.keys():
            for k,c in enumerate(structure[key]['Coordinates']):
                if c.startswith('1...'):
                    continue
                structure[key]['Coordinates'][k]=section+'/'+c
            structure[section+'/'+key]=structure[key]
            del structure[key]

        #unify time dimensions
        for key in structure.keys():
            if key.endswith('/time'):
                del structure[key]
            else:
                coords=structure[key]['Coordinates']
                for k,c in enumerate(coords):
                    if c.endswith('/time'):
                        coords[k]='time'

        #convert separator
        for key in structure.keys():
            for k,c in enumerate(structure[key]['Coordinates']):
                structure[key]['Coordinates'][k]=re.sub('/',separator,structure[key]['Coordinates'][k])
            structure[re.sub('/',separator,key)]=structure[key]
            del structure[key]

        #deploy imas structures as json
        json_string=json.dumps(structure, indent=1, separators=(',',': '))
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
            structure=json.loads(open(imas_json_dir+os.sep+self.attrs['imas_version']+os.sep+data_structure+'.json','r').read())
            self._structure[data_structure]=structure
            self.attrs['structure_'+data_structure]=repr(self._structure[data_structure])

        #consistency checks
        structure=self._structure[data_structure]

        if key not in structure:
            if len(value.dims)==1 and value.dims[0]==key:
                return
            raise(Exception('Entry `%s` is not part of the `%s` data structure'%(key,data_structure)))

        if 'base_coordinate' in structure[key]:
            return

        coords=structure[key]['Coordinates']
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
                value.attrs['Description']='\n'+structure[key]['Description']

        tmp=xarray.Dataset.__setitem__(self, key, value)
        return tmp

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

    #stage #1 must be run to generate necessary .json files
    stage=1

    if stage==0:
        aggregate_html_docs(imas_html_dir,imas_version)

    elif stage==1:
        create_json_structure(imas_version)

    elif stage==2:
        ods=omas()
        ods['time']=xarray.DataArray(numpy.atleast_1d(1000),
                              dims=['time'])

        ods['equilibrium.time_slice.global_quantities.ip']=xarray.DataArray(numpy.atleast_1d(1E6),
                                                             dims=['time'])

        print(ods['equilibrium.time_slice.global_quantities.ip'].attrs['Description'])
        print(ods)

        save_omas_nc(ods,'test.nc')

        ods1=load_omas_nc('test.nc')
        print(ods1)
