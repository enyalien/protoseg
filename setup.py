#!/usr/bin/env python

import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setuptools.setup(name='protoseg',
                 version='0.0.3',
                 description='Prototyped Segmentation',
                 long_description=long_description,
                 long_description_content_type="text/markdown",
                 license='MIT',
                 author='chriamue',
                 author_email='chriamue@gmail.com',
                 url="https://github.com/chriamue/protoseg",
                 install_requires=requirements,
                 extras_require={
                     'visualize': ['pydot>=1.2.4'],
                     'tests': ['pytest',
                               'pytest-pep8',
                               'pytest-xdist',
                               'pytest-cov',
                               'pytest-dependency'],
                 },
                 packages=setuptools.find_packages(),
                 classifiers=(
                     "Intended Audience :: Developers",
                     "Intended Audience :: Education",
                     "Intended Audience :: Science/Research",
                     "Programming Language :: Python :: 3",
                     "License :: OSI Approved :: MIT License",
                     "Operating System :: OS Independent",
                 ), entry_points='''
                    [console_scripts]
                    protoseg-submit=protoseg.cli.submit:main
                    protoseg-train=protoseg.cli.train:main
                    ''',
                 )
