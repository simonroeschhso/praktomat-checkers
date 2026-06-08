from __future__ import annotations
from common import *
from utils import *
from shell import *
import re
import os
import os.path
from exercise import *
from testContext import *
import xml.etree.ElementTree as ET

# Checking Java code using Gradle

@dataclass
class JavaOptions(Options):
    sheet: Optional[str]
    gradleBuildFile: str
    runCheckstyle: bool
    checkstylePath: str
    gradleOffline: bool
    assignments: Optional[str | list[str]]

checkstyleConfig = pjoin(os.path.realpath(os.path.dirname(__file__)), 'checkstyle.xml')

# studentDir is the toplevel directory of the student's project
def execGradle(task: str, offline: bool, studentDir: str, testDir: str='test-src',
               testFilter: str='*', timeout: Optional[int] = None):
    cands = []
    buildFile = None
    for x in ['build.gradle.kts', 'build.gradle']:
        buildFile = abspath(pjoin(studentDir, x))
        if isFile(buildFile):
            break
        cands.append(buildFile)
    if buildFile is None:
        abort(f'No build file found: {cands}')
    cmd = [
        'gradle',
        '-b',
        buildFile,
        '-PtestFilter=' + testFilter,
        '-PtestDir=' + testDir,
        '-PstudentDir=' + studentDir,
        task,
        '--no-parallel',
        '--max-workers=1',
        '--no-continue'
    ]
    if isDebug():
        cmd.append('--info')
        cmd.append('--console=verbose')
    else:
        cmd.append('--warning-mode=none')
        cmd.append('-Dorg.gradle.welcome=never')
    if offline:
        cmd.append('--offline')
    debug(f'Running "{cmd}"')
    result = runWithTimeout(cmd, timeout, f'running gradle task {task}')
    return result

def checkCompile(ctx: CheckCtx, opts: JavaOptions, studentDir: str, exResult: CompileStatus):
    result = execGradle('compileJava', opts.gradleOffline, studentDir=studentDir)
    out = result.stdout
    ctx.compileOutput = out
    if result.exitcode == 0:
        ctx.compileStatus = exResult
    else:
        ctx.compileStatus = 'FAIL'

gradleTestRe = re.compile(r'^(\d+) tests completed, (\d+) failed$')

def getTestResult(testFilter: str, out: str, studentDir: str):
    out = out.replace('\r', '\n')
    testResultDir = abspath(pjoin(studentDir, '_build', 'test-results', 'test'))
    if isDir(testResultDir):
        tests = 0
        failures = 0
        errors = 0
        for file in ls(testResultDir, '*.xml'):
            tree = ET.parse(file)
            root = tree.getroot()
            if root.tag != 'testsuite':
                continue
            tests += int(root.get('tests', '0'))
            failures += int(root.get('skipped', '0'))
            failures += int(root.get('failures', '0'))
            errors += int(root.get('errors', '0'))
        if tests == 0:
            return TestResult(testFilter, out, error=True)
        else:
            return TestResult(testFilter, out, error=False, totalTests=tests,
                              testFailures=failures, testErrors=errors)
    else:
        return TestResult(testFilter, out, error=True)

def checkTest(opts: JavaOptions, assignment: Assignment, studentDir: str, testDir: str, testFilter: str, ctx: TestContext, checkCtx: CheckCtx):
    debug(f'Running tests matching {testFilter} ...')
    result = execGradle('test', opts.gradleOffline, studentDir=studentDir, testDir=testDir,
                        testFilter=testFilter, timeout=testTimeoutSeconds())
    testResult = getTestResult(testFilter, result.stdout, studentDir)
    ctx.results.append(testResult)
    abortIfTestOkRequired(assignment, testResult, checkCtx)

def checkStyle(ctx: CheckCtx, studentDir: str, checkstylePath: str, config: str=checkstyleConfig):
    sourceFiles = []
    for root, dirs, files in os.walk(studentDir):
        for name in files:
            if name.lower().endswith('.java'):
               sourceFiles.append(os.path.join(root, name))
    cmd = [
        'java',
        '-cp',
        checkstylePath,
        '-Dbasedir=.',
        'com.puppycrawl.tools.checkstyle.Main',
        '-c',
        config,
    ]
    cmd += sourceFiles
    debug(f'Running "{cmd}"')
    result = run(cmd, onError='ignore', stderrToStdout=True, captureStdout=True)
    out = result.stdout
    # remove absolute paths from output
    if studentDir and studentDir[0] == '/':
        x = studentDir.rstrip('/') + '/'
        out = out.replace(x, '')
    hasErrors = 'ERROR' in out or result.exitcode != 0
    if hasErrors:
        print('Checking code style FAILED')
        print()
        print(out)
        print()
        print('Here are the style rules to follow:')
        print('- Naming conventions')
        print('  - All identifiers except for constants in camel case, do not use underscores to separate words')
        print('  - Names of classes, interfaces, records and enums start with an uppercase letters')
        print('  - Names of methods and variables start with a lowercase letter')
        print('  - Names of constants are written in SCREAMING_CASE')
        print('- Indentation')
        print('  - Indent a block with four spaces')
        print('  - Do NOT use tabs, this might require to change the settings of your IDE')
        print()
        abort('Aborting')
    ctx.styleResult = StyleResult(hasErrors=hasErrors, styleOutput=result.stdout.replace('\r', '\n'))

def srcExists(s: str) -> bool:
    if s.endswith('.java'):
        return isFile(s)
    else:
        return isDir(s)

def checkFilesExist(ass: list[Assignment], prjDir: str):
    missing = []
    prjDir = prjDir.rstrip('/') + '/'
    for a in ass:
        if a.src is None:
            # Nothing specified -> skip
            continue
        srcFile = pjoin(prjDir, a.src)
        if not srcExists(srcFile) and a.src not in missing:
            missing.append(a.src)
    if missing:
        print('ERROR: The following files are missing in your submission:')
        for f in missing:
            print(f'- {f}')
        print()
        files = run(f"find '{prjDir}' -name '*.java'", captureStdout=splitLines).stdout
        if files:
            print(f'The following .java files are present:')
            for f in files:
                print('- ' + removeLeading(f, prjDir))
        else:
            print(f'No java files found in your submission')
        if len(missing) == len(ass):
            print()
            abort('All files missing, aborting')
        return 'OK_BUT_SOME_MISSING'
    else:
        return 'OK'

def dirnameForSource(s: str):
    if s.endswith('.java'):
        return dirname(s)
    else:
        return s

def dirnameForFilter(s: str):
    s = s.replace('.', '/')
    # Try to find the first class name (assumption: it's the only capitalized element)
    # or wildcard, then continue with its parent directory
    pathElements = s.split('/')
    for i, p in enumerate(pathElements):
        if (len(p) > 0 and p[0].isupper()) or '*' in p:
            pathElements = pathElements[:i]
            break
    return os.path.join('test-src', *pathElements)

def checkWithSourceDir(opts: JavaOptions, projectDir: str, sheetDir: str, ass: list[Assignment]):
    ctx = CheckCtx.empty('Compile', opts.resultFile)
    # do the checks
    debug(f'projectDir={projectDir}')
    cp(opts.gradleBuildFile, projectDir)
    exResult = checkFilesExist(ass, projectDir)
    if opts.runCheckstyle:
        checkStyle(ctx, projectDir, opts.checkstylePath)
    checkCompile(ctx, opts, projectDir, exResult)
    for a in ass:
        testCtx = TestContext(assignment=a, sheet=opts.sheet, results=[])
        ctx.tests.append(testCtx)

        testDirectories = list(map(dirnameForSource, a.tests))
        if a.testFilter:
            testDirectories.append(dirnameForFilter(a.testFilter))
        for td in testDirectories:
            if not isDir(pjoin(sheetDir, td)):
                abort(f'Configuration error: test directory {td} does not exist in {sheetDir}.')

        if len(testDirectories) > 0:
            testFilter = a.testFilter or '*'
            withLimitedDir(sheetDir, testDirectories, lambda d: checkTest(opts, a, projectDir, d, testFilter, testCtx, ctx))
    outputResultsAndExit(ctx)

def check(opts: JavaOptions):
    sheetDir = getSheetDir(opts.testDir, opts.sheet)
    exFile = pjoin(sheetDir, 'exercise.yaml')
    ex = parseExercise(opts.sheet, exFile)
    debug(f'Exercise (file: {exFile}): {ex}')
    projectDir = findSolutionDir(opts.sourceDir, lambda x: isDir(pjoin(x, "src")))
    debug(f'projectDir={projectDir}')
    fixEncodingRecursively(projectDir, 'java')
    if opts.assignments:
        ex.ensureAssignmentsDefined(asList(opts.assignments))
        l = asList(opts.assignments)
        ass = [a for a in ex.assignments if a.id in l]
        subs = set([dirnameForSource(a.src) for a in ass if a.src is not None])
        for sub in subs:
            if not isDir(pjoin(projectDir, sub)):
                abort(f'Directory {sub} required for one of the selected assignments does not exist')
        withLimitedDir(projectDir, list(subs), lambda d: checkWithSourceDir(opts, d, sheetDir, ass))
    else:
        checkWithSourceDir(opts, projectDir, sheetDir, ex.assignments)
