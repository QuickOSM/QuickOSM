"""Manage Overpass API connexion."""

import logging
import os
import re

from typing import List

from qgis.PyQt.QtCore import QDir, QFileInfo, QTemporaryFile

from QuickOSM.core.api.downloader import Downloader
from QuickOSM.core.exceptions import (
    NetWorkErrorException,
    OverpassBadRequestException,
    OverpassManyRequestException,
    OverpassMemoryException,
    OverpassRuntimeError,
    OverpassTimeoutException,
)

LOGGER = logging.getLogger('QuickOSM')


class ConnexionOAPI(Downloader):

    """
    Manage connexion to the overpass API.
    """

    def __init__(self, url: str, convert: bool = False):
        """Constructor of query.

        :param url:Full URL of OverPass Query with the query encoded in it.
        :type url:str
        """
        super().__init__(url)

        if convert:
            temporary = QTemporaryFile(
                os.path.join(QDir.tempPath(), 'request-XXXXXX.txt'))
        else:
            temporary = QTemporaryFile(
                os.path.join(QDir.tempPath(), 'request-XXXXXX.osm'))
        temporary.open()
        self.result_path = temporary.fileName()
        temporary.close()

    def run_convert(self) -> str:
        """Run the query converter

        :return: The converted query
        :rtype: str
        """
        self.download()

        with open(self.result_path, encoding='utf8') as txt_file:
            text = txt_file.read()
            query = re.findall("<pre>\\n(.*?)</pre>", text)[0]

        return query

    def run(self) -> str:
        """Run the query.

        :return: The result of the query.
        :rtype: str

        :raise OverpassBadRequestException:
        :raise NetWorkErrorException:
        :raise OverpassTimeoutException:
        """
        self.download()

        for message in self.errors:
            self.is_query_timed_out(message)
            self.too_many_request(message)
            self.is_bad_request(message)
            LOGGER.error(message)

        if len(self.errors):
            raise NetWorkErrorException('Overpass API', ', '.join(self.errors))

        osm_file = QFileInfo(self.result_path)
        if not osm_file.exists() and not osm_file.isFile():
            # Do not raise a QuickOSM exception here
            # It must be a bug from QuickOSM
            raise FileNotFoundError

        self.check_file(self.result_path)

        # Everything went fine
        return self.result_path

    @staticmethod
    def check_file(path: str):
        """Verify the file provided by the Overpass API"""
        # The download is done, checking for not complete OSM file.
        # Overpass might abort the request with HTTP 200.
        LOGGER.info(f'Checking OSM file content {path}')

        def last_lines(file_path: str, line_count: int) -> List[str]:
            """Select the last lines"""
            bufsize = 8192
            fsize = os.stat(file_path).st_size
            iteration = 0
            with open(file_path, encoding='utf8') as file:
                if bufsize > fsize:
                    bufsize = fsize - 1
                    data = []
                    while True:
                        iteration += 1
                        seek_size = fsize - bufsize * iteration
                        if seek_size < 0:
                            seek_size = 0
                        file.seek(seek_size)
                        data.extend(file.readlines())
                        if len(data) >= line_count or file.tell() == 0:
                            line_content = data[-line_count:]
                            return line_content
                else:
                    return list(file.readlines())

        lines = last_lines(path, 10)

        # Check if we can use the static method below
        timeout = (
            '<remark> runtime error: Query timed out in "[a-z]+" at line '
            r'[\d]+ after ([\d]+) seconds. </remark>')
        if re.search(timeout, ''.join(lines)):
            raise OverpassTimeoutException

        memory = (
            '<remark> runtime error: Query ran out of memory in "query" at '
            r'line [\d]+. It would need at least ([\d]+) (.*) of RAM to '
            'continue. </remark>')
        search = re.search(memory, ''.join(lines))
        if search:
            raise OverpassMemoryException(search.group(1), search.group(2))

        generic = (
            '<remark> runtime error: (.*)</remark>')
        search = re.search(generic, ''.join(lines))
        if search:
            raise OverpassRuntimeError(search.group(1))

        search = re.search(r'Error</strong>:(.*)</p>', ''.join(lines), re.MULTILINE)
        if search:
            raise OverpassBadRequestException(search.group(1))

    @staticmethod
    def is_query_timed_out(string: str):
        """Check the time-out exception"""
        text = 'Network request (.*) timed out'
        search = re.search(text, string)
        if search:
            raise OverpassTimeoutException

    @staticmethod
    def too_many_request(string: str):
        """Check the too many request exception"""
        text = '(.*)server replied: Too Many Requests'
        search = re.search(text, string)
        if search:
            raise OverpassManyRequestException

    @staticmethod
    def is_bad_request(string: str):
        """Check the bad request exception"""
        text = '(.*)server replied: Bad Request'
        search = re.search(text, string)
        if search:
            raise OverpassBadRequestException

        text = '(.*)server replied: Forbidden'
        search = re.search(text, string)
        if search:
            raise OverpassBadRequestException
