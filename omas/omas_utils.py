from __future__ import print_function, division, unicode_literals

from .omas_setup import *
import sys

# --------------------------
# general utility functions
# --------------------------
def printd(*objects, **kw):
    """
    debug print
    environmental variable OMAS_DEBUG_TOPIC sets the topic to be printed
    """
    topic = kw.pop('topic', '')
    if isinstance(topic, basestring):
        topic = [topic]
    topic = list(map(lambda x: x.lower(), topic))
    objects = ['DEBUG:'] + list(objects)
    topic_selected=os.environ.get('OMAS_DEBUG_TOPIC', '')
    dump=False
    if topic_selected.endswith('_dump'):
        dump=True
        topic_selected=re.sub('_dump$','',topic_selected)
    if topic_selected and (topic_selected == '*' or topic_selected in topic or '*' in topic):
        printe(*objects, **kw)
        if dump:
            fb=StringIO.StringIO()
            print(*objects[1:],file=fb)
            with open('omas_dump.txt','a') as f:
                f.write(fb.getvalue())
            fb.close()

def printe(*objects, **kw):
    """
    print to stderr
    """
    kw['file'] = sys.__stderr__
    print(*objects, **kw)


def is_uncertain(var):
    '''
    :param var: Variable or array to test
    :return: True if variable is instance of uncertainties or
             array of shape var with elements indicating uncertainty
    '''
    def uncertain_check(x):
        return isinstance(x, uncertainties.core.AffineScalarFunc)
    if numpy.iterable(var):
        # TODO this fails for some iterables, most notably strings
        # TODO creating numpy arrays is quite an overhead
        # original fix with numpy
        # return numpy.reshape(numpy.fromiter(map(uncertain_check, numpy.array(var).flat),
        #                                     dtype=numpy.array(var).dtype),
        #                      numpy.array(var).shape)
        return [is_uncertain(x) for x in var]
    else:
        return uncertain_check(var)


def json_dumper(obj):
    """
    function used to dump objects to json format

    :param obj: input ojbect

    :return: json-compatible [dict/list] object
    """
    from omas import omas
    if isinstance(obj, omas):
        return OrderedDict(zip(obj.keys(), obj.values()))
    elif numpy.atleast_1d(is_uncertain(obj)).any():
        nomv=nominal_values(obj)
        return dict(__udarray_tolist_avg__=nomv.tolist(),
                    __udarray_tolist_std__=std_devs(obj).tolist(),
                    dtype=str(nomv.dtype),
                    shape=obj.shape)
    elif isinstance(obj, numpy.ndarray):
        if 'complex' in str(obj.dtype).lower():
            return dict(__ndarray_tolist_real__=obj.real.tolist(),
                        __ndarray_tolist_imag__=obj.imag.tolist(),
                        dtype=str(obj.dtype),
                        shape=obj.shape)
        else:
            return dict(__ndarray_tolist__=obj.tolist(),
                        dtype=str(obj.dtype),
                        shape=obj.shape)
    elif isinstance(obj, numpy.generic):
        return numpy.asscalar(obj)
    elif isinstance(obj, complex):
        return dict(__complex__=True, real=obj.real, imag=obj.imag)
    return obj.toJSON()


def json_loader(object_pairs, cls=dict):
    """
    function used to load json-objects generated by the json_dumper function

    :param object_pairs: json-compatible [dict/list] object

    :param cls: dicitonary class to use

    :return: ojbect
    """
    object_pairs = map(lambda o: (o[0], o[1]), object_pairs)
    dct = cls()
    for x, y in object_pairs:
        dct[x] = y
    if '__ndarray_tolist__' in dct:
        return numpy.array(dct['__ndarray_tolist__'], dtype=dct['dtype']).reshape(dct['shape'])
    elif '__ndarray_tolist_real__' in dct and '__ndarray_tolist_imag__' in dct:
        return (numpy.array(dct['__ndarray_tolist_real__'], dtype=dct['dtype']).reshape(dct['shape']) +
                numpy.array(dct['__ndarray_tolist_imag__'], dtype=dct['dtype']).reshape(dct['shape']) * 1j)
    elif '__udarray_tolist_avg__' in dct and '__udarray_tolist_std__' in dct:
        return uarray(numpy.array(dct['__udarray_tolist_avg__'], dtype=dct['dtype']).reshape(dct['shape']),
                      numpy.array(dct['__udarray_tolist_std__'], dtype=dct['dtype']).reshape(dct['shape']))
    elif '__ndarray__' in dct:
        import base64
        data = base64.b64decode(dct['__ndarray__'])
        return numpy.frombuffer(data, dct['dtype']).reshape(dct['shape'])
    elif '__complex__' in dct:
        return complex(dct['real'], dct['imag'])
    return dct


def _credentials(system):
    c = {'s3': {}}
    c['s3']['region_name'] = 'us-east-1'
    c['s3']['aws_access_key_id'] = 'AKIAIDWE2IM2V73OGOPA'
    c['s3']['aws_secret_access_key'] = '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'
    return c[system]


def remote_uri(uri, filename, action):
    """
    :param uri: uri of the container of the file

    :param filename: filename to act on

    :param action: must be one of [`up`, `down`, `list`, `del`]
    """
    if not re.match('\w+://\w+.*', uri):
        return uri

    tmp = uri.split('://')
    system = tmp[0]
    location = '://'.join(tmp[1:])

    if action not in ['down', 'up', 'list', 'del']:
        raise (AttributeError('remote_uri action attribute must be one of [`up`, `down`, `list`, `del`]'))

    if system == 's3':
        import boto3
        from boto3.s3.transfer import TransferConfig
        s3bucket = location.split('/')[0]
        s3connection = boto3.resource('s3', **_credentials('s3'))
        s3filename = '/'.join(location.split('/')[1:])

        if action == 'list':
            printd('Listing %s' % (uri), topic='s3')
            files=map(lambda x:x.key,s3connection.Bucket(s3bucket).objects.all())
            s3filename=s3filename.strip('/')
            if s3filename:
                files=filter(lambda x:x.startswith(s3filename),files)
            return files

        if action == 'del':
            if filename is None:
                filename = s3filename.split('/')[-1]
            printd('Deleting %s' % uri, topic='s3')
            s3connection.Object(s3bucket, s3filename).delete()

        elif action == 'down':
            if filename is None:
                filename = s3filename.split('/')[-1]
            printd('Downloading %s to %s' % (uri, filename), topic='s3')
            obj = s3connection.Object(s3bucket, s3filename)
            if not os.path.exists(os.path.abspath(os.path.split(filename)[0])):
                os.makedirs(os.path.abspath(os.path.split(filename)[0]))
            obj.download_file(filename,Config=TransferConfig(use_threads=False))

        elif action == 'up':
            printd('Uploading %s to %s' % (filename, uri), topic='s3')
            from botocore.exceptions import ClientError
            if s3filename.endswith('/'):
                s3filename += filename.split('/')[-1]
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
            with open(filename, 'rb') as data:
                bucket.put_object(Key=s3filename, Body=data)  # , Metadata=meta)


def remove_parentheses(inv, replace_with=''):
    '''
    function used to remove/replace top-level matching parenthesis from a string

    :param inv: input string

    :param replace_with: string to replace matching parenthesis with

    :return: input string without first set of matching parentheses
    '''
    k = 0
    lp = ''
    out = ''
    for c in inv:
        # go one level deep
        if c == '(':
            k += 1
            lp = c
        # go one level up
        elif c == ')':
            k -= 1
            lp += c
            if k == 0:
                out += replace_with
        # zero depth: add character to output string
        elif k == 0:
            out += c
    return out


# ----------------------------------------------
# handling of OMAS json structures
# ----------------------------------------------
_structures = {}
_structures_dict = {}


def list_structures(imas_version):
    return list(map(lambda x: os.path.splitext(os.path.split(x)[1])[0],
                    glob.glob(imas_json_dir + os.sep + re.sub('\.', '_', imas_version) + os.sep + '*' + '.json')))


def load_structure(filename, imas_version):
    """
    load omas json structure filename

    :param filename: full path or IDS string

    :param imas_version: imas version to load the data schema of (ignored if filename is a full path)

    :return: tuple with structure, hashing mapper, and ods
    """
    if os.sep not in filename:
        filename = imas_json_dir + os.sep + re.sub('\.', '_', imas_version) + os.sep + filename + '.json'
        if not os.path.exists(filename):
            if not os.path.exists(os.path.split(filename)[0]) or not os.path.exists(os.path.split(filename)[0]+os.sep+'info.json'):
                raise (Exception('`%s` is not a valid IMAS structure directory.\n'
                                 'Perhaps the structure files for IMAS version %s must be generated.\n'
                                 'Try running the `omas/samples/build_json_structures.py` script.'% (os.path.split(filename)[0],imas_version)))
            else:
                raise (Exception('`%s` is not a valid IMAS structure' % filename))
        else:
            filename = os.path.abspath(filename)
    if filename not in _structures:
        _structures[filename] = json.loads(open(filename, 'r').read(), object_pairs_hook=json_loader)
        _structures_dict[filename] = {}
        for item in _structures[filename]:
            h = _structures_dict[filename]
            for step in re.sub('\[:\]', '.:', item).split(separator):
                if step not in h:
                    h[step] = {}
                h = h[step]

    return _structures[filename], _structures_dict[filename]


def o2i(path):
    """
    Formats a ODS path format into a IMAS path

    :param path: ODS path format

    :return: IMAS path format
    """
    ipath = path[0]
    for step in path[1:]:
        if isinstance(step, int):
            ipath += "[%d]" % step
        else:
            ipath += '.%s' % step
    return ipath


def ids_cpo_mapper(ids, cpo=None):
    '''
    translate (some) IDS fields to CPO

    :param ids: input omas data object (IDS format) to read

    :param cpo: optional omas data object (CPO format) to which to write to

    :return: cpo
    '''
    from omas import omas
    if cpo is None:
        cpo = omas()
    cpo.consistency_check = False

    for itime in range(len(ids['core_profiles.time'])):

        if 'equilibrium' in ids:
            cpo['equilibrium'][itime]['time'] = ids['equilibrium.time'][itime]
            cpo['equilibrium'][itime]['profiles_1d.q'] = ids['equilibrium.time_slice'][itime]['profiles_1d.q']
            cpo['equilibrium'][itime]['profiles_1d.rho_tor'] = ids['equilibrium.time_slice'][itime]['profiles_1d.rho_tor']
            for iprof in range(len(ids['equilibrium.time_slice'][itime]['profiles_2d'])):
                cpo['equilibrium'][itime]['profiles_2d'][iprof]['psi'] = ids['equilibrium.time_slice'][itime]['profiles_2d'][iprof]['psi']

        if 'core_profiles' in ids:
            cpo['coreprof'][itime]['te.value'] = ids['core_profiles.profiles_1d'][itime]['electrons.temperature']
            cpo['coreprof'][itime]['ne.value'] = ids['core_profiles.profiles_1d'][itime]['electrons.density']
            pdim = len(cpo['coreprof'][itime]['te.value'])
            idim = len(ids['core_profiles.profiles_1d[0].ion'])
            cpo['coreprof'][itime]['ni.value'] = numpy.zeros((pdim, idim))
            cpo['coreprof'][itime]['ti.value'] = numpy.zeros((pdim, idim))
            for iion in range(len(ids['core_profiles.profiles_1d'][itime]['ion'])):
                if 'density' in ids['core_profiles.profiles_1d'][itime]['ion'][iion]:
                    cpo['coreprof'][itime]['ni.value'][:, iion] = ids['core_profiles.profiles_1d'][itime]['ion'][iion]['density']
                cpo['coreprof'][itime]['ti.value'][:, iion] = nominal_values(ids['core_profiles.profiles_1d'][itime]['ion'][iion]['temperature'])

    return cpo
