from __future__ import absolute_import, print_function, division, unicode_literals

from omas_structure import *
from omas_json import *
from omas import omas

def imas_open(user, tokamak, version, shot, run, new=False):
    '''
    function to open an IMAS

    :param user: IMAS username

    :param tokamak: IMAS tokamak

    :param version: IMAS tokamak version

    :param shot: IMAS shot

    :param run: IMAS run id

    :param new: whether the open should create a new IMAS tree

    :return: IMAS ids
    '''
    import imas
    ids=imas.ids()
    ids.setShot(shot)
    ids.setRun(run)
    if new:
        ids.create_env(user,tokamak,version)
    else:
        ids.open_env(user,tokamak,version)
    if not ids.isConnected():
        raise(Exception('Failed to establish connection to IMAS database (user:%s tokamak:%s version:%s shot:%s run:%s)'%(user,tokamak,version,shot,run)))
    return ids

def imas_set(ids, jpath, value, skipMissingNodes=False, allocate=False):
    '''
    assign a value to a path of an open IMAS ids

    :param ids: open IMAS ids to write to

    :param jpath: IMAS path in json format

    :param value: value to assign

    :param skipMissingNodes:  if the IMAS path does not exists:
                             `False` raise an error
                             `True` does not raise error
                             `None` prints a warning message

    :param allocate: whether to perform only IMAS memory allocation (ids.resize)

    :return: jpath if set was done, otherwise None
    '''
    printd('setting: %s'%repr(jpath),topic='imas')
    ds=jpath[0]
    jpath=jpath[1:]

    if hasattr(ids,ds):
        m=getattr(ids,ds)
    elif skipMissingNodes is not False:
        if skipMissingNodes is None:
            printe('WARNING: %s is not part of IMAS structure'%j2i([ds]+jpath))
        return None
    else:
        raise(AttributeError('%s is not part of IMAS structure'%j2i([ds]+jpath)))
    m.setExpIdx(0)

    out=m
    for kp,p in enumerate(jpath):
        if isinstance(p,basestring):
            if hasattr(out,p):
                if kp<(len(jpath)-1):
                    out=getattr(out,p)
            elif skipMissingNodes is not False:
                if skipMissingNodes is None:
                    printe('WARNING: %s is not part of IMAS structure'%j2i([ds]+jpath))
                return None
            else:
                raise(AttributeError('%s is not part of IMAS structure'%j2i([ds]+jpath)))
        else:
            try:
                out=out[p]
            except IndexError:
                if not allocate:
                    raise(IndexError('%s structure array exceed allocation'%j2i([ds]+jpath)))
                printd('resizing: %d'%(p+1),topic='imas')
                out.resize(p+1)
                out=out[p]

    if allocate:
        return [ds]+jpath

    setattr(out,jpath[-1],value)
    m.put(0)
    return [ds]+jpath

def imas_get(ids, jpath, skipMissingNodes=False):
    '''
    read the value of a path in an open IMAS ids

    :param ids: open IMAS ids to read from

    :param jpath: IMAS path in json format

    :param skipMissingNodes:  if the IMAS path does not exists:
                             `False` raise an error
                             `True` does not raise error
                             `None` prints a warning message

    :return: the value that was read if successful or None otherwise

    '''
    printd('fetching: %s'%repr(jpath),topic='imas')
    ds=jpath[0]
    jpath=jpath[1:]

    if hasattr(ids,ds):
        m=getattr(ids,ds)
    elif skipMissingNodes is not False:
        if skipMissingNodes is None:
            printe('WARNING: %s is not part of IMAS structure'%j2i([ds]+jpath))
        return None
    else:
        raise(AttributeError('%s is not part of IMAS structure'%j2i([ds]+jpath)))

    m.get()

    out=m
    for kp,p in enumerate(jpath):
        if isinstance(p,basestring):
            if hasattr(out,p):
                out=getattr(out,p)
            elif skipMissingNodes is not False:
                if skipMissingNodes is None:
                    printe('WARNING: %s is not part of IMAS structure'%j2i([ds]+jpath))
                return None
            else:
                raise(AttributeError('%s is not part of IMAS structure'%j2i([ds]+jpath)))
        else:
            out=out[p]

    return out

def hmas_set(ids, jpath, hierarcy, *args, **kw):
    '''
    convenience function to assign data to a path of an open IMAS ids from a json hierarcy

    :param ids: open IMAS ids to write to

    :param jpath: IMAS path in json format

    :param hierarcy: json hierarchy

    :param skipMissingNodes:  if the IMAS path does not exists:
                             `False` raise an error
                             `True` does not raise error
                             `None` prints a warning message

    :param allocate: whether to perform only IMAS memory allocation (ids.resize)

    :return: jpath if set was done, otherwise None
    '''
    printd('',topic='imas')
    data=gethdata(hierarcy,jpath)['__data__']
    printd('.'.join(map(str,jpath)),data,topic='imas')
    return imas_set(ids,jpath,data,*args,**kw)

#---------------------------
# save and load OMAS to IMAS
#---------------------------
def save_omas_imas(ods, user, tokamak, version, shot, run, new=False):
    '''
    save OMAS data set to IMAS

    :param ods: OMAS data set

    :param user: IMAS username

    :param tokamak: IMAS tokamak

    :param version: IMAS tokamak version

    :param shot: IMAS shot

    :param run: IMAS run id

    :param new: whether the open should create a new IMAS tree

    :return: patsh that have been written to IMAS
    '''

    printd('Saving to IMAS: %s %s %s %d %d'%(user, tokamak, version, shot, run),topic='imas')

    hierarchy=ods_to_json(ods)
    paths=htraverse(hierarchy)[0]

    ids=imas_open(user, tokamak, version, shot, run, new)

    set_paths=[]
    for path in paths:
        set_paths.append( hmas_set(ids,path,hierarchy,None,allocate=True) )
    set_paths=filter(None,set_paths)

    for path in set_paths:
        if 'time' in path[:1] or path[-1]!='time':
            continue
        printd('writing %s'%j2i(path))
        hmas_set(ids,path,hierarchy,True)
    for path in set_paths:
        if 'time' in path[:1] or path[-1]=='time':
            continue
        printd('writing %s'%j2i(path))
        hmas_set(ids,path,hierarchy,True)
    return set_paths

def load_omas_imas(user, tokamak, version, shot, run, paths):
    ids=imas_open(user,tokamak,version,shot,run)
    hierarchy={}
    for path in paths:
        location = hierarchy
        for k in range(len(path)-1):
            step=path[k]
            next_step=path[k+1]
            if isinstance(step,basestring) and not isinstance(next_step,int):
                location.setdefault(step,{})
            elif isinstance(step,basestring) and isinstance(next_step,int):
                location.setdefault(step,[])
            else:
                for ks in range(step-len(location)+1):
                    location.append({})
            location=location[step]
        location[path[-1]]={'__data__':imas_get(ids,path,None)}
    pprint(hierarchy)
    return hierarchy

def test_omas_imas(ods):
    '''
    test save and load OMAS IMAS

    :param ods: ods

    :return: ods
    '''
    user=os.environ['USER']
    tokamak='D3D'
    version=os.environ.get('IMAS_VERSION','3.10.1')
    shot=1
    run=0

    paths=save_omas_imas(ods,user,tokamak,version,shot,run)#,True)
    ods=load_omas_imas(user,tokamak,version,shot,run,paths)

    return ods

#------------------------------
if __name__ == '__main__':
    print('='*20)

    from omas import omas_data_sample
    os.environ['OMAS_DEBUG_TOPIC']='imas'
    ods=omas_data_sample()

    ods=test_omas_imas(ods)
