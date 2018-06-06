#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
"""

from importlib import import_module
from setuptools import setup, find_packages


PKG_NAME = 'py_gql'
PKG_AUTHOR = 'Charles Lirsac'
PKG_AUTHOR_EMAIL = 'c.lirsac@gmail.com'
PKG_URL = ''


def run_setup():
    with open('README.md') as f:
        readme = '\n' + f.read()

    with open('LICENSE') as f:
        license_ = f.read()

    _requirements = '''
    six >= 1.11.0
    '''

    requirements = [
        line for line in (line.strip() for line in _requirements.split('\n'))
        if line and not line.startswith('#')
    ]

    version = import_module('%s.__version__' % PKG_NAME).__version__

    setup(
        name=PKG_NAME,
        version=version,
        description=__doc__.split('\n')[0],
        long_description=readme,
        author=PKG_AUTHOR,
        author_email=PKG_AUTHOR_EMAIL,
        # url='',
        license=license_,
        packages=find_packages(exclude=('tests', 'docs')),
        install_requires=requirements,
        include_package_data=True,
        classifiers=[
            # Trove classifiers
            # Full list: https://pypi.python.org/pypi?%3Aaction=list_classifiers
            'License :: OSI Approved :: MIT License',
            'Programming Language :: Python',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.6',
            'Programming Language :: Python :: 2',
            'Programming Language :: Python :: 2.7',
            'Programming Language :: Python :: Implementation :: CPython',
        ],
        # entry_points={
        #     'console_scripts': ['mycli=mymodule:cli'],
        # },
    )


if __name__ == '__main__':
    run_setup()
