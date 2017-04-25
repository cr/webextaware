# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from setuptools import setup, find_packages

PACKAGE_VERSION = '0.0.1a'

# Dependencies
with open('requirements.txt') as f:
    dependencies = f.read().splitlines()

setup(
    name='webextaware',
    version=PACKAGE_VERSION,
    description='WebExtensions Security Analyzer',
    classifiers=[],
    keywords='mozilla',
    author='Christiane Ruetten',
    author_email='cr@mozilla.com',
    url='https://github.com/cr/webextaware',
    license='MPL',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=True,
    install_requires=dependencies,
    entry_points={
        "console_scripts": [
            "webextaware = main:main"
        ]
    }
)
