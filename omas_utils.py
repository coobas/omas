from __future__ import absolute_import, print_function, division, unicode_literals

from omas_setup import *

#--------------------------
# general utility functions
#--------------------------
def printd(*objects, **kw):
    '''
    debug print
    environmental variable OMAS_DEBUG_TOPIC sets the topic to be printed
    '''
    topic=kw.pop('topic','')
    if isinstance(topic,basestring):
        topic=[topic]
    topic=map(lambda x:x.lower(),topic)
    objects=['DEBUG:']+list(objects)
    if os.environ.get('OMAS_DEBUG_TOPIC','') in topic or ('*' in topic and len(os.environ.get('OMAS_DEBUG_TOPIC',''))):
        print(*objects, **kw)

def printe(*objects, **kw):
    '''
    print to stderr
    '''
    kw['file']=sys.__stderr__
    print(*objects, **kw)

def json_dumper(obj):
    '''
    function used to dump objects to json format

    :param obj: input ojbect

    :return: json-compatible [dict/list] object
    '''
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
    '''
    function used to load json-objects generated by the json_dumper function

    :param obj: json-compatible [dict/list] object

    :return: ojbect
    '''
    object_pairs=map(lambda o:(o[0],o[1]),object_pairs)
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
    '''
    function used to remove matching parenthesis from a string
    :param inv: input string
    :return: input string without first set of matching parentheses
    '''
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
    '''
    shortened md5sum hash used for storing OMAS objects in MDS+
    this is necessary due to a limitation in the MDS+ implementation
    which limits the maximum length of a node string to 12 characters
    MDS+ also requires that the nodes names starts with a string,
    hence the leading `H` in front of the hash.

    :param inv: input string

    :return: shortened md5sum hash
    '''
    return str('H'+md5(inv).hexdigest()[:11]).upper()

def credentials(system):
    c={}
    c['s3']={}
    c['s3']['region_name']='us-east-1'
    c['s3']['aws_access_key_id']='AKIAIDWE2IM2V73OGOPA'
    c['s3']['aws_secret_access_key']='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'
    return c[system]

def remote_uri(uri, filename, up_down):
    '''

    :param uri:
    :param filename:
    :param up_down:
    :return:
    '''
    if not re.match('\w+://\w+.*',uri):
        return uri

    tmp=uri.split('://')
    system=tmp[0]
    location='://'.join(tmp[1:])

    if up_down not in ['down','up']:
        raise(AttributeError('remote_uri up_down attribute must be set to either `up` or `down`'))

    if system=='s3':
        import boto3
        s3bucket=location.split('/')[0]
        s3connection = boto3.resource('s3',**credentials('s3'))
        s3filename='/'.join(location.split('/')[1:])

        if up_down=='down':
            if filename is None:
                filename=s3filename.split('/')[-1]
            printd('Downloading %s to %s'%(uri,filename),topic='s3')
            obj=s3connection.Object(s3bucket, s3filename)
            obj.download_file(os.path.split(filename)[1])

        elif up_down=='up':
            printd('Uploading %s to %s'%(filename,uri),topic='s3')
            from botocore.exceptions import ClientError
            if s3filename.endswith('/'):
                s3filename+=filename.split('/')[-1]
            try:
                s3connection.meta.client.head_bucket(Bucket=s3bucket)
            except ClientError as _excp:
                # If a client error is thrown, then check that it was a 404 error.
                # If it was a 404 error, then the bucket does not exist.
                error_code = int(_excp.response['Error']['Code'])
                if error_code == 404:
                    s3connection.create_bucket(Bucket=s3bucket)
                else:
                    raise
            bucket = s3connection.Bucket(s3bucket)
            data = open(filename, 'rb')
            bucket.put_object(Key=s3filename, Body=data)#, Metadata=meta)

def equal_ods(ods1,ods2):
    equal=True
    k1=set(ods1.keys())
    k2=set(ods2.keys())
    for k in k1.difference(k2):
        print('DIFF: key `%s` missing in 2nd ods'%k)
        equal=False
    for k in k2.difference(k1):
        print('DIFF: key `%s` missing in 1st ods'%k)
        equal=False
    for k in k1.intersection(k2):
        if not numpy.allclose(ods1[k].values,ods2[k].values):
            print('DIFF: `%s` differ in value'%k)
            print(ods1[k].values)
            print(ods2[k].values)
            equal=False
        a1=set(ods1[k].attrs)
        a2=set(ods2[k].attrs)
        for a in a1.difference(a2):
            print('DIFF: attr `%s` missing in key `%s` of 2nd ods'%(a,k))
            equal=False
        for a in a2.difference(a1):
            print('DIFF: attr `%s` missing in key `%s` of 1st ods'%(a,k))
            equal=False
    return equal

def type_mapper(kind):
    mapper={'struct':'',
            'flt':'float',
            'int':'int',
            'str':'str'}
    for k in mapper:
        if k in kind.lower():
            return mapper[k]

#-----------------
# path conversions
#-----------------
def m2o(mpath):
    '''
    translates an OMAS MDS+ path to a OMAS path

    :param mpath: string with the OMAS path

    :return: string with OMAS path
    '''
    ods=mpath.split('TOP'+separator)[1].split(separator)[0].lower()
    hash=mpath.split('TOP'+separator)[1].split(separator)[1].split(':')[0]
    meta=load_structure(ods)[1][hash]
    return meta['full_path']

def o2m(tree, opath):
    '''
    translates an OMAS path to an OMAS MDS+ path

    :param opath: string with OMAS path

    :return: string with the OMAS path
    '''
    ods=opath.split(separator)[0]
    hash=md5_hasher(opath)
    return ('\\%s::TOP.%s.%s'%(tree,ods,hash)).upper()

def j2i(jpath):
    '''
    Formats a json path as a IMAS path

    :param jpath: json path, that is a list with strings and indices

    :return: IMAS path
    '''
    ipath=jpath[0]
    for step in jpath[1:]:
        if isinstance(step,int):
            ipath+="[%d]"%step
        else:
            ipath+='.%s'%step
    return ipath

def j2o(jpath):
    '''
    Formats a json path as a OMAS path

    :param jpath: json path, that is a list with strings and indices

    :return: OMAS path
    '''
    return separator.join(filter(lambda x:isinstance(x,basestring), jpath ))

def htraverse(hierarchy, **kw):
    '''
    traverse the json hierarchy and returns its info

    :param hierarchy: json hierarchy

    :return: paths_out, dests_out, mapper
    '''

    # json paths in the hierarchy
    paths=kw.setdefault('paths',[])
    #json paths skipping the arrays
    dests=kw.setdefault('dests',[])
    #mapper dictionary that tells for each of the entries in `dests` what are the corresponding entries in `paths`
    mapper=kw.setdefault('mapper',{})
    #all of the fundamental dimensions in the json hierarchy
    dims=kw.setdefault('dims',[])

    paths_in=paths
    paths_out=[]

    dests_in=dests
    dests_out=[]

    dims_in=dims

    #handle dict
    if isinstance(hierarchy,dict):
        for kid in hierarchy.keys():
            if not kid.startswith('__'):
                paths=paths_in+[kid]
                dests=dests_in+[kid]
                dims=dims_in
                tmp=htraverse(hierarchy[kid],paths=paths,dests=dests,mapper=mapper,dims=dims)
                paths_out.extend( tmp[0] )
                dests_out.extend( tmp[1] )
                mapper.update(    tmp[2] )
            elif kid.startswith('__data__'):
                paths_out.append(paths)
                dests_out.append(dests)
                dims=copy.deepcopy(dims_in)
                dims.extend( hierarchy['__dims__'] )
                mapper.setdefault(separator.join(dests),{'path':[],'dims':dims})
                mapper[separator.join(dests)]['path'].append(paths)

    #handle list
    elif isinstance(hierarchy,list) and len(hierarchy):
        for k in range(len(hierarchy)):
            paths=paths_in+[k]
            dests=dests_in
            dims=copy.deepcopy(dims_in)
            dims.extend(info_node(separator.join(dests_in))['coordinates'])
            tmp=htraverse(hierarchy[k],paths=paths,dests=dests,mapper=mapper,dims=dims)
            paths_out.extend( tmp[0] )
            dests_out.extend( tmp[1] )
            mapper.update(    tmp[2] )

    return paths_out, dests_out, mapper

def gethdata(hierarchy, path):
    '''
    get data from path in json hierarchy

    :param hierarchy: json hierarchy

    :param path: path in the json hierarchy

    :return: data at path in json hierarchy
    '''
    h=hierarchy
    for step in path:
        h=h[step]
    return h

#----------------------------------------------
# handling of OMAS json structures
#----------------------------------------------
_structures={}
_structures_by_hash={}
def load_structure(file=None):
    '''
    load omas json structure file

    :param file:

    :return: tuple with structure, hashing mapper, and ods
    '''
    if file is None:
        return glob.glob(imas_json_dir+os.sep+imas_version+os.sep+'*'+'.json')
    if os.sep not in file:
        file=glob.glob(imas_json_dir+os.sep+imas_version+os.sep+file+'*'+'.json')[0]
    if file not in _structures:
        _structures[file]=json.loads(open(file,'r').read(),object_pairs_hook=json_loader)
        _structures_by_hash[file]={}
        for item in _structures[file]:
            _structures_by_hash[_structures[file][item]['hash']]=_structures[file][item]
    ods=_structures[file].keys()[0].split(separator)[0]
    return _structures[file], _structures_by_hash, ods

def info_node(node):
    '''
    return omas structure attributes for a node

    :param node: node in the omas data structure

    :return: attributes of the node
    '''
    data_structure=node.split(separator)[0]
    structure=load_structure(data_structure)[0]
    return structure[node]

#------------------------------
if __name__ == '__main__':

    from omas import ods_sample
    os.environ['OMAS_DEBUG_TOPIC']='*'

    uri='s3://omas3/{username}/'.format(username=os.environ['USER'])
    remote_uri(uri,'test.nc','up')

    remote_uri(uri+'test.nc','test_downS3.nc','down')