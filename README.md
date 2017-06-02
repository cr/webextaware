# Web Extension Aware

## Installation

Locally clone the repo, then cd there. Create a virtualenv and install with

```
virtualenv --always-copy --python=python3 venv
. venv/bin/activate
pip install -e .
```

As long as the virtualenv is active, the ```webextaware``` command is available.

Install the node dependencies (ignore npm warnings) with

```
npm install
```

## Metadata update

Sync all the AMO data with

```
webextaware sync
```

You may run into AMO's occasional 504s or an error about too many open files. In any case, re-run the following
command until all you get are persistent 404 errors:

```
webextaware -n sync
```

## Usage examples

### info, query

Get some info on the current set with

```
webextaware info
```

Query the metadata for known hashes or IDs:

```
```

### stats

Print a tab-separated CSV with stats for all the extensions with

```
webextaware stats
```

### manifest, get, unzip

Show the manifests and paths of zip archives associated with a specific AMO ID and
unzip them to the /tmp folder with

```
webextaware manifest 728674
webextaware get 728674
webextaware unzip 728674 /tmp
```

The last command prints a list of extracted folders.

You can unzip all the extensions to a specific folder with

```
webextaware unzip all /tmp/exts
```

It will print a list of AMO IDS and folders where the extensions were extracted.

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
