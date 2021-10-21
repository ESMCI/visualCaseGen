import distutils
import setuptools
import subprocess

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()


class CheckoutCESM(distutils.cmd.Command):
    description = 'Run manage_externals to check out the CESM source code'
    user_options = [('verbose','v','verbose log')]

    def initialize_options(self):
        self.verbose = False

    def finalize_options(self):
        pass

    def run(self):
        subprocess.run('./manage_externals/checkout_externals -o', shell=True, capture_output=True, cwd='./CESM')


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
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "visualCaseGen"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.8",
    install_requires=[
        'jupyterlab>3.2.0,<4',
        'ipywidgets>=7.6.5,<8',
        'PyYAML>=5.4,<6'
    ],
    cmdclass={
        'checkout_cesm':CheckoutCESM, 
    }
)