# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from setuptools import setup, find_packages

PACKAGE_NAME = "webextaware"
PACKAGE_VERSION = "1.2.4"

INSTALL_REQUIRES = [
    "coloredlogs",
    "gevent",
    "grequests",
    "hashfs",
    "ipython",
    "json-cfg",
    "requests",
    "pynpm",
    "python-magic",
    "urllib3"
]

TESTS_REQUIRE = [
    "coverage",
    "mock",
    "pytest",
    "pytest-runner"
]

DEV_REQUIRES = [
    "coverage",
    "mock",
    "nose",
    "pycodestyle",
    "pytest",
    "pytest-runner",
    "radon"
]

setup(
    name=PACKAGE_NAME,
    version=PACKAGE_VERSION,
    description="Mozilla WebExtensions Security Analyzer",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",
        "Natural Language :: English",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Security",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: Software Development :: Testing",
        "Topic :: Utilities"
    ],
    keywords=["mozilla", "firefox", "browser", "addons", "web extensions", "testing", "security"],
    author="Christiane Ruetten",
    author_email="cr@mozilla.com",
    url="https://github.com/cr/webextaware",
    download_url="https://github.com/cr/webextaware/archive/latest.tar.gz",
    license="MPL2",
    packages=find_packages(exclude=["tests"]),
    include_package_data=True,  # See MANIFEST.in
    zip_safe=False,
    use_2to3=False,
    install_requires=INSTALL_REQUIRES,
    tests_require=TESTS_REQUIRE,
    extras_require={"dev": DEV_REQUIRES},  # For `pip install -e .[dev]`
    entry_points={
        "console_scripts": [
            "webextaware = webextaware.main:main"
        ]
    }
)
