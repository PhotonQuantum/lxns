#!/usr/bin/env python3

from setuptools import setup

import lxns


setup(
    name='lxns',
    version=lxns.__version__,
    description='A container helper for nspawn',
    author='LightQuantum',
    author_email='cy.n01@outlook.com',
    packages=[
        'lxns',
    ],
    package_data={
        "lxns": ["templates/*"]
    },
    url='https://github.com/PhotonQuantum/lxns',
    keywords=['container'],
    classifiers=(
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3 :: Only',
    ),
    install_requires=[
        'fire',
        'prettytable',
        'loguru',
        'python-slugify'
    ],
    entry_points={
        'console_scripts': [
            "lxns=lxns.__main__:main",
        ]
    },
)
