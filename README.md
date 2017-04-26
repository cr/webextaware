# Web Extension Aware

## Usage

Locally clone the repo, then cd there. Create a virtualenv and install with

```
virtualenv --always-copy --python=python3 .
. bin/activate
pip install -e .
```

As long as the virtualenv is active, the ```webextaware``` command is available.

Sync all the data with

```
webextaware --debug sync
```

If you run into an error about too many open files, rerun the following command until everything is downloaded:

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