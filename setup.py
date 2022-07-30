from distutils.core import setup

import pyltd2

CLASSIFIERS = [
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python",
    "Programming Language :: Python :: 3",
    "Topic :: Software Development",
    "Topic :: Utilities",
    "Operating System :: Microsoft",
    "Operating System :: MacOS",
    "Operating System :: POSIX :: Linux",
]

setup(
    name="pyltd2",
    version=pyltd2.__version__,
    description="Client package for the download of Legion TD 2 game data.",
    author="GCidd",
    url="https://github.com/GCidd/pyltd2",
    license="MIT",
    packages=[
        "pyltd2"
    ],
    include_package_data=True,
    install_requires=[
        "numpy >= 1.14.6",
        "pandas >= 1.4.3",
        "tqdm >= 4.64.0",
    ],
)