#!/usr/bin/env python
from setuptools import setup
from imp import load_source
from os import path
import io

pkginfo = load_source("pkginfo.version", "gtirb_types/version.py")
__version__ = pkginfo.__version__

here = path.abspath(path.dirname(__file__))

with io.open(path.join(here, "requirements.txt"), encoding="utf-8") as f:
    install_requires = [x.strip() for x in f.read().split("\n")]

with io.open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="gtirb-types",
    author="GrammaTech, Inc.",
    version=__version__,
    description="Utilities for dealing with types in GTIRB",
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    keywords="",
    entry_points={
        "console_scripts": ["gtirb_types=gtirb_types.graph:main"],
    },
    package_dir={"gtirb_types": "gtirb_types"},
    packages=["gtirb_types"],
    include_package_data=True,
    install_requires=install_requires,
)
