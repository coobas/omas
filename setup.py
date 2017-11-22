from setuptools import setup
import os

install_requires = ['numpy', 'netCDF4', 'boto3', 'future']

extras_require = {'imas': ['imas'], 'build_structures': ['pandas', 'xlrd']}

# Add .json IMAS structure files to the package
here = os.path.abspath(os.path.split(__file__)[0]) + os.sep

# Automatically generate requirement.txt file if this is the OMAS repo and requirements.txt is missing
if os.path.exists(here + '.git') and not os.path.exists(here + 'requirements.txt'):
    print('Generating new requirements.txt')
    with open(here + 'requirements.txt', 'w') as f:
        f.write('#do not edit this file by hand\n#operate on setup.py instead\n#\n')
        f.write('#usage: pip install -r requirements.txt\n\n')
        for item in install_requires:
            f.write(item.ljust(20) + '# required\n')
        for requirement in extras_require:
            if requirement != 'imas':
                for item in extras_require[requirement]:
                    f.write(item.ljust(20) + '# %s\n' % requirement)

setup(
    name='omas',
    version='0.1.3',
    description='Ordered Multidimensional Array Structure',
    url='https://gafusion.github.io/omas',
    author='Orso Meneghini',
    license='MIT',
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],

    # What does your project relate to?
    keywords='integrated modeling OMFIT IMAS ITER',
    packages=['omas', 'omas.imas_structures.3_10_1'],
    package_data={
        'omas.imas_structures.3_10_1': ['*.json'],
    },
    install_requires=install_requires,
    extras_require={'imas': ['imas'],
                    'build_structures': ['pandas', 'xlrd']})
