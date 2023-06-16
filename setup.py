import setuptools
from pathlib import Path


root_dir = Path(__file__).absolute().parent
with (root_dir / "VERSION").open() as f:
    version = f.read()
with (root_dir / "requirements.in").open() as f:
    requirements = f.read().splitlines()

setuptools.setup(
    name="api2gn",
    version=version,
    description="api2gn",
    maintainer="PNE",
    # url='https://github.com/PnX-SI/gn_module_monitoring',
    packages=setuptools.find_packages("api2gn"),
    package_dir={"": "."},
    install_requires=requirements,
    tests_require=[],
    entry_points={
        "console_scripts": ["gn-parser = api2gn.main:cli"],
        "gn_module": [
            "code = api2gn:MODULE_CODE",
            "blueprint = api2gn.blueprint:blueprint",
            "config_schema = api2gn.config_schema:Api2GNSchema",
            "migrations = api2gn:migrations",
        ],
    },
    classifiers=[
        "Development Status :: 1 - Planning",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: GNU Affero General Public License v3"
        "Operating System :: OS Independent",
    ],
)
