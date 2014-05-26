from setuptools import setup

import os.path

# copy README.markdown to README
if os.path.exists("README.markdown"):
    with open("README", "w") as of:
        of.write(open("README.markdown").read())

VERSION = "0.5.0"
README = open("README").read()

setup(
    author="The Magnificant Nick",
    name="toil",
    version=VERSION,
    long_description=README,
    packages=["toil"],
    entry_points={
        "console_scripts": [
            "toil = toil.core:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
    ]
)
