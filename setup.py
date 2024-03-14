from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="wayfire",
    version="1.0.0",
    author="Killown",
    author_email="systemofdown@gmail.com",
    description="python module to control wayfire compositor",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/killown/waypy",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
