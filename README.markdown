TOIL
====

A project to help with managing development tasks.

Place a file called 'toilfile' in the root of the environment directory and run:

    toil

Example toilfile
----------------

    class Settings(object):
        TASKS = ["virtualenv", "pip", "nodejs", "coffeescript"]
        ENV_REL = ".env"
        PIP_REQUIREMENTS = "requirements-cpython.txt"

Tasks available
---------------

virtualenv: download the virtualenv source and create a virtual environment.

pip: install packages from a file called pip-requirements.txt.  You can
  specify the PIP_REQUIREMENTS settings in your toilfile

nodejs: Download and build nodejs and place it in your development environment.

coffeescript: Download and build nodejs and place it into your development environment.  (requires nodejs)

ruby: Download and build ruby and place it in your development environment.

gem: Update gem.

compass: Download and install compass and place it in your development environment.  (requires ruby)

Roadmap
-------

Up next:
* Make tasks more 'plugable'.
* Add clean command.
* Add more tasks.
* Test on supported python versions.
* Add init command to create initial toilfile.
* PIP packages should be specified in the toilfile.
* System packages should be specified in the toilfile.


Python version support
----------------------

* Python 2.7
* Python 3.2, 3.3, 3.4, 3.5
* PyPy latest stable

