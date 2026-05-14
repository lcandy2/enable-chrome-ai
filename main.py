import os
import sys
import json
import shutil
import argparse
import subprocess

import psutil


BACKUP_SUFFIX = '.enable-chrome-ai.bak'


def parse_args():
    parser = argparse.ArgumentParser(
        description='Patch Chrome local profile data to enable built-in AI features.'
    )
    parser.add_argument(
        '--restore',
        action='store_true',
        help='Restore Local State from the backup created before the first patch.',
    )
    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='Patch without creating a Local State backup.',
    )
    return parser.parse_args()


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


def get_local_state_file(user_data_path):
    return os.path.join(user_data_path, 'Local State')


def get_backup_file(local_state_file):
    return local_state_file + BACKUP_SUFFIX


def backup_local_state(local_state_file):
    backup_file = get_backup_file(local_state_file)
    if os.path.exists(backup_file):
        print('Backup already exists', backup_file)
        return
    shutil.copy2(local_state_file, backup_file)
    print('Created backup', backup_file)


def restore_local_state(user_data_path):
    local_state_file = get_local_state_file(user_data_path)
    backup_file = get_backup_file(local_state_file)
    if not os.path.exists(backup_file):
        print('No backup found', backup_file)
        return False
    shutil.copy2(backup_file, local_state_file)
    print('Restored Local State from backup', backup_file)
    return True


def is_top_level_chrome_process(process):
    name = process.name()
    if sys.platform == 'darwin':
        return name.startswith('Google Chrome')
    if os.path.splitext(name)[0] != 'chrome':
        return False
    if not process.is_running():
        return False

    parent = process.parent()
    if parent is None:
        return True
    try:
        return parent.name() != name
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return True


def shutdown_chrome():
    terminated_chromes = set()
    for process in psutil.process_iter():
        try:
            if not is_top_level_chrome_process(process):
                continue
            location = process.exe()
            process.kill()
            terminated_chromes.add(location)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return terminated_chromes


def get_last_version(user_data_path):
    last_version_file = os.path.join(user_data_path, 'Last Version')
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


def patch_local_state(user_data_path, last_version, create_backup=True):
    local_state_file = get_local_state_file(user_data_path)
    if not os.path.exists(local_state_file):
        print('Failed to patch Local State. File not found', local_state_file)
        return

    if create_backup:
        backup_local_state(local_state_file)

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
    args = parse_args()
    version_and_user_data_path = get_version_and_user_data_path()
    if len(version_and_user_data_path) == 0:
        raise Exception('No available user data path found')

    terminated_chromes = shutdown_chrome()
    if len(terminated_chromes) > 0:
        print('Shutdown Chrome')

    if args.restore:
        for version, user_data_path in version_and_user_data_path.items():
            print('Restoring Chrome', version, '"'+user_data_path+'"')
            restore_local_state(user_data_path)
    else:
        for version, user_data_path in version_and_user_data_path.items():
            last_version = get_last_version(user_data_path)
            if last_version is None:
                print('Failed to get version. File not found', os.path.join(user_data_path, 'Last Version'))
                continue
            print('Patching Chrome', version, last_version, '"'+user_data_path+'"')
            patch_local_state(user_data_path, last_version, create_backup=not args.no_backup)

    if len(terminated_chromes) > 0:
        print('Restart Chrome')
        for chrome in terminated_chromes:
            subprocess.Popen([chrome], stderr=subprocess.DEVNULL)

    input('Enter to continue...')


if __name__ == '__main__':
    main()
