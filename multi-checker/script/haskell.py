from __future__ import annotations
from common import *
from utils import *
from shell import *
import re
from exercise import *
from testContext import *

@dataclass
class HaskellOptions(Options):
    sheet: Optional[str]

def checkCompile(ctx: CheckCtx):
    cmd = 'stack test --only-locals'
    debug(f'Running "{cmd}"')
    tmpName = mkTempFile(suffix='.log')
    capture = None
    try:
        if isDebug():
            capture = createTee([TEE_STDOUT, tmpName])
        else:
            capture = open(tmpName, 'w')
        result = run(cmd, onError='ignore', stderrToStdout=True, captureStdout=capture)
    finally:
        if capture:
            capture.close()
    out = readFile(tmpName)
    if result.exitcode == 0:
        ctx.compileOutput = out
        ctx.compileStatus = 'OK'
    else:
        print(f'"{cmd}" failed\n\n{out}')
        findOut = run("find . -type f | xargs ls -l", onError='ignore', stderrToStdout=True, captureStdout=True).stdout
        debug(f"Directory listing:\n{findOut}")
        abort("Aborting")

haskellTestRe = re.compile(r'^Cases:\s*(\d+)\s*Tried:\s*(\d+)\s*Errors:\s*(\d+)\s*Failures:\s*(\d+)')
magicLine = "__START_TEST__"

def getTestResult(testFile, out: str):
    after = False
    lastTestLine = None
    out = out.replace('\r', '\n')
    # running the tests in ghci always exists with ExitFailure 1. Don't show this to the students.
    exitStr = '*** Exception: ExitFailure 1'
    i = out.find(exitStr)
    if i >= 0:
        cleanOut = out[:i] + out[i+len(exitStr):]
    else:
        cleanOut = out
    for line in out.split('\n'):
        line = line.rstrip()
        if line == magicLine:
            after = True
        if after:
            m = haskellTestRe.match(line)
            if m:
                lastTestLine = line
    if lastTestLine:
        m = haskellTestRe.match(lastTestLine)
        if not m:
            print('Cannot parse test output!')
            return TestResult(testFile, cleanOut, True)
        cases = int(m.group(1))
        tried = int(m.group(2))
        errors = int(m.group(3)) + (cases - tried)
        failures = int(m.group(4))
        return TestResult(testFile, cleanOut, False, cases, errors, failures)
    else:
        return TestResult(testFile, cleanOut, True)

def checkTest(assignment: Assignment, ctx: TestContext, testFile: str, incDirs: list[str], checkCtx: CheckCtx):
    prjName = 'ap' + str(assignment.sheet)
    testModName = removeExt(basename(testFile))
    srcFile = assignment.src
    incOpts = []
    for d in incDirs:
        incOpts.append(f'--ghci-options -i{d}')
    cmd = f'stack --silent ghci "{srcFile}" "{testFile}" --flag {prjName}:test-mode ' + \
          " ".join(incOpts) + \
          f' --ghci-options -e --ghci-options ":m {testModName}"' + \
          f' --ghci-options -e --ghci-options {testModName}.tutorMain'
    debug(f'Executing tests {testFile} for {srcFile} ...')
    debug(f'Command: {cmd}')
    result = run(cmd, onError='ignore', stderrToStdout=True, captureStdout=True)
    testResult = getTestResult(testFile, 'Command: ' + cmd + '\n\n' + result.stdout)
    ctx.results.append(testResult)
    abortIfTestOkRequired(assignment, testResult, checkCtx)

pragmaRe = re.compile(r'^\s*{-# OPTIONS_GHC -Wno.*$', re.MULTILINE)
def checkHsFile(path):
    content = open(path).read()
    m = pragmaRe.search(content)
    if m:
        abort(f'Source file {path} contains illegal pragma: {m.group(0)}')

BLACKLIST = ['package.yaml', 'stack.yaml']
def doCheck(srcDir, sheetDir, sheet, resultFile):
    exFile = pjoin(sheetDir, 'exercise.yaml')
    ex = parseExercise(sheet, exFile)
    debug(f'Exercise (file: {exFile}): {ex}')
    # copy files
    for x in ls(srcDir):
        name = basename(x)
        if name.startswith('.') or name in BLACKLIST or name.endswith('.cabal'):
            continue
        if name.endswith('.hs'):
            checkHsFile(x)
        cp(x, '.')
    cp(pjoin(sheetDir, 'package.yaml'), '.')
    cp(pjoin(sheetDir, 'stack.yaml'), '.')
    # do the checks
    missing = 0
    for a in ex.assignments:
        if a.src and not isFile(a.src):
            print(f'ERROR: File {a.src} not included in submission. I found the following .hs files:')
            run(f'find . -name "*.hs" | head -20')
            missing += 1
    if missing == len(ex.assignments):
        abort('All source files missing!')
    ctx = CheckCtx.empty('Compile', resultFile)
    checkCompile(ctx)
    for a in ex.assignments:
        testCtx = TestContext(assignment=a, sheet=sheet, results=[])
        ctx.tests.append(testCtx)
        for t in a.tests:
            checkTest(a, testCtx, pjoin(sheetDir, t), [pjoin(sheetDir, 'lib'), sheetDir], ctx)
        checkScript(a, testCtx, sheetDir, ctx)
    outputResultsAndExit(ctx)

def check(opts: HaskellOptions):
    nestedSourceDir = findSolutionDir(opts.sourceDir)
    with tempDir(dir='.') as d:
        with workingDir(d):
            debug(f"Running Haskell checks from directory {d}")
            sheetDir = getSheetDir(opts.testDir, opts.sheet)
            doCheck(nestedSourceDir, sheetDir, opts.sheet, opts.resultFile)
