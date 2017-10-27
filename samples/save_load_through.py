from omas import *

# load some sample data
ods_start = ods_sample()

# save/load Python pickle
filename = 'test.pkl'
save_omas_pkl(ods_start, filename)
ods = load_omas_pkl(filename)

# save/load ASCII Json
filename = 'test.json'
save_omas_json(ods, filename)
ods = load_omas_json(filename)

# save/load NetCDF
filename = 'test.nc'
save_omas_nc(ods, filename)
ods = load_omas_nc(filename)

# remote save/load S3
filename = 'test.s3'
save_omas_s3(ods, filename)
ods = load_omas_s3(filename)

# save/load IMAS
user = os.environ['USER']
tokamak = 'D3D'
version = os.environ.get('IMAS_VERSION','3.10.1')
shot = 1
run = 0
new = True
paths = save_omas_imas(ods,  user, tokamak, version, shot, run, new)
ods_end = load_omas_imas(user, tokamak, version, shot, run, paths)

# check data
if not different_ods(ods_start, ods_end):
   print('OMAS data got saved to and loaded correctly throughout')