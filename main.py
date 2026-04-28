import os
import sys
import json
import subprocess

import psutil


def get_version_and_user_data_path():
    os_and_user_data_paths = {
        'win32': {
            'stable': '~/AppData/Local/Google/Chrome/User Data',
            'canary': '~/AppData/Local/Google/Chrome SxS/User Data',
            'dev': '~/AppData/Local/Google/Chrome Dev/User Data',
            'beta': '~/AppData/Local/Google/Chrome Beta/User Data',
        },
        'linux': {
            'stable': '~/.config/google-chrome',
            'canary': '~/.config/google-chrome-canary',
            'dev': '~/.config/google-chrome-unstable',
            'beta': '~/.config/google-chrome-beta',
        },
        'darwin': {
            'stable': '~/Library/Application Support/Google/Chrome',
            'canary': '~/Library/Application Support/Google/Chrome Canary',
            'dev': '~/Library/Application Support/Google/Chrome Dev',
            'beta': '~/Library/Application Support/Google/Chrome Beta',
        },
    }

    for platform, version_and_user_data_path in os_and_user_data_paths.items():
        available_version_and_user_data_path = {}
        if sys.platform.startswith(platform):
            for version, user_data_path in version_and_user_data_path.items():
                user_data_path = os.path.abspath(os.path.expanduser(user_data_path))
                if os.path.exists(user_data_path):
                    available_version_and_user_data_path[version] = user_data_path
            return available_version_and_user_data_path

    raise Exception('Unsupported platform %s' % sys.platform)




def shutdown_chrome():
    terminated_chromes = set()
    for process in psutil.process_iter(attrs=["name", "exe"]):
        try:
            name = process.info.get("name") or process.name()
            base = os.path.splitext(name)[0].lower() if name else ""

            if sys.platform == 'darwin':
                if not (name or "").startswith('Google Chrome'):
                    continue
            else:
                if base != 'chrome':
                    continue

            if not process.is_running():
                continue

            try:
                parent = process.parent()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                parent = None

            if parent is not None:
                try:
                    parent_name = parent.name()
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    parent_name = None
                if parent_name and (os.path.splitext(parent_name)[0].lower() == base):
                    continue

            try:
                location = process.info.get("exe") or process.exe()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                location = None

            try:
                process.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

            if location:
                terminated_chromes.add(location)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return terminated_chromes

def get_last_version(user_data_path):
    last_version_file = os.path.join(user_data_path, 'Last Version')
    if not os.path.exists(last_version_file):
        return None
    with open(last_version_file, 'r', encoding='utf-8') as fp:
        return fp.read()

    if not os.path.exists(last_version_file):
        return None
    with open(last_version_file, 'r', encoding='utf-8') as fp:
        return fp.read()
def set_all_is_glic_eligible(obj):
    """Recursively find and set all is_glic_eligible to true."""
    modified = False
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == 'is_glic_eligible' and value != True:
                obj[key] = True
                modified = True
            elif isinstance(value, (dict, list)):
                if set_all_is_glic_eligible(value):
                    modified = True
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, (dict, list)):
                if set_all_is_glic_eligible(item):
                    modified = True
    return modified


def patch_local_state(user_data_path, last_version):
    local_state_file = os.path.join(user_data_path, 'Local State')
    if not os.path.exists(local_state_file):
        print('Failed to patch Local State. File not found', local_state_file)
        return

    with open(local_state_file, 'r', encoding='utf-8') as fp:
        local_state = json.load(fp)

    modified = False

    # 1. Set all is_glic_eligible to true (recursive)
    if set_all_is_glic_eligible(local_state):
        modified = True
        print('Patched is_glic_eligible')

    # 2. Set variations_country to "us" (root level)
    if local_state.get('variations_country') != 'us':
        local_state['variations_country'] = 'us'
        modified = True
        print('Patched variations_country')

    # 3. Set variations_permanent_consistency_country[0] to last_version, [1] to "us" (root level)
    if 'variations_permanent_consistency_country' in local_state:
        if isinstance(local_state['variations_permanent_consistency_country'], list) and \
           len(local_state['variations_permanent_consistency_country']) >= 2:
            if local_state['variations_permanent_consistency_country'][0] != last_version or \
               local_state['variations_permanent_consistency_country'][1] != 'us':
                local_state['variations_permanent_consistency_country'][0] = last_version
                local_state['variations_permanent_consistency_country'][1] = 'us'
                modified = True
                print('Patched variations_permanent_consistency_country')

    if modified:
        with open(local_state_file, 'w', encoding='utf-8') as fp:
            json.dump(local_state, fp)
        print('Succeeded in patching Local State')
    else:
        print('No need to patch Local State')


def main():
    version_and_user_data_path = get_version_and_user_data_path()
    if len(version_and_user_data_path) == 0:
        raise Exception('No available user data path found')

    terminated_chromes = shutdown_chrome()
    if len(terminated_chromes) > 0:
        print('Shutdown Chrome')

    for version, user_data_path in version_and_user_data_path.items():
        last_version = get_last_version(user_data_path)
        if last_version is None:
            print('Failed to get version. File not found', os.path.join(user_data_path, 'Last Version'))
            continue
        main_version = int(last_version.split('.')[0])
        print('Patching Chrome', version, last_version, '"'+user_data_path+'"')
        patch_local_state(user_data_path, last_version)

    if len(terminated_chromes) > 0:
        print('Restart Chrome')
        for chrome in terminated_chromes:
            subprocess.Popen([chrome], stderr=subprocess.DEVNULL)
    try:
        if sys.stdin.isatty():
            input('Enter to continue...')
    except EOFError:
        pass
if __name__ == '__main__':
    main()










