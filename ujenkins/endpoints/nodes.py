import json

from functools import partial
from typing import Any, Dict, Optional

from ujenkins.exceptions import JenkinsError, JenkinsNotFoundError


class Nodes:

    def __init__(self, jenkins):
        self.jenkins = jenkins

    @staticmethod
    def _normalize_name(name: str) -> str:
        # embedded node `master` actually have brackets in HTTP requests
        if name == 'master':
            return '(master)'
        return name

    def get(self) -> Dict[str, dict]:
        """
        Get all available nodes on server.

        Example:

        .. code-block:: python

            {
                "master": dict(...),
                "buildbot1": dict(...)
            }

        Returns:
            Dict[str, dict]: node name, and it`s detailed information.
        """
        def callback(response):
            nodes = json.loads(response.body)
            return {v['displayName']: v for v in nodes['computer']}

        return self.jenkins._request(
            'GET',
            '/computer/api/json',
            callback=callback,
        )

    def get_info(self, name: str) -> dict:
        """
        Get node detailed information.

        Args:
            name (str): node name.

        Returns:
            dict: detailed node information.
        """
        name = self._normalize_name(name)

        return self.jenkins._request(
            'GET',
            f'/computer/{name}/api/json',
        )

    def get_config(self, name: str) -> str:
        """
        Return node config in XML format.

        Args:
            name (str): node name.

        Returns:
            str: node config.
        """
        name = self._normalize_name(name)

        return self.jenkins._request(
            'GET',
            f'/computer/{name}/config.xml'
        )

    def is_exists(self, name: str) -> bool:
        """
        Check is node exist.

        Args:
            name (str):
                node name.

        Returns:
            bool: node existing.
        """
        if name == '':
            return False

        def callback1(_) -> Any:
            return partial(self.get_info, name)

        def callback2(response: Any) -> bool:
            if isinstance(response, JenkinsNotFoundError):
                return False

            return True

        return self.jenkins._chain([callback1, callback2])

    def create(self, name: str, config: dict) -> None:
        """
        Create new node.

        Args:
            name (str):
                Node name.

            config (str):
                XML config for new node.

        Returns:
            None

        Raises:
            JenkinsError: in case node already exists.
        """
        def callback1(_) -> Any:
            return partial(self.get)

        def callback2(response: Any) -> bool:
            # if not check, then we get 400 error with unclear stacktrace
            if name in response:
                raise JenkinsError(f'Node `{name}` is already exists')

            if 'type' not in config:
                config['type'] = 'hudson.slaves.DumbSlave'

            config['name'] = name

            params = {
                'name': name,
                'type': config['type'],
                'json': json.dumps(config)
            }

            return self.jenkins._request(
                'POST',
                '/computer/doCreateItem',
                params=params,
            )

        return self.jenkins._chain([callback1, callback2])

    def delete(self, name: str) -> None:
        """
        Delete node.

        Args:
            name (str):
            node name.

        Returns:
            None
        """
        name = self._normalize_name(name)

        return self.jenkins._request(
            'POST',
            f'/computer/{name}/doDelete'
        )

    def enable(self, name: str) -> None:
        """
        Enable node.

        Args:
            name (str): node name.

        Returns:
            None
        """
        name = self._normalize_name(name)

        def callback1(_) -> Any:
            return partial(self.get_info, name)

        def callback2(response: dict) -> None:
            if not response['offline']:
                return None

            return self.jenkins._request('POST', f'/computer/{name}/toggleOffline')

        return self.jenkins._chain([callback1, callback2])

    def disable(self, name: str, message: Optional[str] = '') -> None:
        """
        Disable node.

        Args:
            name (str):
                node name.

            message (Optional[str]):
                reason message.

        Returns:
            None
        """
        name = self._normalize_name(name)

        def callback1(_) -> Any:
            return partial(self.get_info, name)

        def callback2(response: dict) -> None:
            if response['offline']:
                return None

            return self.jenkins._request(
                'POST',
                f'/computer/{name}/toggleOffline',
                params={'offlineMessage': message},
            )

        return self.jenkins._chain([callback1, callback2])

    def update_offline_reason(self, name: str, message: str) -> None:
        """
        Update reason message of disabled node.

        Args:
            name (str):
                node name.

            message (str):
                reason message.

        Returns:
            None
        """
        name = self._normalize_name(name)

        return self.jenkins._request(
            'POST',
            '/computer/{}/changeOfflineCause'.format(name),
            params={'offlineMessage': message}
        )
