import distutils
import setuptools
import subprocess
from distutils.command.build import build as _build

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="visualCaseGen",
    version="0.0.1",
    author="Alper Altuntas",
    author_email="altuntas@ucar.edu",
    description="A JupyterLab based Graphical User Interface for CESM create_newcase tool.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ESMCI/visualCaseGen",
    project_urls={
        "Bug Tracker": "https://github.com/pypa/visualCaseGen/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: LGPL-3 License",
        "Operating System :: Unix-like",
    ],
    package_dir={"": "visualCaseGen"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.8",
    install_requires=[
        'jupyterlab>3.2.0,<4',
        'ipywidgets>=7.6.5,<8',
        'PyYAML>=5.4,<6'
    ],
)