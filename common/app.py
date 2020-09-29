import json
import os
from base64 import b64encode
from typing import Dict, Optional, Union

from .utils import load_yaml

DEPLOYMENT_ATTRIBUTES = [
    'tags',
    'image-tag',
    'containers',
    'environment',
]


class App:
    def __init__(self, name: str, path: Optional[str] = None, deployments: Optional[Dict] = None, secrets: Optional[Dict] = None, load_secrets: bool = True, account_id: str = ''):
        self.name = name
        self.path = path
        self.account_id = account_id
        self.deployments = deployments or {}
        self.secrets = secrets or {}
        if path:
            self.deployments = load_yaml(os.path.join(path, 'deployment.yml'))
            if load_secrets:
                self.secrets = load_yaml(os.path.join(path, 'secrets.yml')).get('secrets', {})
            else:
                self.secrets = secrets or {}
        self.values = self._make_values()
        self.chart = Chart(self.values['chart'])

    def __eq__(self, other):
        return (
            type(self) == type(other)
            and self.name == other.name
            and json.dumps(self.values, sort_keys=True) == json.dumps(other.values, sort_keys=True)
        )

    def is_inactive(self):
        return 'inactive' in self.values.get('tags', [])

    def _make_values(self) -> Dict:
        values = {
            **self.deployments,
            'secrets': {
                **{
                    k: b64encode(v.encode()).decode()
                    for k, v in self.secrets.items()
                }
            }
        }

        image = self._make_image(self.deployments)
        if image:
            values['image'] = image

        # Don't include the `images` key. It will only cause everything to be
        # redeployed when any group changes.
        values.pop('images', None)
        return values

    def _make_image(self, deployment_config: Dict):
        if 'image-tag' in deployment_config:
            return deployment_config['images']['template'].format(
                account_id=self.account_id,
                tag=deployment_config['image-tag'],
            )
        else:
            return deployment_config.get('image')


class Chart:
    """Represents a Helm chart

    Can be stored in a git repo, helm repo or local path

    Example definition in `deployments.yml`:
    chart:
      type: git
      git_sha: develop
      git_repo_url: https://github.com/uptick/workforce

    of
    chart:
      type: helm
      helm_repo: brigade
      helm_repo_url: https://brigadecore.github.io/charts
      helm_chart: brigade/brigade

    If a dictionary is not passed, it is assumed to be a git repo. eg:
      chart: https://github.com/uptick/workforce
    """
    def __init__(self, definition: Union[Dict, str]):
        if isinstance(definition, str):
            # for backwards compat, any chart definition which is a string, is a git repo
            self.type = "git"
            self.git_sha = None
            self.git_repo_url = definition
        elif isinstance(definition, dict):
            self.type = definition['type']
            self.git_sha = definition.get('git_sha')
            self.git_repo_url = definition.get('git_repo_url')
            self.helm_repo = definition.get('helm_repo')
            self.helm_repo_url = definition.get('helm_repo_url')
            self.helm_chart = definition.get('helm_chart')
            self.path = definition.get('path')
        else:
            raise Exception("Chart definition must be either a dict or string. Instead it is: {definition}")

        if self.git_repo_url and '@' in self.git_repo_url:
            self.git_repo_url, self.git_sha = self.git_repo_url.split('@')

    def is_git(self):
        return self.type == "git"

    def is_helm(self):
        return self.type == "helm"

    def is_local(self):
        return self.type == "local"
