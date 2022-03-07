import os
import requests

from xml.etree import ElementTree

from cloudify import ctx as ctx_from_import
from .utils import with_rest_client
from .constansts import (SYNCTHING_DIR, SYNCTHING_API_PORT)


class Syncthing(object):
    """Interface to the syncthing API."""
    def __init__(self,
                 logger,
                 home_dir=SYNCTHING_DIR,
                 port=SYNCTHING_API_PORT,
                 *args,
                 **kwargs):
        self.home_dir = home_dir
        self._config_path = os.path.join(home_dir,
                                         '.config/syncthing/config.xml')
        self._syncthing_port = port
        self._api_key = None
        self._session = None
        self.logger = logger

    def _url(self, part):
        return 'http://127.0.0.1:{0}/rest/{1}'.format(
            self._syncthing_port, part)

    @property
    def api_key(self):
        if self._api_key:
            return self._api_key
        with open(self._config_path) as f:
            config_source = f.read()
        tree = ElementTree.fromstring(config_source)
        self._api_key = tree.findall('.//gui/apikey')[0].text
        return self._api_key

    @property
    def session(self):
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update({'X-Api-Key': self.api_key})
        return self._session

    def status(self):
        return self.session.get(self._url('system/status')).json()

    def get_id(self):
        return self.status()['myID']

    def config(self):
        return self.session.get(self._url('system/config')).json()

    def folders(self):
        self.logger.debug('Getting configured folders')
        return self.config()['folders']

    def devices(self):
        self.logger.debug('Getting configured devices')
        return self.config()['devices']

    def folder_status(self, folder):
        """
        Getting the current sync status of a specific folder

        :param folder: folder ID (string)
        :return: json with folder status
        """
        self.logger.debug('Getting {0} folder status'.format(folder))
        return self.session.get(url=self._url('db/status'),
                                params={'folder': folder}).json()


@with_rest_client
def get_syncthing_status(rest_client):
    is_cluster = len(rest_client.manager.get_managers()['items']) > 1
    if is_cluster:
        syncthing = Syncthing(ctx_from_import.logger)
        return syncthing.status()
    return None


@with_rest_client
def get_folder_status(check_path, rest_client):
    is_cluster = len(rest_client.manager.get_managers()['items']) > 1
    if is_cluster:
        syncthing = Syncthing(ctx_from_import.logger)
        need_bytes = syncthing.folder_status(check_path)['needBytes']
        return "OK" if need_bytes == 0 else "NOT OK"
    return 'OK'
