import re

from setuptools import setup

install_requires = [
    "attrs>=17.2.0",
    "cached-property>=1.3.0; python_version<'3.8'",
    "isodate>=0.5.4",
    "lxml>=4.6.0",
    "platformdirs>=1.4.0",
    "requests>=2.7.0",
    "requests-toolbelt>=0.7.1",
    "requests-file>=1.5.1",
    "pytz",
]

docs_require = [
    "sphinx>=1.4.0",
]

async_require = ["httpx>=0.15.0"]

xmlsec_require = [
    "xmlsec>=0.6.1",
]

tests_require = [
    "coverage[toml]==5.2.1",
    "freezegun==0.3.15",
    "pretend==1.0.9",
    "pytest-cov==2.8.1",
    "pytest-httpx",
    "pytest-asyncio",
    "pytest==6.2.5",
    "requests_mock>=0.7.0",
    # Linting
    "isort==5.3.2",
    "flake8==3.8.3",
    "flake8-blind-except==0.1.1",
    "flake8-debugger==3.2.1",
    "flake8-imports==0.1.1",
]


with open("README.rst") as fh:
    long_description = re.sub(
        "^.. start-no-pypi.*^.. end-no-pypi", "", fh.read(), flags=re.M | re.S
    )

setup(
    name="zeep",
    version="4.2.1",
    description="A Python SOAP client",
    long_description=long_description,
    author="Michael van Tellingen",
    author_email="michaelvantellingen@gmail.com",
    url="https://docs.python-zeep.org",
    project_urls={
        "Source": "https://github.com/mvantellingen/python-zeep",
    },
    python_requires=">=3.7",
    install_requires=install_requires,
    tests_require=tests_require,
    extras_require={
        "docs": docs_require,
        "test": tests_require,
        "async": async_require,
        "xmlsec": xmlsec_require,
    },
    entry_points={},
    package_dir={"": "src"},
    packages=["zeep"],
    include_package_data=True,
    license="MIT",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
    ],
    zip_safe=False,
)
