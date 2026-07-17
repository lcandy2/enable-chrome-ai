import os
import subprocess
import sys

import psutil


MACOS_CHROME_PROCESS_NAMES = {
    'Google Chrome',
    'Google Chrome Canary',
    'Google Chrome Dev',
    'Google Chrome Beta',
}


def is_top_level_chrome(process):
    try:
        name = process.name()
        if sys.platform == 'darwin':
            return name in MACOS_CHROME_PROCESS_NAMES
        if os.path.splitext(name)[0].lower() != 'chrome':
            return False

        parent = process.parent()
        if parent is None:
            return True
        return parent.name() != name
    except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
        return False


def shutdown_chrome():
    executable_paths = set()
    processes_to_wait = []

    for process in psutil.process_iter():
        if not is_top_level_chrome(process):
            continue
        try:
            executable_path = process.exe()
            children = process.children(recursive=True)
            process.terminate()
        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
            continue

        executable_paths.add(executable_path)
        processes_to_wait.extend([process, *children])

    _, alive = psutil.wait_procs(processes_to_wait, timeout=10)
    for process in alive:
        try:
            process.kill()
        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
            pass
    if alive:
        psutil.wait_procs(alive, timeout=5)

    return executable_paths


def chrome_restart_command(executable_path):
    if sys.platform == 'darwin':
        bundle_marker = '.app/'
        if bundle_marker not in executable_path:
            raise ValueError('Chrome executable is not inside an app bundle')
        app_bundle = executable_path.split(bundle_marker, 1)[0] + '.app'
        return ['open', app_bundle]
    return [executable_path]


def restart_chrome(executable_path):
    subprocess.Popen(
        chrome_restart_command(executable_path),
        stderr=subprocess.DEVNULL,
    )
