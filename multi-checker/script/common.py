from dataclasses import dataclass
from typing import *
from shell import *
from utils import *

OK_WITH_WARNINGS_EXIT_CODE = 121

# Exit code of the timeout command on timeout
TIMEOUT_EXIT_CODE = 124

@dataclass
class Options:
    sourceDir: str
    testDir: Optional[str]
    resultFile: Optional[str]

def getSheetDir(testDir: Optional[str], sheet: str):
    if testDir is None:
        return '/external'
    return pjoin(testDir, sheet)

def getSolutionDir(solutionDir: Optional[str]):
    if solutionDir is None:
        return '/solution'
    return solutionDir
    
def getPdfDir(pdfDir: Optional[str]):
    if pdfDir is None:
        return '/pdf'
    return pdfDir

def replaceAll(l: list[str], repl: str, s: str) -> str:
    for x in l:
        s = s.replace(x, repl)
    return s

def testTimeoutSeconds(default: int=60):
    fromEnv = os.getenv('PRAKTOMAT_CHECKER_TEST_TIMEOUT')
    debug('Timeout from environment: ' + str(fromEnv))
    if fromEnv:
        try:
            return int(fromEnv)
        except TypeError:
            pass
    return default

def runWithTimeout(cmd: list[str], timeout: Optional[int], what: str, env: dict=None):
    # Note: I first tried using the unix timeout command. But the combination with gradle
    # and the subprocess did not work, the process just hung.
    debug(f'Command: {" ".join(cmd)}')
    #res = subprocess.run(cmd, env=env)
    res = run(cmd, onError='ignore', env=env, stderrToStdout=True, captureStdout=True, timeout=timeout)
    ecode = res.exitcode
    debug(f'Exit code: {ecode}')
    if timeout and ecode == TIMEOUT_EXIT_CODE:
        msg = f'Timeout after {timeout}s while {what}'
        debug(msg)
        newStdout = res.stdout
        if newStdout:
            newStdout = newStdout + '\n\n' + msg
        else:
            newStdout = msg
        return RunResult(newStdout, res.stderr, TIMEOUT_EXIT_CODE)
    else:
        return RunResult(res.stdout, res.stderr, ecode)
