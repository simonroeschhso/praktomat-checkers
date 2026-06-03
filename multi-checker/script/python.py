from dataclasses import dataclass
from typing import Optional
from shell import *
import sys
import os
from utils import *
from common import *
from exercise import *
from testContext import *
from typing import *

def configError(s):
    abort('Config error: ' + s)

@dataclass
class PythonOptions(Options):
    sheet: Optional[str]
    assignments: Optional[str | list[str]]
    wypp: str

def prepareEnv(testEnv: Optional[dict], searchDirs: list[str]) -> dict:
    if testEnv is None:
        testEnv = {}
    else:
        testEnv = testEnv.copy()
    if searchDirs:
        l: list[str] = []
        for x in searchDirs:
            x = x.strip()
            if not x:
                x = '.'
            x = os.path.normpath(x)
            if x not in l:
                l.append(x)
        searchDirs = l
        key = 'PYTHONPATH'
        pyPath = ':'.join(searchDirs)
        oldPyPath = os.getenv(key)
        if oldPyPath:
            pyPath = pyPath + ':' + oldPyPath
        testEnv[key] = pyPath
    return testEnv

def runWypp(studentFile: str, wyppPath: str, onlyRunnable: bool, typecheck: bool,
            testFile: Optional[str]=None, testEnv: Optional[dict]=None, timeout: Optional[int]=None):
    thisDir = abspath('.')
    # print('pyPath='+pyPath)
    testEnv = prepareEnv(testEnv, [wyppPath + '/python/code:', thisDir])
    args = ['python3', wyppPath + '/python/code/wypp/runYourProgram.py', '--lang', 'de']
    if testFile:
        args = args + ['--test-file', testFile]
    args = args + ['--check-runnable' if onlyRunnable else '--check']
    if not typecheck:
        args = args + ['--no-typechecking']
    args = args + [studentFile]
    res = runWithTimeout(args, timeout, f'running {studentFile} via WYPP, testFile={testFile}',
                         env=testEnv)
    return res

def runUnittest(testFile: str, searchDirs: list[str], testEnv: Optional[dict]=None,
                timeout: Optional[int]=None):
    if not isFile(testFile):
        abort(f'Test file {testFile} does not exist')
    testEnv = prepareEnv(testEnv, ['.'] + searchDirs)
    args = ['python3', testFile]
    res = runWithTimeout(args, timeout, f'running unittests in {testFile}', env=testEnv)
    return res

LoadStudentCodeStatus = Literal['ok', 'fail', 'not_found']

@dataclass
class LoadStudentCodeResult:
    status: LoadStudentCodeStatus
    output: str
    srcDir: Optional[str]

LoadCheck = Literal['dont-load', 'load-no-typecheck', 'load-typecheck']

def loadStudentCode(opts: PythonOptions, p: str, checkLoad: LoadCheck) -> LoadStudentCodeResult:
    """
    Checks that the student file loads ok and that the student tests are successful.
    Executed from within source dir.
    """
    if checkLoad not in ['dont-load', 'load-no-typecheck', 'load-typecheck']:
        raise ValueError('Invalid value for checkLoad argument: ' + str(checkLoad))
    _out = ''
    def printOut(s='', emptyNewline=True):
        nonlocal _out
        if s or emptyNewline:
            _out = _out + s + '\n'
    _srcDir = None
    def mkResult(status: LoadStudentCodeStatus) -> LoadStudentCodeResult:
        return LoadStudentCodeResult(status, _out, _srcDir)
    studentFile = findFile(p, '.', ignoreCase=True)
    if not studentFile:
        pyFilesList = run(f'find . -name "*.py"', captureStdout=splitLines, onError='ignore').stdout
        pyFiles = '\n'.join(pyFilesList[:20])
        printOut(f'''ERROR: File {p} not part of the submission. I found the following files:

{pyFiles}''')
        return mkResult('not_found')
    _srcDir = dirname(studentFile)
    fixEncoding(studentFile)
    if checkLoad == 'dont-load':
        printOut(f'Only checking that file {studentFile} exists, not loading.')
        return mkResult('ok')
    printOut()
    printOut(f'## Checking that {p} loads successfully ...')
    typecheck = checkLoad == 'load-typecheck'
    runRes = runWypp(studentFile, opts.wypp, onlyRunnable=True, typecheck=typecheck,
                     timeout=testTimeoutSeconds())
    printOut(runRes.stdout, emptyNewline=False)
    if runRes.exitcode == 0:
        printOut(f'## OK: {p} loads successfully')
    else:
        printOut(f'''File {p} could not be loaded.
You find more error messages above.''')
        return mkResult('fail')
    printOut()
    printOut(f'## Executing tests in {p} ...')
    testRes = runWypp(studentFile, opts.wypp, onlyRunnable=False, typecheck=typecheck,
                      timeout=testTimeoutSeconds())
    printOut(testRes.stdout, emptyNewline=False)
    if testRes.exitcode == 0:
        printOut(f'## OK: no test failures in {p}')
    elif testRes.exitcode == TIMEOUT_EXIT_CODE:
        printOut(f'Timeout for tests in {p}. Probably there is an infinite loop!')
    else:
        printOut(f'''File {p} contains test failures!
If you cannot make a test succeed, you have to comment it out.''')
    return mkResult('ok')

def checkFileLoadsOk(opts: PythonOptions, p: str):
    res = loadStudentCode(opts, p, 'load-typecheck')
    print(res.output)
    return res.status

def checkAssignmentsLoadOk(opts: PythonOptions, ass: str | list[str] | None):
    if isinstance(ass, str):
        ass = [ass]
    elif ass is None:
        ass = []
    delim = '=============================================================================='
    stats = []
    for x in ass:
        possible_filenames = [
            f'aufgabe_{x.zfill(2)}.py',
            f'aufgabe_{x}.py',
            f'aufgabe{x.zfill(2)}.py',
            f'aufgabe{x}.py',
            f'aufgabe-{x.zfill(2)}.py',
            f'aufgabe-{x}.py',
        ]
        # Use a default file name in case none is found.
        # The script will then fail at a later point.
        p = possible_filenames[0]
        for name in possible_filenames:
            if findFile(name, '.', ignoreCase=True) is not None:
                p = name
                break
        print(f'\n{delim}')
        print(f'Checking assignment {x} (file: {p})')
        stat = checkFileLoadsOk(opts, p)
        stats.append((p, stat))
    print('\n')
    print(delim)
    print('Summary')
    print()
    warn = False
    err = False
    for (p, stat) in stats:
        match stat:
            case 'not_found':
                print(f'{p}: not found')
                warn = True
            case 'fail':
                print(f'{p}: failed')
                err = True
    print()
    if err:
        print('Error: at least one assignment failed!')
        sys.exit(1)
    if warn:
        print('Warn: at least one assignment not found')
        sys.exit(OK_WITH_WARNINGS_EXIT_CODE)

class PythonTestResult:
    @staticmethod
    def parseWyppResult(testFile: str, s: str):
        r1 = re.compile(r'^Tutor:\s*(\d+) Tests, (\d+) Fehler')
        r2 = re.compile(r'^Tutor:\s*(\d+) Tests, alle erfolgreich')
        for l in s.split('\n'):
            m1 = r1.match(l)
            m2 = r2.match(l)
            if m1 or m2:
                total = 0
                fail = 0
                if m1:
                    total = int(m1.group(1))
                    fail = int(m1.group(2))
                elif m2:
                    total = int(m2.group(1))
                    fail = 0
                return TestResult(testFile=testFile, testOutput=s, error=False, totalTests=total,
                        testFailures=fail, testErrors=0)
    @staticmethod
    def parseUnitResult(testFile: str, s: str):
        # Ran 3 tests in 0.000s
        # FAILED (errors=1)
        # FAILED (failures=1, errors=1, skipped=1)
        # OK
        # OK (skipped=5)
        total = -1
        errors = 0
        failures = 0
        skipped = 0
        r = re.compile('^Ran (\\d+) test')
        def getKv(l, k):
            r = re.compile(f'{k}=(\\d+)')
            m = r.search(l)
            if m:
                return int(m.group(1))
            else:
                return 0
        for l in s.split('\n'):
            l = l.strip()
            m = r.match(l)
            if m:
                total = int(m.group(1))
            if l.startswith('FAILED'):
                errors = getKv(l, 'errors')
                failures = getKv(l, 'failures')
                skipped = getKv(l, 'skipped')
            if l.startswith('OK'):
                skipped = getKv(l, 'skipped')
        if total > 0:
            return TestResult(testFile=testFile, testOutput=s, error=False,
                    totalTests=(total - skipped), testFailures=failures, testErrors=errors)

def getTestResult(testFile, runRes: RunResult):
    r = PythonTestResult.parseWyppResult(testFile, runRes.stdout)
    if r:
        return r
    r = PythonTestResult.parseUnitResult(testFile, runRes.stdout)
    if r:
        return r
    return TestResult(testFile=testFile, testOutput=runRes.stdout, error=(runRes.exitcode != 0),
            totalTests=0, testFailures=0, testErrors=0)

def checkTutorTests(opts: PythonOptions,
                    testCtx: TestContext,
                    a: Assignment,
                    srcDir: Optional[str],
                    checkCtx: CheckCtx):
    """
    Checks the tutor tests. Executed from within the source dir.
    """
    for t in a.tests:
        testEnv = {'CHECK_ASSIGNMENT': a.id, 'CHECK_TEST': t}
        testPath = pjoin(sheetDir(opts), t)
        if a.pythonConfig.wypp:
            src = a.src
            if src is None:
                abort(f'Configuration error: src option not set for assignment {a.id}')
                return
            if srcDir:
                src = pjoin(srcDir, src)
            testOut = runWypp(src, opts.wypp, onlyRunnable=False,
                              typecheck=a.pythonConfig.typecheck,
                              testFile=testPath, testEnv=testEnv, timeout=testTimeoutSeconds())
        else:
            searchDirs = [opts.wypp + '/python/code']
            if srcDir:
                searchDirs.append(srcDir)
            testOut = runUnittest(testPath, searchDirs,
                                  testEnv=testEnv, timeout=testTimeoutSeconds())
        testRes = getTestResult(t, testOut)
        testCtx.results.append(testRes)
        abortIfTestOkRequired(a, testRes, checkCtx)
    pass

def checkAssignments(opts: PythonOptions, ex: Exercise, allAss: list[Assignment]):
    """
    Checks the given assignments by checking if the code loads successfully and
    if it passes the tutor tests.
    Executed from within the source dir.

    This function is called if an exercise.yaml file exists.
    """
    allFiles = []
    extras = set()
    for a in allAss:
        if a.src is not None and a.src not in [x[0] for x in allFiles]:
            checkLoad: LoadCheck = 'dont-load'
            pc = a.pythonConfig
            if pc.typecheck:
                checkLoad = 'load-typecheck'
            elif pc.checkLoad:
                checkLoad = 'load-no-typecheck'
            allFiles.append((a.src, checkLoad))
            for e in a.extraFiles:
                extras.add(e)
    for e in extras:
        cp(pjoin(sheetDir(opts), e), '.')
    ctx = CheckCtx.empty('Load and student tests', opts.resultFile)
    compileStatus = 'OK'
    missing = 0
    srcDirDict = {} # a.src -> directory where file is found
    for p, checkLoad in allFiles:
        res = loadStudentCode(opts, p, checkLoad)
        if res.srcDir:
            srcDirDict[p] = res.srcDir
        ctx.appendCompileOutput(res.output)
        match res.status:
            case 'fail':
                compileStatus = 'FAIL'
            case 'ok':
                pass
            case 'not_found':
                missing = missing + 1
                # print(f'File {p} missing')
    if compileStatus == 'OK' and missing > 0:
        if missing == len(allFiles):
            compileStatus = 'FAIL'
            print('All files missing')
        else:
            compileStatus = 'OK_BUT_SOME_MISSING'
    ctx.compileStatus = compileStatus
    for a in allAss:
        testCtx = TestContext(assignment=a, sheet=ex.sheet, results=[])
        ctx.tests.append(testCtx)
        checkTutorTests(opts, testCtx, a, srcDirDict.get(a.src), ctx)
        checkScript(a, testCtx, sheetDir(opts), ctx)
    outputResultsAndExit(ctx)

def sheetDir(opts: PythonOptions):
    return getSheetDir(opts.testDir, opts.sheet)

def check(opts: PythonOptions):
    sheet = opts.sheet
    exFile = pjoin(sheetDir(opts), 'exercise.yaml')
    if isFile(exFile):
        ex = parseExercise(sheet, exFile)
    else:
        ex = None
    debug(f'Exercise (file: {exFile}): {ex}')
    ass = opts.assignments
    nestedSourceDir = findSolutionDir(opts.sourceDir)
    with workingDir(nestedSourceDir):
        if ex is None:
            if ass is None:
                configError(f'Option --assignment not given, exercise file {exFile} not found')
            checkAssignmentsLoadOk(opts, ass)
        else:
            if ass is None:
                allAss = ex.assignments
            else:
                l = asList(ass)
                ex.ensureAssignmentsDefined(l)
                allAss = [a for a in ex.assignments if a.id in l]
            checkAssignments(opts, ex, allAss)
