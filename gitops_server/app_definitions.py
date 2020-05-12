import json
import logging
import os
from base64 import b64encode

from .utils import load_yaml

logger = logging.getLogger('gitops')


class AppDefinitions:
    def __init__(self, name):
        self.name = name

    def from_path(self, path):
        self.apps = {}
        path = os.path.join(path, 'apps')
        for entry in os.listdir(path):
            entry_path = os.path.join(path, entry)
            if entry[0] != '.' and not os.path.isfile(entry_path):
                app = App(entry, entry_path)
                self.apps[entry] = app


class App:
    def __init__(self, name, path=None, deployments={}, secrets={}, load_secrets=True):
        self.name = name
        self.path = path
        if path:
            self.deployments = load_yaml(os.path.join(path, 'deployment.yml'))
            if load_secrets:
                self.secrets = load_yaml(os.path.join(path, 'secrets.yml')).get('secrets', {})
            else:
                self.secrets = secrets
        else:
            self.deployments = deployments
            self.secrets = secrets
        self.make_values()

    def __eq__(self, other):
        return (
            self.name == other.name
            and json.dumps(self.values, sort_keys=True) == json.dumps(other.values, sort_keys=True)
        )

    def is_inactive(self):
        return 'inactive' in self.values.get('tags', [])

    def get_target_cluster(self):
        return self.values.get('cluster')

    def make_values(self):
        self.values = {
            **self.deployments,
            'image': self.make_image(self.deployments),
            'secrets': {
                **{
                    k: b64encode(v.encode()).decode()
                    for k, v in self.secrets.items()
                }
            }
        }
        # Don't include the `images` key. It will only cause everything to be
        # redeployed when any group changes.
        try:
            del self.values['images']
        except KeyError:
            pass

    def make_image(self, details):
        if 'image-tag' in details:
            return self.deployments['images']['template'].format(
                tag=details['image-tag']
            )
        else:
            return details.get('image')