#!/usr/bin/env python3

import setuptools

setuptools.setup(
    name="d2_docker",
    version="1.18.0",
    description="Dockers for DHIS2 instances",
    long_description=open("README.md", encoding="utf-8").read(),
    keywords=["python"],
    author="EyeSeeTea Team",
    url="https://github.com/eyeseetea/d2-docker",
    packages=setuptools.find_packages("src"),
    package_dir={"": "src"},
    include_package_data=True,
    install_requires=open("requirements.txt").readlines(),
    python_requires=">=3.10",
    zip_safe=False,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    entry_points={"console_scripts": [
        "d2-docker=d2_docker.cli:main",
    ]},
)
