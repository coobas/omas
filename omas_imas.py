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

def imas_set(ids,path,value):
    print('setting: %s'%repr(path))
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
                print('resizing: %d'%(p+1))
                out.resize(2) #issue:resizing must be done once before data write
                out=out[p]
    setattr(out,path[-1],value)
    m.put(0)
    return out

def imas_get(ids,path):
    print('fetching: %s'%repr(path))
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

def hmas_set(ids,path,hierarcy):
    print()
    data=gethdata(hierarcy,path)['__data__']
    print('.'.join(map(str,path)),data)
    return imas_set(ids,path,data)

#------------------------------
if __name__ == '__main__':
    print('='*20)
    if True:
        from omas_nc import *
        ods=load_omas_nc('test.nc')

        hierarchy=d2h(ods)
        paths=htraverse(hierarchy)[0]
        ids=imas_open('meneghini','D3D','3.10.1',1,0,True)
        hmas_set(ids,['equilibrium','time_slice',0,'time'],hierarchy)
        hmas_set(ids,['equilibrium','time_slice',1,'time'],hierarchy)
        hmas_set(ids,['equilibrium','time_slice',0,'global_quantities','ip'],hierarchy)
        hmas_set(ids,['equilibrium','time_slice',1,'global_quantities','ip'],hierarchy)
        print imas_get(ids,['equilibrium','time_slice',0,'time'])
        print imas_get(ids,['equilibrium','time_slice',1,'time'])
        print imas_get(ids,['equilibrium','time_slice',0,'global_quantities','ip'])
        print imas_get(ids,['equilibrium','time_slice',1,'global_quantities','ip'])

    else:
        ids=imas_open('meneghini','D3D','3.10.1',1,0)
        imas_set(ids,['magnetics','time'],numpy.linspace(0,1))
        imas_set(ids,['magnetics','flux_loop',0,'name'],'bla2')
        imas_set(ids,['magnetics','flux_loop',0,'flux','data'],numpy.linspace(0,1))
        print imas_get(ids,['magnetics','flux_loop',0,'name'])
        print imas_get(ids,['magnetics','flux_loop',0,'flux','data'])

