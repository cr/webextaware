# Web Extension Aware

## Usage

Locally clone the repo, then cd there. Create a virtualenv and install with

```
virtualenv --always-copy --python=python3 .
. bin/activate
pip install -e .
```

As long as the virtualenv is active, the ```webextaware``` command is available.

Install node dependencies (ignore npm warnings) with

```
npm install retire https://github.com/mozfreddyb/eslint-config-scanjs
```

Sync all the AMO data with

```
webextaware --debug sync
```

You may run into an error about too many open files. In any case, re-run the following command until all you see are persistent 404 errors:

```
webextaware --debug -n sync
```

Get some info on the current set with

```
webextaware info
```

Print a tab-separated CSV with stats for all the extensions with

```
webextaware stats
```

Show the manifests and paths of zip archives associated with a specific AMO ID and
unzip them to the /tmp folder with


```
webextaware manifest 728674
webextaware get 728674
webextaware unzip 728674 /tmp
```

The last command prints a list of extracted folders.
