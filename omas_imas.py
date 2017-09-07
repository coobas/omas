import imas

from omas_structure import *
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

def imas_set(ids,path,value):
    ds=path[0]
    path=path[1:]

    m=getattr(ids,ds)
    m.setExpIdx(0)

    out=m
    for p in path[:-1]:
        if isinstance(p,basestring):
            out=getattr(out,p)
        else:
            if p in out:
                out=out[p]
            else:
                out.resize(p+1)
                out=out[p]
    setattr(out,path[-1],value)
    m.put()
    return out

def imas_get(ids,path):
    ds=path[0]
    path=path[1:]

    m=getattr(ids,ds)
    m.get()

    out=m
    for p in path:
        if isinstance(p,basestring):
            out=getattr(out,p)
        else:
            out=out[p]

    return out

#------------------------------
if __name__ == '__main__':
    ids=imas_open('meneghini','D3D','3.10.1',1,0)
    imas_set(ids,['magnetics','flux_loop',0,'name'],'bla2')

    ids=imas_open('meneghini','D3D','3.10.1',1,0)
    print imas_get(ids,['magnetics','flux_loop',0,'name'])

