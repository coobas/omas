from __future__ import print_function, division, unicode_literals

from .omas_setup import *

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
    topic=list(map(lambda x:x.lower(),topic))
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

def json_loader(object_pairs, cls=dict):
    '''
    function used to load json-objects generated by the json_dumper function

    :param obj: json-compatible [dict/list] object

    :return: ojbect
    '''
    object_pairs=map(lambda o:(o[0],o[1]),object_pairs)
    dct=cls()
    for x,y in object_pairs:
        dct[x]=y
    if '__ndarray_tolist__' in dct:
        return numpy.array(dct['__ndarray_tolist__'],dtype=dct['dtype']).reshape(dct['shape'])
    elif ('__ndarray_tolist_real__' in dct and
          '__ndarray_tolist_imag__' in dct):
          return (numpy.array(dct['__ndarray_tolist_real__'],dtype=dct['dtype']).reshape(dct['shape'])+
                  numpy.array(dct['__ndarray_tolist_imag__'],dtype=dct['dtype']).reshape(dct['shape'])*1j)
    elif '__ndarray__' in dct:
        data = base64.b64decode(dct['__ndarray__'])
        return np.frombuffer(data, dct['dtype']).reshape(dct['shape'])
    elif '__complex__' in dct:
        return complex(dct['real'],dct['imag'])
    return dct

def _credentials(system):
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
        s3connection = boto3.resource('s3',**_credentials('s3'))
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

#----------------------------------------------
# handling of OMAS json structures
#----------------------------------------------
_structures={}

def list_structures(imas_version=default_imas_version):
    return list(map(lambda x:os.path.splitext(os.path.split(x)[1])[0],glob.glob(imas_json_dir+os.sep+imas_version+os.sep+'*'+'.json')))

def load_structure(file, imas_version=default_imas_version):
    '''
    load omas json structure file

    :param file:

    :return: tuple with structure, hashing mapper, and ods
    '''
    if os.sep not in file:
        filename=imas_json_dir+os.sep+imas_version+os.sep+file+'.json'
        if not os.path.exists(filename):
            raise(Exception('`%s` is not a valid IMAS structure'%file))
        else:
            file=os.path.abspath(filename)
    if file not in _structures:
        _structures[file]=json.loads(open(file,'r').read(),object_pairs_hook=json_loader)
    return _structures[file]

def o2i(path):
    '''
    Formats a ODS path format into a IMAS path

    :param path: ODS path format

    :return: IMAS path format
    '''
    ipath=path[0]
    for step in path[1:]:
        if isinstance(step,int):
            ipath+="[%d]"%step
        else:
            ipath+='.%s'%step
    return ipath
