# Web Extension Aware

[![PyPI Package version](https://badge.fury.io/py/webextaware.svg)](https://pypi.python.org/pypi/webextaware)


## Requirements
WebExtAware depends on other command line tools and Python modules, some of which require
libraries for building. You need to ensure that the following dependencies are met:
* grep

## Installation for users
WebExtAware requires **Python 3** to run. If that's what you have, you're good to go:
```
$ pip install [--user] webextaware
$ webextaware --help
```

Whether or not the `--user` flag is required depends on your Python installation. It is usually
not required on Macs with Homebrew while most Linux distributions can't do without it.

To use the `scan` sub command, you need to have a recent version of `node` and `npm` installed.
Check that they are installed and available:
```
$ node --version
v7.10.0
$ npm --version
4.2.0
```

## Installation for developers

Locally clone the repo, then cd there. Create a virtualenv and install with

```
virtualenv --always-copy --python=python3 venv
. venv/bin/activate
pip install -e .[dev]
```

As long as the virtualenv is active, the ```webextaware``` command is available.

## Metadata update

Sync all the AMO data with

```
webextaware sync
```

You may run into AMO's occasional 504s or an error about too many open files. In any case, re-run the following
command until all you get are persistent 404 errors:

```
webextaware sync -n
```

## Usage examples

Most commands accept selectors for selecting packages. Valid selectors are:

* any AMO ID like *737717*
* any extension file ID (sha256 hashes) like *2c8fc1861903551dac72bdbe9ec389bff8c417ba7217f6c738ac8d968939fc30*
* the keyword *all* for selecting everything the whole metadata set
* the keyword *orphans* for selecting extensions not referenced by the metadata set
* a regular expression that is matched against extension names

### info, query

Get some info on the cache state with

```
webextaware info
```

Query the metadata for known hashes or IDs:

```
webextaware query 835644
```

### stats

Write CSV with stats for all the extensions to terminal with

```
webextaware stats
```

### manifest, get, unzip

Show the manifests and paths of cache files associated with a specific AMO ID and
unzip them to the /tmp folder with

```
webextaware manifest 728674
webextaware get 728674
webextaware unzip 728674 -o /tmp
```

The last command prints a list of extracted folders.

Pass `-r` to the `manifest` subcommand to dump raw manifests. Pass `-t` to the manifest command
to get manifests in a grep-friendly line-based format.

```
webextaware manifest all -t | grep /optional_permissions:
```

You can unzip all the extensions to a specific folder with

```
webextaware unzip all -o /tmp/exts
```

It will print a list of folders where the extensions were extracted.

### grep

Grep for a regular expression in all or specific extensions with

```
webextaware grep optional_permissions
webextaware grep -- -A5 optional_permissions 739662
```

You can pass arguments to grep after a double dash.

### scan

Scan a web extension with retire.js and scanjs with

```
webextaware scan 739662
```

The result is formatted in JSON.
