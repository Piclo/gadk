from typing import Any, Dict

import yaml

from .elements import EnvVars, Expression


def env_vars_to_yaml(env_vars: EnvVars) -> Dict:
    return {
        key: value.to_yaml() if type(value) is Expression else value
        for key, value in env_vars.items()
    }


class _NoAliasDumper(yaml.SafeDumper):
    """
    Safe dumper that outputs no aliases or anchors.

    See https://github.com/yaml/pyyaml/issues/103
    """

    def ignore_aliases(self, data):
        return True


def represent_str(dumper: yaml.Dumper, data: str) -> yaml.ScalarNode:
    """Represent multi-line strings as literal scalars.

    Based on https://stackoverflow.com/a/33300001/250673
    """
    return (
        dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
        if len(data.splitlines()) > 1
        else dumper.represent_str(data)
    )


def dump_yaml(value: Any) -> str:
    """
    Dump value as Yaml.

    This function makes the following guarantees:
        * Keys are NOT sorted. The order in which elements are defined will determine the order
          of keys in the output.
        * Yaml anchors and aliases are disabled as Github Actions does not support them.
    """

    yaml.representer.SafeRepresenter.add_representer(str, represent_str)
    # Note: dump_all uses a subclass of the safe yaml dumper. If tools mark this line as insecure,
    # then they probably don't follow the inheritance tree.
    return yaml.dump_all([value], sort_keys=False, Dumper=_NoAliasDumper, width=120)
