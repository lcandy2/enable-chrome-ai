import os
import sys
import json
import argparse
import stat
import tempfile

from chrome_processes import restart_chrome, shutdown_chrome
from launchd import install_launch_agent, uninstall_launch_agent


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


def get_last_version(user_data_path):
    last_version_file = os.path.join(user_data_path, 'Last Version')
    if not os.path.exists(last_version_file):
        return None
    with open(last_version_file, 'r', encoding='utf-8') as fp:
        return fp.read().strip()


def set_all_is_glic_eligible(obj):
    """Recursively find and set all is_glic_eligible to true."""
    modified = False
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == 'is_glic_eligible' and value is not True:
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


def write_json_atomically(path, value):
    directory = os.path.dirname(path)
    original_mode = stat.S_IMODE(os.stat(path).st_mode)
    descriptor, temporary_path = tempfile.mkstemp(
        prefix='.local-state-', dir=directory)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as fp:
            json.dump(value, fp)
            fp.flush()
            os.fsync(fp.fileno())
        os.chmod(temporary_path, original_mode)
        os.replace(temporary_path, path)
    finally:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)


def local_state_needs_patch(user_data_path, last_version, country):
    local_state_file = os.path.join(user_data_path, 'Local State')
    if not os.path.exists(local_state_file):
        return False

    with open(local_state_file, 'r', encoding='utf-8') as fp:
        local_state = json.load(fp)

    if country is not None:
        if local_state.get('variations_country') != country:
            return True
        consistency = local_state.get('variations_permanent_consistency_country')
        if not isinstance(consistency, list) or len(consistency) < 2:
            return True
        if consistency[0] != last_version or consistency[1] != country:
            return True

    probe = json.loads(json.dumps(local_state))
    return set_all_is_glic_eligible(probe)


def patch_local_state(user_data_path, last_version, country=None):
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

    # Use the requested variations country (defaults to "us").
    if country is not None:
        # 2. Set variations_country (root level)
        if local_state.get('variations_country') != country:
            local_state['variations_country'] = country
            modified = True
            print('Patched variations_country -> %s' % country)

        # 3. Set variations_permanent_consistency_country[0] to last_version, [1] to country
        consistency = local_state.get('variations_permanent_consistency_country')
        if not isinstance(consistency, list) or len(consistency) < 2:
            local_state['variations_permanent_consistency_country'] = [last_version, country]
            modified = True
            print('Created variations_permanent_consistency_country -> %s' % country)
        elif consistency[0] != last_version or consistency[1] != country:
            consistency[0] = last_version
            consistency[1] = country
            modified = True
            print('Patched variations_permanent_consistency_country -> %s' % country)
    else:
        print('Kept variations_country as-is (%s); pass --country to override'
              % local_state.get('variations_country'))

    if modified:
        write_json_atomically(local_state_file, local_state)
        print('Succeeded in patching Local State')
    else:
        print('No need to patch Local State')


def parse_country(value):
    country = value.lower()
    if len(country) != 2 or not country.isascii() or not country.isalpha():
        raise argparse.ArgumentTypeError('country must be a two-letter code')
    return country


def parse_args():
    parser = argparse.ArgumentParser(
        description="Enable Chrome's built-in AI by patching the local profile.")
    parser.add_argument(
        '--country', default='us', type=parse_country, metavar='CC',
        help='Set variations country (default: us; e.g. us, sg).')
    parser.add_argument(
        '-y', '--yes', action='store_true',
        help='Run non-interactively (skip the final Enter prompt). For launchd/cron.')
    persistence = parser.add_mutually_exclusive_group()
    persistence.add_argument(
        '--install-persistence', action='store_true',
        help='Install a macOS LaunchAgent that repairs country drift.')
    persistence.add_argument(
        '--remove-persistence', action='store_true',
        help='Unload and remove the macOS LaunchAgent.')
    return parser.parse_args()


def main():
    args = parse_args()

    if args.install_persistence:
        install_launch_agent(args.country, __file__)
        return
    if args.remove_persistence:
        uninstall_launch_agent()
        return

    version_and_user_data_path = get_version_and_user_data_path()
    if len(version_and_user_data_path) == 0:
        raise Exception('No available user data path found')

    pending = {}
    for version, user_data_path in version_and_user_data_path.items():
        last_version = get_last_version(user_data_path)
        if last_version is None:
            print('Failed to get version. File not found', os.path.join(user_data_path, 'Last Version'))
            continue
        if local_state_needs_patch(user_data_path, last_version, args.country):
            pending[version] = (last_version, user_data_path)

    if not pending:
        print('All Chrome profiles already match country %s' % args.country)
        if not args.yes:
            input('Enter to continue...')
        return

    terminated_chromes = shutdown_chrome()
    if len(terminated_chromes) > 0:
        print('Shutdown Chrome')

    try:
        for version, (last_version, user_data_path) in pending.items():
            print('Patching Chrome', version, last_version, '"'+user_data_path+'"')
            patch_local_state(user_data_path, last_version, country=args.country)
    finally:
        if len(terminated_chromes) > 0:
            print('Restart Chrome')
            for chrome in terminated_chromes:
                restart_chrome(chrome)

    if not args.yes:
        input('Enter to continue...')


if __name__ == '__main__':
    main()
