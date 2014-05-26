import argparse
import contextlib
import getpass
import os
import os.path
from pprint import pprint
import shutil
import traceback
import urllib
import subprocess
import string
import uuid
import textwrap
import imp

# Settings

def interpolate(source, context, max_depth=3):
    if isinstance(source, str):
        last = None
        cur = source
        depth = 0
        while last != cur and depth < max_depth:
            last = cur
            cur = string.Template(cur).safe_substitute(context)
            depth += 1
        return cur
    elif hasattr(source, "items"):
        return {interpolate(k, context, max_depth-1): interpolate(v, context, max_depth-1) for k, v in source.items()}
    elif hasattr(source, "__iter__"):
        return [interpolate(i, context, max_depth-1) for i in source]
    else:
        return source

class DefaultSettings(object):
    PROJECT_ROOT = os.getcwd()
    TMP_BASE = uuid.uuid4().hex
    ENV_REL = "env"
    ENV_ROOT = "$PROJECT_ROOT/$ENV_REL"  # os.path.join(PROJECT_ROOT, ENV_REL)

    GITIGNORE_PYTHON = [
        "*.py[odc]",
        "dist/",
        "*.egg-info/"
    ]
    GITIGNORE_TEMPLATE = """
        .gitignore-local

        *.py[odc]
        dist/

        *.tar.gz
        *.gz
        *.zip

        build/
        ${ENV_ROOT}
    """.strip()
    GITIGNORE_TEMPLATE = textwrap.dedent(GITIGNORE_TEMPLATE)

    VIRTUALENV_VERSION = "1.11.4"
    VIRTUALENV_DOWNLOAD_LINK = "https://pypi.python.org/packages/source/v/virtualenv/virtualenv-{virtualenv_version}.tar.gz".format(virtualenv_version=VIRTUALENV_VERSION)
    VIRTUALENV_USER = "nick"
    VIRTUALENV_GROUP = "nick"
    VIRTUALENV_ARCHIVE_BASE = "virtualenv-${VIRTUALENV_VERSION}"
    VIRTUALENV_HOME = "v"

    PIP_BIN = "${VIRTUALENV_HOME}/bin/pip"
    PIP_REQUIREMENTS = "${PROJECT_ROOT}/test-requirements.txt"

    RUBY_BIN = os.path.join(ENV_ROOT, "bin/ruby")
    RUBY_GEM = os.path.join(ENV_ROOT, "bin/gem")
    RUBY_VERSION = "2.1.1"
    RUBY_ARCHIVE_ROOT = "ruby-{0}".format(RUBY_VERSION)
    RUBY_ARCHIVE_FORMAT = "tar.gz"
    RUBY_DOWNLOAD_URL = "http://cache.ruby-lang.org/pub/ruby/{0}/{1}.{2}".format(RUBY_VERSION[:-2], RUBY_ARCHIVE_ROOT, RUBY_ARCHIVE_FORMAT)

    NODEJS_VERSION = "v0.10.26"
    NODEJS_PLATFORM = "linux-x64"
    NODEJS_ARCHIVE_BASE = "node-{0}-{1}".format(NODEJS_VERSION, NODEJS_PLATFORM)
    NODEJS_ARCHIVE = "{0}.tar.gz".format(NODEJS_ARCHIVE_BASE)
    NODEJS_DOWNLOAD_URL = "http://nodejs.org/dist/{1}/{0}".format(NODEJS_ARCHIVE, NODEJS_VERSION)
    NODEJS_SYMLINK = os.path.join(ENV_ROOT, "nodejs")

def merge_settings(settings_one, settings_two):
    def settings_vars(obj):
        return {k: getattr(obj, k) for k in dir(obj) if not k.startswith("_")}
    all_attrs = settings_vars(settings_two())
    all_attrs.update(settings_vars(settings_one()))
    all_attrs = {k: interpolate(v, all_attrs) for k, v in all_attrs.items()}
    return type("Settings", (object,), all_attrs)

# Environment

def execute(cmd, fail_fast=True):
    print("$ " + " ".join(cmd))
    res = subprocess.call(cmd)
    if res != 0 and fail_fast:
        raise Exception("Command railed with {0}: {1}".format(res, cmd))
    return res

class ActivateScript(object):
    def __init__(self):
        self.vars = {}
        self.paths = set()

    def set_var(self, name, value):
        self.vars[name] = value

    def add_path(self, path):
        self.paths.add(path)

    def get_text(self):
        shebang = "#!/bin/bash"

        lines = [shebang] + ['']
        if self.vars:
            lines += ["{0}={1}".format(k, v) for k, v in self.vars.items()] + ['']
            lines += ["export {0}".format(k) for k in self.vars] + ['']
        lines += ["# Set up the path to point to the new environment."]
        lines += ["export PATH=" + ":".join(list(self.paths) + ["$PATH"])] + ['']

        return "\n".join(lines)

env_activate_script = ActivateScript()
settings = None

def initialize(settings_in):
    global settings
    settings = merge_settings(settings_in, DefaultSettings)()
    env_activate_script.add_path(os.path.join(settings.ENV_ROOT, "bin"))
    return settings

# Helpers

@contextlib.contextmanager
def chdir(dir):
    oldcwd = os.getcwd()
    os.chdir(dir)
    yield
    os.chdir(oldcwd)

def make_temp_dir(tmp_dir=None):
    os.makedirs(tmp_dir or settings.TMP_BASE)

def remove_temp_dir(tmp_dir=None):
    tmp_dir = tmp_dir or settings.TMP_BASE
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)


# Tasks

TASKS = []
def task(fn):
    TASKS.append(fn.__name__)
    return fn

def activate_script(script):
    try:
        with open(os.path.join(settings.ENV_ROOT, "activate.sh"), "w") as f:
            f.write(env_activate_script.get_text())
    except IOError as ex:
        print("Can't write activate.sh script: {0}".format(ex))

@task
def untar(archive, cwd):
    execute(["tar", "-C", cwd, "-xzvpf", archive])

@task
def gitignore(path):
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write(settings.GITIGNORE_TEMPLATE.format(
                envroot=settings.ENV_REL + "/"
            ))

@task
def virtualenv(path, tmp_dir, owner=None):
    if os.path.exists(path):
        print("virtualenv already exists")
        return

    urllib.urlretrieve(settings.VIRTUALENV_DOWNLOAD_LINK, os.path.join(tmp_dir, "virtualenv.tar.gz"))
    execute(["tar", "-C", tmp_dir, "-xzvpf", os.path.join(tmp_dir, "virtualenv.tar.gz")])
    if owner:
        sudo = ["sudo", "-u", owner]
    else:
        sudo = []

    execute(sudo + [
        "python", os.path.join(tmp_dir, os.path.join(settings.VIRTUALENV_ARCHIVE_BASE, "virtualenv.py")), settings.VIRTUALENV_HOME
    ])

    with open(os.path.join(path, "VERSION"), "w") as f:
        f.write(settings.VIRTUALENV_VERSION)

@task
def pip(requirements_file, user=None, sys_packages=False):
    sudo = []
    if user and user != getpass.getuser():
        sudo = ["sudo", "-u", user]

    cmd = sudo + [settings.PIP_BIN, "install", "-U", "-r", requirements_file]
    if sys_packages:
        cmd += ["--system-site-packages"]
    execute(cmd)

@task
def ruby(tmp_dir):
    if os.path.exists(settings.RUBY_BIN):
        print("Ruby already installed.")
        return

    urllib.urlretrieve(settings.RUBY_DOWNLOAD_URL, os.path.join(tmp_dir, "ruby.tar.gz"))
    execute(["tar", "-C", tmp_dir, "-xzvpf", os.path.join(tmp_dir, "ruby.tar.gz")])
    cwd = os.getcwd()
    os.chdir(os.path.join(settings.TMP_BASE, settings.RUBY_ARCHIVE_ROOT))
    execute(["./configure", "--prefix={0}".format(settings.ENV_ROOT)], fail_fast=True)
    execute(["make"], fail_fast=True)
    execute(["make", "install"], fail_fast=True)
    os.chdir(cwd)

@task
def gem():
    execute([settings.RUBY_GEM, "update", "--system"])

@task
def compass():
    gem_bin = os.path.join(os.path.dirname(settings.RUBY_BIN), "compass")
    if os.path.exists(gem_bin):
        print("compass already installed")
        return
    execute([settings.RUBY_GEM, "install", "compass"])

@task
def nodejs(tmp_dir):
    env_activate_script.set_var("NODEJS_HOME", os.path.join(settings.ENV_ROOT, settings.NODEJS_SYMLINK))
    env_activate_script.add_path(os.path.join(settings.NODEJS_SYMLINK, "bin"))

    if not os.path.exists(os.path.join(settings.ENV_ROOT, settings.NODEJS_ARCHIVE_BASE)):
        urllib.urlretrieve(settings.NODEJS_DOWNLOAD_URL, os.path.join(tmp_dir, settings.NODEJS_ARCHIVE))
        untar(os.path.join(tmp_dir, settings.NODEJS_ARCHIVE), tmp_dir)
        shutil.move(os.path.join(tmp_dir, settings.NODEJS_ARCHIVE_BASE), os.path.join(settings.ENV_ROOT, settings.NODEJS_ARCHIVE_BASE))
        if os.path.exists(settings.NODEJS_SYMLINK):
            os.unlink(settings.NODEJS_SYMLINK)
        os.symlink(os.path.join(settings.ENV_ROOT, settings.NODEJS_ARCHIVE_BASE), settings.NODEJS_SYMLINK)

@task
def coffeescript():
    execute([os.path.join(settings.ENV_ROOT, os.path.join(settings.NODEJS_SYMLINK, "bin/npm")), "install", "-g", "coffee-script"])


# Runner
DEFAULT_SETTINGS_FILE = os.path.join(os.getcwd(), "toilfile")

argparser = argparse.ArgumentParser()
argparser.add_argument("--settings-file", "-s", default=DEFAULT_SETTINGS_FILE, help="Settings file to read.")

def load_settings(path):
    if not os.path.exists(path):
        if os.path.exists(path + ".py"):
            path += ".py"

    if os.path.exists(path):
        module = imp.load_source("toil_settings", path)
        return module.Settings
    return DefaultSettings

def main():
    args = argparser.parse_args()
    settings = load_settings(args.settings_file)
    try:
        settings = initialize(settings)
        make_temp_dir(settings.TMP_BASE)

        if not hasattr(settings, "TASKS"):
            raise Exception("No tasks specified.")

        for task in settings.TASKS:
            if not task in TASKS:
                raise Exception("Unknown task specified: {0}".format(task))

        if "virtualenv" in settings.TASKS:
            virtualenv(settings.VIRTUALENV_HOME, settings.TMP_BASE)
        if "pip" in settings.TASKS:
            pip(settings.PIP_REQUIREMENTS, sys_packages=False)
        if "ruby" in settings.TASKS:
            ruby(settings.TMP_BASE)
        if "gem" in settings.TASKS:
            gem()
        if "nodejs" in settings.TASKS:
            nodejs(settings.TMP_BASE)
        if "coffeescript" in settings.TASKS:
            coffeescript()

        activate_script(os.path.join(settings.ENV_ROOT, "activate.sh"))

    except:
        print("An exception occurred:")
        pprint({k: getattr(settings, k) for k in dir(settings) if not k.startswith("_")})
        traceback.print_exc()

    finally:
        if os.path.exists(getattr(settings, "TMP_BASE", "None")):
            remove_temp_dir(settings.TMP_BASE)
