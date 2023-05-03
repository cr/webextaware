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


def download_metadata(max_pages=(2 << 31), max_ext=(2 << 31), page_size=50, min_users=0, max_users=0):
    """
    Retrieves the metadata for all public extensions.
    If specified, limit to extensions with at least |min_users| users.
    If specified, limit to extensions with less than |max_users| users.

    Returns an array of addon results from the AMO API as described at
    https://addons-server.readthedocs.io/en/latest/topics/api/addons.html#addon-detail-object
    """
    global logger

    # Maximum page_size seems to be 50 right now, 25 is AMO's current default.
    url = amo_server + "/api/v5/addons/search/"
    search_params = "sort=created" \
        "&type=extension" \
        "&app=firefox" \
        "&page_size=%d" % page_size
    if min_users:
        search_params += "&users__gte=%d" % min_users
    if max_users:
        search_params += "&users__lt=%d" % max_users
    logger.debug("Search parameters for AMO query: %s" % search_params)

    extra_desc = ""
    if min_users and max_users:
        extra_desc += ", with at least %d and less than %d users" % (min_users, max_users)
    elif min_users:
        extra_desc += ", with at least %d users" % min_users
    elif max_users:
        extra_desc += ", with less than %d users" % max_users

    # Grab page_size and count from first result page and calculate num_pages from that
    first_page = requests.get("%s?%s" % (url, search_params), verify=True).json()
    logger.info("There are currently %d web extensions listed%s" % (first_page["count"], extra_desc))
    supported_page_size = int(first_page["page_size"])
    if page_size != supported_page_size:
        logger.warning("Requested size %d is greater than supported size %d" % (page_size, supported_page_size))
    num_pages = min(max_pages, int(math.ceil(first_page["count"] / supported_page_size)))
    max_pages_in_api = first_page["page_count"]
    if num_pages > max_pages_in_api:
        actual_result_count = max_pages_in_api * supported_page_size
        if not min_users and not max_users and num_pages <= max_pages and first_page["count"] < max_ext:
            logger.info("Splitting query to avoid truncation to %d results" % actual_result_count)
            return download_metadata_workaround_limit(max_pages, max_ext, supported_page_size, first_page["count"])
        logger.warning("Truncating results to %d pages (%d results) due to API limitation" % (max_pages_in_api, actual_result_count))
        num_pages = max_pages_in_api
    logger.info("Fetching %d pages of AMO metadata" % num_pages)
    pages_to_get = ["%s?%s&page=%d" % (url, search_params, n) for n in range(2, num_pages + 1)]

    # NOTE: The logic below assumes the result set to be stable during the query.
    # If an item is deleted during the query, another item may be missing or
    # appear multiple times due to shifted items during pagination.

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


def download_metadata_workaround_limit(max_pages, max_ext, page_size, total_count):
    global logger

    # The AMO API is limited to 30k, but there are more extensions. To work
    # around this limit, we run two queries with logically disjoint results and
    # merge them. In May 2023, the total number of public extensions is 32k,
    # of which 14k have at least 10 users (=user_count_for_split).
    #
    # The work-around here depends on the ability to partition the results in
    # subsets. Ideally the AMO API should not have a cap on the result window:
    # https://github.com/mozilla/addons-server/issues/20640
    user_count_for_split = 10
    logger.info("Part 1 of 2: Looking up extensions with at least %d users" % user_count_for_split)
    metadata_part_1 = download_metadata(max_pages, max_ext, page_size, user_count_for_split, 0)
    logger.info("Part 2 of 2: Looking up extensions with less than %d users" % user_count_for_split)
    metadata_part_2 = download_metadata(max_pages, max_ext, page_size, 0, user_count_for_split)
    logger.info("Merging %d and %d and expecting %d results" % (len(metadata_part_1), len(metadata_part_2), total_count))

    id_seen = set()
    metadata = []
    for metadata_part in [metadata_part_1, metadata_part_2]:
        for ext in metadata_part:
            amo_id = ext["id"]
            if amo_id in id_seen:
                # In theory, the user count could update while the query is
                # running, and an addon can appear in both lists.
                logger.warning("Ignoring duplicate entry for AMO ID %s (addon ID %s)" % (amo_id, ext["guid"]))
                continue
            id_seen.add(amo_id)
            metadata.append(ext)

    if len(metadata) != total_count:
        # Could happen for several reasons, including but not limited to:
        # - An extension was added or removed while querying.
        # - user count updated, extension no longer in metadata_part_2.
        logger.warning("Got %d instead of the expected %d results after combining two result sets" % (len(metadata), total_count))
    return metadata[0:min(len(metadata), max_ext)]


def __as_chunks(flat_list, chunk_size):
    for i in range(0, len(flat_list), chunk_size):
        yield flat_list[i:i + chunk_size]


def update_files(metadata, hash_fs):
    urls_to_get = []
    for ext in metadata:
        for ext_file in ext.files():
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
