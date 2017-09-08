from setuptools import setup, find_packages

import versioneer
versioneer.VCS = 'git'
versioneer.versionfile_source = 'confmodel/_version.py'
versioneer.versionfile_build = 'confmodel/_version.py'
versioneer.tag_prefix = 'confmodel-'
versioneer.parentdir_prefix = 'confmodel-'


setup(
    name="confmodel",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    url='http://github.com/praekelt/confmodel',
    license='BSD',
    description="Declarative configuration access and validation system.",
    long_description=open('README.rst', 'r').read(),
    author='Praekelt Foundation',
    author_email='dev@praekeltfoundation.org',
    packages=find_packages(),
    install_requires=[
        'six>=1.10.0,<2.0',
        'zope.interface',
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
