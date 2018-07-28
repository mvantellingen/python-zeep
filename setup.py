import re
import sys

from setuptools import find_packages, setup

install_requires = [
    'appdirs>=1.4.0',
    'attrs>=17.2.0',
    'cached-property>=1.3.0',
    'defusedxml>=0.4.1',
    'isodate>=0.5.4',
    'lxml>=3.1.0',
    'requests>=2.7.0',
    'requests-toolbelt>=0.7.1',
    'six>=1.9.0',
    'pytz',
]

docs_require = [
    'sphinx>=1.4.0',
]

tornado_require = [
    'tornado>=4.0.2,<5'
]

async_require = []  # see below

xmlsec_require = [
    'xmlsec>=0.6.1',
]

tests_require = [
    'freezegun==0.3.8',
    'mock==2.0.0',
    'pretend==1.0.8',
    'pytest-cov==2.5.1',
    'pytest==3.1.3',
    'requests_mock>=0.7.0',
    'pytest-tornado==0.4.5',

    # Linting
    'isort==4.2.15',
    'flake8==3.3.0',
    'flake8-blind-except==0.1.1',
    'flake8-debugger==1.4.0',
    'flake8-imports==0.1.1',
]


if sys.version_info > (3, 4, 2):
    async_require.append('aiohttp>=1.0')
    tests_require.append('aioresponses>=0.4.1')


with open('README.rst') as fh:
    long_description = re.sub(
        '^.. start-no-pypi.*^.. end-no-pypi', '', fh.read(), flags=re.M | re.S)

setup(
    name='zeep',
    version='3.1.0',
    description='A modern/fast Python SOAP client based on lxml / requests',
    long_description=long_description,
    author="Michael van Tellingen",
    author_email="michaelvantellingen@gmail.com",
    url='http://docs.python-zeep.org',

    install_requires=install_requires,
    tests_require=tests_require,
    extras_require={
        'docs': docs_require,
        'test': tests_require,
        'async': async_require,
        'tornado': tornado_require,
        'xmlsec': xmlsec_require,
    },
    entry_points={},
    package_dir={'': 'src'},
    packages=['zeep'],
    include_package_data=True,
    license='MIT',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],
    zip_safe=False,
)
