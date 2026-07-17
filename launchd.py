import os
import plistlib
import subprocess
import sys
import tempfile


LABEL = 'com.github.lcandy2.enable-chrome-ai'


def launch_agent_path():
    return os.path.expanduser('~/Library/LaunchAgents/%s.plist' % LABEL)


def build_launch_agent(country, python_executable, script_path):
    log_dir = os.path.expanduser('~/Library/Logs/enable-chrome-ai')
    return {
        'Label': LABEL,
        'ProgramArguments': [
            python_executable,
            script_path,
            '--country',
            country,
            '--yes',
        ],
        'ProcessType': 'Background',
        'RunAtLoad': True,
        'StartCalendarInterval': {
            'Weekday': 0,
            'Hour': 4,
            'Minute': 0,
        },
        'StandardOutPath': os.path.join(log_dir, 'stdout.log'),
        'StandardErrorPath': os.path.join(log_dir, 'stderr.log'),
    }


def _launchctl(*args, check=True):
    return subprocess.run(
        ['launchctl', *args],
        check=check,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def install_launch_agent(country, script_path):
    if sys.platform != 'darwin':
        raise RuntimeError('Persistent mode currently supports macOS launchd only')

    agent_path = launch_agent_path()
    log_dir = os.path.expanduser('~/Library/Logs/enable-chrome-ai')
    os.makedirs(os.path.dirname(agent_path), exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)

    agent = build_launch_agent(
        country=country,
        python_executable=os.path.abspath(sys.executable),
        script_path=os.path.realpath(script_path),
    )
    descriptor, temporary_path = tempfile.mkstemp(
        prefix=LABEL + '-', suffix='.plist', dir=os.path.dirname(agent_path))
    try:
        with os.fdopen(descriptor, 'wb') as fp:
            plistlib.dump(agent, fp, sort_keys=False)
        os.replace(temporary_path, agent_path)
    finally:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)

    domain = 'gui/%d' % os.getuid()
    _launchctl('bootout', domain, agent_path, check=False)
    try:
        _launchctl('bootstrap', domain, agent_path)
    except subprocess.CalledProcessError as error:
        message = error.stderr.strip() or error.stdout.strip()
        raise RuntimeError('Failed to load LaunchAgent: %s' % message) from error

    print('Installed %s' % agent_path)
    print('Schedule: at login and every Sunday at 04:00 (or after the next wake)')
    print('Country: %s' % country)


def uninstall_launch_agent():
    if sys.platform != 'darwin':
        raise RuntimeError('Persistent mode currently supports macOS launchd only')

    agent_path = launch_agent_path()
    domain = 'gui/%d' % os.getuid()
    _launchctl('bootout', domain, agent_path, check=False)
    if os.path.exists(agent_path):
        os.unlink(agent_path)
    print('Removed %s' % agent_path)
