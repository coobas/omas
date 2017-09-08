import imas

from omas_structure import *
from omas_json import *
from omas import omas

def imas_open(user,tokamak,version,shot,run,new=False):
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

def imas_set(ids,path,value,skipMissingNodes=False):
    printd('setting: %s'%repr(path),topic='imas')
    ds=path[0]
    path=path[1:]

    m=getattr(ids,ds)
    m.setExpIdx(0)

    out=m
    for p in path[:-1]:
        if isinstance(p,basestring):
            out=getattr(out,p)
        else:
            try:
                out=out[p]
            except IndexError:
                printd('resizing: %d'%(p+1),topic='imas')
                out.resize(2) #issue:resizing must be done once before data write
                out=out[p]
    if hasattr(out,path[-1]):
        setattr(out,path[-1],value)
        m.put(0)
        return [ds]+path
    elif skipMissingNodes is not False:
        if skipMissingNodes is None:
            printe('WARNING: %s is not part of IMAS structure'%human_redeable_path([ds]+path))
        return None
    else:
        raise(AttributeError('%s is not part of IMAS structure'%human_redeable_path([ds]+path)))

def imas_get(ids,path,skipMissingNodes=False):
    printd('fetching: %s'%repr(path),topic='imas')
    ds=path[0]
    path=path[1:]

    if hasattr(ids,ds):
        m=getattr(ids,ds)
    elif skipMissingNodes is not False:
        if skipMissingNodes is None:
            printe('WARNING: %s is not part of IMAS structure'%human_redeable_path([ds]+path))
        return None
    else:
        raise(AttributeError('%s is not part of IMAS structure'%human_redeable_path([ds]+path)))

    m.get()

    out=m
    for p in path:
        if isinstance(p,basestring):
            if hasattr(out,p):
                out=getattr(out,p)
            elif skipMissingNodes is not False:
                if skipMissingNodes is None:
                    printe('WARNING: %s is not part of IMAS structure'%human_redeable_path([ds]+path))
                return None
            else:
                raise(AttributeError('%s is not part of IMAS structure'%human_redeable_path([ds]+path)))
        else:
            out=out[p]

    return out

def hmas_set(ids,path,hierarcy,*args,**kw):
    printd('',topic='imas')
    data=gethdata(hierarcy,path)['__data__']
    printd('.'.join(map(str,path)),data,topic='imas')
    return imas_set(ids,path,data,*args,**kw)

def save_omas_imas(ods, user, tokamak, version, shot, run, new=False):
    hierarchy=d2h(ods)
    paths=htraverse(hierarchy)[0]

    ids=imas_open(user, tokamak, version, shot, run, new)
    set_paths=[]
    for path in paths:
        if 'time' in path[:1] or path[-1]!='time':
            continue
        printd('writing %s'%human_redeable_path(path))
        set_paths.append( hmas_set(ids,path,hierarchy,True) )
    for path in paths:
        if 'time' in path[:1] or path[-1]=='time':
            continue
        printd('writing %s'%human_redeable_path(path))
        set_paths.append( hmas_set(ids,path,hierarchy,None) )
    return filter(None,set_paths)

#------------------------------
if __name__ == '__main__':
    print('='*20)
    if True:
        from omas_nc import *
        ods=load_omas_nc('test.nc')

        paths=save_omas_imas(ods,'meneghini','D3D','3.10.1',1,0)#,True)

        ids=imas_open('meneghini','D3D','3.10.1',1,0)
        for path in paths:
            print('%s = %s'%(human_redeable_path(path),repr(imas_get(ids,path,None))))
