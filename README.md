# Praktomat Checkers with Docker

This repository contains checkers for praktomat when used with Docker.
The checkers are independent from concrete tests for specific
courses. Such tests can be found, for example, [here](https://git.hs-offenburg.de/swehr/praktomat-tests).

## Checkers

At the moment, there is only one checkers, the `multi-checker`

### multi-checker

To be used with python, haskell and Java submissions.

* Python submission use [WYPP](https://github.com/skogsbaer/write-your-python-program)
  or the unit testmodule.
* Haskell submissions are checked for compile errors (via `stack test`) and instructors
  can also provide unit tests to be run against student's submission. The
  [praktomat-tests](https://git.hs-offenburg.de/swehr/praktomat-tests) repository contains
  examples for such unit tests.
* Java submissions are checked using Gradle. The submission will be compiled and the specified
  tests will be run against the student's submission. Also, a coding style check will be
  performed.

See `multi-checker/tests/runTests.py` for examples showcasing these checkers.

In principle, multi-checker could be separated into a python, a Java, and a haskell checker.
But the checker script (files in `multi-checker/script/`) shares some logic between
both languages, so we created only one checker for simplicity.

Commandline options: invoke with `--help`

Environment variables:

* `PRAKTOMAT_CHECKER_TEST_TIMEOUT`: timeout in seconds


## How it works

Praktomat has the `ScriptChecker`, which simply runs a shell script
against the student submission. The shell script is executed
inside the directory containing the student submission. The exit code
of this shell script communicates the result of the checker back to praktomat.

The shell script runs either in the same environment as praktomat (same
machine or same docker container) or it runs inside an extra docker container.
Praktomat with its Docker integration takes care of the latter case.

When runing praktomat via docker (see
https://github.com/hso-praktomat/praktomat-docker), you enable
execution inside an extra docker container by setting
the environment variable `PRAKTOMAT_CHECKER_IMAGE` to the docker
image the checker script should run in. Two more environment variables
are available for tweaking:

* `PRAKTOMAT_CHECKER_UID_MOD` prevents the UID and GID of the user
 executing the checks in the Docker container from being modified to match
 those of the user running Praktomat.
 Keep in mind that you might run your checkers as root (although it's just inside the container). It is determined by what you specify in your Dockerfile.
* `PRAKTOMAT_CHECKER_WRITABLE` can be used to make the filesystem of a
 container writable when running a checker. Otherwise, it's read-only.
 However, the directory containing the submission is always writable, regardless of this setting.
* `PRAKTOMAT_CHECKER_EXTERNAL_DIR` can be set to a directory on the host system. This directory
  is made available to the checker scripts as `/external`.
* `PRAKTOMAT_CHECKER_ENABLE_NETWORK=True` enables network in the checker
  container.

Running checkers with Docker enforces several restrictions:

* The checker script finish within 60 seconds. (Setting
  `TEST_TIMEOUT` in local.py der Praktomat-Instanz)
* The checker script must not use more than 1GB of resident size.
  (Setting `TEST_MAXMEM`)
* The checker script must not create files of size greater than 512MB.
  (Setting `TEST_MAXFILESIZE`)
* The checker script has an upper limt of 8192 on the number of open
  files. (Setting `TEST_MAXFILENUMBER`)
* Only files within the current directory are readable.
* Environment variable `HOME` is set to the directory holding the
  submission. You might change this in the checker script.

## How to write a new checker

* Subdirectory `checker-container` contains a dockerfile specifying a base
  image for the checkers in this repo.
* Write a new dockerfile that builds an image containing everything you
  need to run your checker script. You should use the base image
  from `checker-container` as the base of your new image.
* Write one ore more checker script. At the moment, you need for every
  phase (compilation, running student's tests, running instructor's tests)
  a different script, potentially also for different assignments. This
  script is uploaded to the task definition in praktomat and is executed
  for each submission in a docker container using the image specified
  in the preceding step. When the script is execute, the current
  working directory contains the file the student submitted, already in
  unzipped form.

## Internal notes

### How external dir is propagated

* `PRAKTOMAT_CHECKER_EXTERNAL_DIR` is set in the environment (docker-compose.yaml)
  * Might contain `${TASK_ID_CUSTOM}`, which will be replaced by the value of a text field in the
    configuration of the task
* The env var is used to configure the praktomat setting `DOCKER_CONTAINER_EXTERNAL_DIR`
  * praktomat-docker
* The `DOCKER_CONTAINER_EXTERNAL_DIR` setting is used to create the `--volume=...:/external:ro`
  cmdline flag when running then checker.
  * praktomat in `safeexec.py`
  * this is where `${TASK_ID_CUSTOM}` gets replaced

How to get the sample solutions back in?
Here is a simple but flexible solution:

* A task in praktomat can have it's own volumen mapping. Simple a textfield, and then you
  configure `DIR_ON_THE_HOST_SYSTEM:/external_solution:ro` there
* The praktomat checker gets a new commandline option `--solution-dir`
* We also need to configure networkability for the LLM-Tutor task.
