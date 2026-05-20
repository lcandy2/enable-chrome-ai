import os
import sys
import json
import subprocess

import psutil


TARGET_COUNTRY = 'us'
CHROME_RESTART_ARGS = (
    f'--variations-override-country={TARGET_COUNTRY}',
    '--glic-dev',
    '--disable-features=GlicUseSessionCountryForFiltering',
)
FORCED_LABS_EXPERIMENTS = (
    'glic@1',
    'glic-actor@1',
    'glic-entrypoint-variations@1',
)
PROFILE_PREF_PATCHES = {
    ('browser', 'gemini_settings'): 0,
    ('glic', 'pinned_to_tabstrip'): True,
    ('sync', 'glic_rollout_eligibility'): True,
}
MACOS_CHROME_PROCESS_NAMES = {
    'Google Chrome',
    'Google Chrome Canary',
    'Google Chrome Dev',
    'Google Chrome Beta',
}
EXCLUDED_PROFILE_DIRS = {
    'CertificateRevocation',
    'Guest Profile',
    'System Profile',
}


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
    processes_to_wait = []
    for process in psutil.process_iter():
        try:
            if sys.platform == 'darwin':
                if process.name() not in MACOS_CHROME_PROCESS_NAMES:
                    continue
            elif os.path.splitext(process.name())[0] != 'chrome':
                continue
            elif not process.is_running():
                continue
            elif process.parent() is not None and process.parent().name() == process.name():
                continue
            location = process.exe()
            process.kill()
            processes_to_wait.append(process)
            terminated_chromes.add(location)
        except psutil.NoSuchProcess:
            pass
    psutil.wait_procs(processes_to_wait, timeout=10)
    return terminated_chromes


def get_macos_app_path(executable_path):
    app_suffix = '.app'
    app_index = executable_path.find(app_suffix)
    if app_index == -1:
        return None
    return executable_path[:app_index + len(app_suffix)]


def restart_chrome(chrome):
    restart_args = list(CHROME_RESTART_ARGS)
    print('Start Chrome with args', ' '.join(restart_args))
    if sys.platform == 'darwin':
        app_path = get_macos_app_path(chrome)
        if app_path:
            subprocess.Popen(
                ['open', app_path, '--args', *restart_args],
                stderr=subprocess.DEVNULL,
            )
            return
    subprocess.Popen([chrome, *restart_args], stderr=subprocess.DEVNULL)


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


def set_nested_value(obj, path, value):
    current = obj
    for key in path[:-1]:
        next_obj = current.get(key)
        if not isinstance(next_obj, dict):
            next_obj = {}
            current[key] = next_obj
        current = next_obj

    key = path[-1]
    if current.get(key) == value:
        return False
    current[key] = value
    return True


def get_profile_preference_files(user_data_path, local_state):
    profile_dirs = []
    info_cache = local_state.get('profile', {}).get('info_cache', {})
    if isinstance(info_cache, dict):
        profile_dirs.extend(info_cache.keys())

    try:
        for profile_dir in os.listdir(user_data_path):
            preference_file = os.path.join(user_data_path, profile_dir, 'Preferences')
            if os.path.isfile(preference_file):
                profile_dirs.append(profile_dir)
    except FileNotFoundError:
        return []

    preference_files = []
    seen = set()
    for profile_dir in profile_dirs:
        if profile_dir in EXCLUDED_PROFILE_DIRS or profile_dir in seen:
            continue
        preference_file = os.path.join(user_data_path, profile_dir, 'Preferences')
        if os.path.isfile(preference_file):
            preference_files.append(preference_file)
            seen.add(profile_dir)
    return preference_files


def patch_profile_preferences(user_data_path, local_state):
    modified_files = 0
    for preference_file in get_profile_preference_files(user_data_path, local_state):
        try:
            with open(preference_file, 'r', encoding='utf-8') as fp:
                preferences = json.load(fp)
        except (json.JSONDecodeError, OSError) as error:
            print('Failed to patch Preferences.', preference_file, error)
            continue

        modified = False
        for path, value in PROFILE_PREF_PATCHES.items():
            if set_nested_value(preferences, path, value):
                modified = True
                print('Patched', '.'.join(path), 'in', preference_file)

        if modified:
            with open(preference_file, 'w', encoding='utf-8') as fp:
                json.dump(preferences, fp)
            modified_files += 1

    return modified_files


def append_forced_labs_experiments(local_state):
    browser = local_state.get('browser')
    if not isinstance(browser, dict):
        browser = {}
        local_state['browser'] = browser

    experiments = browser.get('enabled_labs_experiments')
    if not isinstance(experiments, list):
        experiments = []
        browser['enabled_labs_experiments'] = experiments

    modified = False
    for experiment in FORCED_LABS_EXPERIMENTS:
        if experiment not in experiments:
            experiments.append(experiment)
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
    if local_state.get('variations_country') != TARGET_COUNTRY:
        local_state['variations_country'] = TARGET_COUNTRY
        modified = True
        print('Patched variations_country')

    # 3. Patch both permanent and session country values used by current Glic filtering.
    target_permanent_country = [last_version, TARGET_COUNTRY]
    if local_state.get('variations_permanent_consistency_country') != target_permanent_country:
        local_state['variations_permanent_consistency_country'] = target_permanent_country
        modified = True
        print('Patched variations_permanent_consistency_country')

    if local_state.get('variations_permanent_overridden_country') != TARGET_COUNTRY:
        local_state['variations_permanent_overridden_country'] = TARGET_COUNTRY
        modified = True
        print('Patched variations_permanent_overridden_country')

    for key in (
        'variations_safe_seed_permanent_consistency_country',
        'variations_safe_seed_session_consistency_country',
    ):
        if local_state.get(key) != TARGET_COUNTRY:
            local_state[key] = TARGET_COUNTRY
            modified = True
            print('Patched', key)

    if append_forced_labs_experiments(local_state):
        modified = True
        print('Patched browser.enabled_labs_experiments')

    if modified:
        with open(local_state_file, 'w', encoding='utf-8') as fp:
            json.dump(local_state, fp)
        print('Succeeded in patching Local State')
    else:
        print('No need to patch Local State')

    patched_preferences = patch_profile_preferences(user_data_path, local_state)
    if patched_preferences > 0:
        print('Succeeded in patching Preferences', patched_preferences)
    else:
        print('No need to patch Preferences')


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
        print('Patching Chrome', version, last_version, '"'+user_data_path+'"')
        patch_local_state(user_data_path, last_version)

    if len(terminated_chromes) > 0:
        print('Restart Chrome')
        for chrome in terminated_chromes:
            restart_chrome(chrome)
    else:
        print(
            'Chrome was not running. Start Chrome with:',
            ' '.join(CHROME_RESTART_ARGS),
        )

    input('Enter to continue...')


if __name__ == '__main__':
    main()
