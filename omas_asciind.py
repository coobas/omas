from __future__ import absolute_import, print_function, division, unicode_literals

from omas_structure import *
from omas import omas

#-----------------------------
# save and load OMAS to ascii-ND
#-----------------------------
def save_omas_asciind(ods, filename, order='C'):
    '''
    Save an OMAS data set to ascii-ND

    :param ods: OMAS data set

    :param order: 'C' means to flatten in row-major (C-style) order. 'F' means to flatten in column-major (Fortran- style) order.

    :param filename: directory to save to
    '''

    printd('Saving OMAS data to ascii-ND: %s'%filename, topic='asciind')

    if not os.path.exists(filename):
        os.makedirs(filename)

    for item in ods.keys():
        with open(filename+os.sep+item,'w') as f:
            f.write(' '.join(ods[item].dims)+'\n')
            f.write(' '.join(map(lambda x:'%d'%x,ods[item].shape))+'\n')
            f.write(order+'\n')
            f.write(' '.join(map(lambda x:'%g'%x,ods[item].values.flatten(order=order))))

def load_omas_asciind(filename, **kw):
    '''
    Load an OMAS data set from ascii-ND

    :param filename: directory to load from

    :return: OMAS data set
    '''

    printd('Loading OMAS data to ascii-ND: %s'%filename, topic='asciind')

    items=[]
    for item in glob.glob(filename+os.sep+'*'):
        items.append( os.path.split(item)[1] )

    #identify dependencies
    dependencies=[]
    for item in items:
        with open(filename+os.sep+item,'r') as f:
            dependencies+=f.readline().split()
    dependencies=numpy.unique(dependencies).tolist()

    #load dependencies first
    ods=omas()
    for item in items:
        if item in dependencies:
            printd('Reading: '+filename+os.sep+item,topic='asciind')
            with open(filename+os.sep+item,'r') as f:
                dims=f.readline().split()
                shape=tuple(map(int,f.readline().split()))
                order=f.readline().strip()
                data=numpy.reshape(map(float,f.readline().split()),shape,order=order)
            ods[item]=xarray.DataArray(data,dims=dims)

    #load others then
    for item in items:
        if item not in dependencies:
            printd('Reading: '+filename+os.sep+item,topic='asciind')
            with open(filename+os.sep+item,'r') as f:
                dims=f.readline().split()
                shape=tuple(map(int,f.readline().split()))
                order=f.readline().strip()
                data=numpy.reshape(map(float,f.readline().split()),shape,order=order)
            ods[item]=xarray.DataArray(data,dims=dims,coords={dim:ods[dim] for dim in dims})

    return ods

def test_omas_asciind(ods):
    '''
    test save and load NetCDF

    :param ods: ods

    :return: ods
    '''
    filename='test.asciind'
    save_omas_asciind(ods,filename,'F')
    ods1=load_omas_asciind(filename)
    equal_ods(ods,ods1)
    return ods1

#------------------------------
if __name__ == '__main__':

    from omas import omas_data_sample
    os.environ['OMAS_DEBUG_TOPIC']='asciind'
    ods=omas_data_sample()

    ods=test_omas_asciind(ods)