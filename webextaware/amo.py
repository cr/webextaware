# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import grequests
from io import BytesIO
import logging
import math
import requests


logger = logging.getLogger(__name__)
amo_server = "https://addons.mozilla.org"
MAX_CONCURRENT_REQUESTS = 10


def download_metadata(max_pages=(2 << 31), max_ext=(2 << 31), page_size=50):
    global logger

    # Maximum page_size seems to be 50 right now, 25 is AMO's current default.
    url = amo_server + "/api/v3/addons/search/"
    search_params = "sort=created" \
        "&type=extension" \
        "&app=firefox" \
        "&appversion=" + ",".join(map(str, range(57, 75))) + \
        "&page_size=%d" % page_size
    logger.debug("Search parameters for AMO query: %s" % search_params)

    # Grab page_size and count from first result page and calculate num_pages from that
    first_page = requests.get("%s?%s" % (url, search_params), verify=True).json()
    logger.info("There are currently %d web extensions listed" % first_page["count"])
    supported_page_size = int(first_page["page_size"])
    if page_size != supported_page_size:
        logger.warning("Requested size %d is greater than supported size %d" % (page_size, supported_page_size))
    num_pages = min(max_pages, int(math.ceil(first_page["count"] / supported_page_size)))
    if num_pages > 500:
        logger.warning("Truncating results to 500 pages (25000 results) due to API limitation")
        num_pages = 500
    logger.info("Fetching %d pages of AMO metadata" % num_pages)
    pages_to_get = ["%s?%s&page=%d" % (url, search_params, n) for n in range(2, num_pages + 1)]

    session = create_request_session()
    metadata = first_page["results"]
    while True:
        fatal_errors = 0
        unsent_requests = [grequests.get(url, verify=True, session=session) for url in pages_to_get]
        for response in grequests.imap(unsent_requests, size=MAX_CONCURRENT_REQUESTS):
            if 200 <= response.status_code < 400:
                logger.debug("Downloaded %d bytes from `%s`" % (len(response.content), response.url))
                metadata += response.json()["results"]
                try:
                    original_url = response.history[0].url
                except IndexError:
                    # There was no redirect
                    original_url = response.url
                pages_to_get.remove(original_url)
            else:
                logger.error("Unable to download `%s`, status code %d" % (response.url, response.status_code))
                if 400 <= response.status_code < 500:
                    fatal_errors += 1
            if len(pages_to_get) % 25 == 0:
                logger.info("%d pages to go" % len(pages_to_get))
        if len(pages_to_get) == fatal_errors:
            break

    if len(pages_to_get) > 0:
        logger.error("Unable to fetch %d pages. Please try again later later" % len(pages_to_get))
        return None

    if len(metadata) != first_page["count"]:
        logger.warning("Got %d instead of the expected %d results" % (len(metadata), first_page["count"]))

    return metadata[0:min(len(metadata), max_ext)]


def __as_chunks(flat_list, chunk_size):
    for i in range(0, len(flat_list), chunk_size):
        yield flat_list[i:i + chunk_size]


def update_files(metadata, hash_fs):
    urls_to_get = []
    for ext in metadata:
        for ext_file in ext["current_version"]["files"]:
            if not ext_file["is_webextension"]:
                continue
            ext_file_hash_type, ext_file_hash = ext_file["hash"].split(":")
            assert ext_file_hash_type == "sha256"
            if hash_fs.get(ext_file_hash) is None:
                if ext_file["url"] in urls_to_get:
                    logger.warning("Duplicate URL in metadata: %s" % ext_file["url"])
                urls_to_get.append(ext_file["url"])
            else:
                logger.debug("`%s` is already cached locally" % ext_file_hash)

    logger.info("Fetching %d uncached web extensions from AMO" % len(urls_to_get))

    session = create_request_session()

    while True:
        fatal_errors = 0
        unsent_requests = [grequests.get(url, verify=True, session=session) for url in urls_to_get]
        for response in grequests.imap(unsent_requests, size=MAX_CONCURRENT_REQUESTS):
            if response.status_code == 200:
                logger.debug("Downloaded %d bytes from `%s`" % (len(response.content), response.url))
                try:
                    hash_fs.put(BytesIO(response.content), ".zip")
                except ValueError as err:
                    # probably the mysterious ValueError: embedded null byte
                    logger.error("Unable to store `%s` in local cache: %s" % (response.url, str(err)))
                    continue
                try:
                    original_url = response.history[0].url
                except IndexError:
                    # There was no redirect
                    original_url = response.url
                urls_to_get.remove(original_url)
            else:
                logger.error("Unable to download `%s`, status code %d" % (response.url, response.status_code))
                if 400 <= response.status_code < 500:
                    fatal_errors += 1
            if len(urls_to_get) % 100 == 0:
                logger.info("%d extensions to go" % len(urls_to_get))

        if len(urls_to_get) == fatal_errors:
            break

    if len(urls_to_get) > 0:
        logger.warning("Unable to fetch %d extensions, likely deleted add-ons" % len(urls_to_get))


def create_request_session():
    # Share connections between requests to avoid overusing file descriptors.
    a = requests.adapters.HTTPAdapter(pool_maxsize=MAX_CONCURRENT_REQUESTS)
    session = requests.Session()
    session.mount('https://', a)
    return session
