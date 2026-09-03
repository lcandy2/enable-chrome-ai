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
    """Kill all Chrome processes; return only the main browser executables to relaunch."""
    terminated_chromes = set()
    for process in psutil.process_iter():
        try:
            name = process.name()

            if sys.platform == 'darwin':
                # 主浏览器 + helper 都以 "Google Chrome" 开头。
                is_chrome = name.startswith('Google Chrome')
                is_main_browser = is_chrome and 'Helper' not in name
                # crashpad 进程名 "chrome_crashpad_handler" 与 Electron 应用（WorkBuddy、
                # CodeBuddy 等）同名，必须用可执行文件路径确认它确实属于 Google Chrome。
                if not is_chrome and name.startswith('chrome_crashpad'):
                    is_chrome = 'Google Chrome' in process.exe()
            else:
                is_chrome = os.path.splitext(name)[0] == 'chrome'
                # 主浏览器是其父进程不是另一个 chrome 的顶层进程（保留原脚本语义）。
                is_main_browser = is_chrome and (
                    process.parent() is None or process.parent().name() != name
                )

            if not is_chrome:
                continue

            # 先取 exe 路径再 kill：kill 之后进程可能变成僵尸态取不到 exe。
            location = process.exe() if is_main_browser else None
            process.kill()

            # 只重启主浏览器。裸启动 Helper / crashpad 子进程会产生孤儿进程，导致 Chrome 卡死。
            if is_main_browser:
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
            if sys.platform == 'darwin':
                # 用 open -a 走 LaunchServices 拉起：直接 exec 内部二进制在更新期会变成
                # code_sign_clone 临时副本导致静默失败，且不会把窗口带到前台。
                subprocess.Popen(['open', '-a', os.path.basename(chrome)], stderr=subprocess.DEVNULL)
            else:
                subprocess.Popen([chrome], stderr=subprocess.DEVNULL)

    input('Enter to continue...')


if __name__ == '__main__':
    main()

