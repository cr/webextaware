# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

from io import BytesIO
import logging
import pprint
import requests

logger = logging.getLogger(__name__)
amo_server = "https://addons.mozilla.org"
pp = pprint.PrettyPrinter(indent=4)


def download_matedata(all_pages=True):
    global logger
    url = amo_server + "/api/v3/addons/search/?sort=created&type=extension"
    metadata = []
    while True:
        logger.debug("Downloading `%s`" % url)
        list_response = requests.get(url)
        list_json = list_response.json()
        metadata += list_json["results"]
        if not list_json['next'] or not all_pages:
            break
        url = list_json['next']

    return metadata


def update_files(metadata, hash_fs):
    for ext in metadata:
        for ext_file in ext["current_version"]["files"]:
            if not ext_file["is_webextension"]:
                break
            ext_file_hash_type, ext_file_hash = ext_file["hash"].split(":")
            assert ext_file_hash_type == "sha256"
            if hash_fs.get(ext_file_hash) is None:
                response = requests.get(ext_file["url"])
                if response.status_code == 200:
                    pp.pprint(len(response.content))
                    hash_fs.put(BytesIO(response.content), ".zip")
                else:
                    logger.error("Unable to download `%s`, status code %d" % (ext_file["url"], response.status_code))


def do_something(metadata):
    for ext in metadata:
        pp.pprint(ext['current_version'])
        # compat_url = amo_server + "/api/v3/addons/addon/%s/feature_compatibility/" % ext['id'])
        zip_url = ext['current_version']['files'][0]['url']  # 0 might not be the latest public
        pp.pprint(zip_url)
    pp.pprint(len(metadata))