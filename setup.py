import re
from setuptools import find_packages, setup

install_requires = [
    'appdirs>=1.4.0',
    'cached-property>=1.0.0',
    'defusedxml>=0.4.1',
    'isodate>=0.5.4',
    'lxml>=3.0.0',
    'requests>=2.7.0',
    'six>=1.9.0',
    'pytz',
]

docs_require = [
    'sphinx>=1.4.0',
]

tests_require = [
    'freezegun==0.3.8',
    'mock==2.0.0',
    'pretend==1.0.8',
    'pytest-cov==2.4.0',
    'pytest==3.0.5',
    'requests_mock>=0.7.0',

    # Linting
    'isort==4.2.5',
    'flake8==3.2.1',
    'flake8-blind-except==0.1.1',
    'flake8-debugger==1.4.0',
]

with open('README.rst') as fh:
    long_description = re.sub(
        '^.. start-no-pypi.*^.. end-no-pypi', '', fh.read(), flags=re.M | re.S)

setup(
    name='zeep',
    version='0.24.0',
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
    },
    entry_points={},
    package_dir={'': 'src'},
    packages=find_packages('src'),
    include_package_data=True,

    license='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],
    zip_safe=False,
)
