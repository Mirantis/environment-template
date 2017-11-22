import pytest
import mock
import os
import shutil
import tempfile
import yaml

from reclass_tools import render


def find_yaml_paths(tmp_dir, exts=None):
    if exts is None:
        exts = ['.yml', '.yaml']
    print(tmp_dir, exts)
    for root, subFolder, files in os.walk(tmp_dir):
        for filename in files:
            if any([filename.endswith(ext) for ext in exts]):
                yield str(os.path.join(root, filename))


def generate_context():
    for context_file in find_yaml_paths('./inventory_examples'):
        with open(context_file, 'r') as f:
            yield yaml.load(f), "test_env-" + os.path.basename(context_file)

    for interface_file in find_yaml_paths('./{# interfaces #}', exts=['']):
        if 'readme.txt' in interface_file:
            continue
        interface_role = os.path.basename(interface_file)
        node = {
            'nodes': {
                'test_node': {
                    'reclass_storage_name': 'test_node_01',
                    'interfaces': {
                        'eth1000': {
                            'role': interface_role,
                            'dpdk_pci': '0000:05:00.1',
                            'dpdk_mac': '00:11:22:33:44:55',
                        }
                    }
                }
            }
        }
        yield node, "test_env-interface-" + interface_role

    for role_file in find_yaml_paths('./{# roles #}', exts=['']):
        if 'readme.txt' in role_file:
            continue
        node_role = os.path.basename(role_file)
        node = {
            'nodes': {
                'test_node': {
                    'reclass_storage_name': 'test_node_01',
                    'roles': [
                        node_role,
                    ],
                    'interfaces': {}
                }
            }
        }
        yield node, "test_env-role-" + node_role


@pytest.mark.parametrize("environment_context, env_name", generate_context())
@mock.patch('reclass_tools.helpers.yaml_read')
def test_mkdir(mocked_yaml_read, environment_context, env_name):
    def mocked_yaml_read_returner(yaml_path):
        return environment_context
    mocked_yaml_read.side_effect = mocked_yaml_read_returner

    tmp_dir = tempfile.mkdtemp()
    try:
        render.render_dir('.', tmp_dir, ['1.yaml'], env_name=env_name)

        for yaml_file in find_yaml_paths(tmp_dir):
            try:
                with open(yaml_file, 'r') as f:
                    yaml.load(f)
            except yaml.error.YAMLError as e:
                with open(yaml_file, 'r') as f:
                    e.note = ("\n" + "".join(
                        ["{0:5}: {1}".format(num + 1, line)
                         for num, line in enumerate(f.readlines())]))
                raise
    finally:
        shutil.rmtree(tmp_dir)
