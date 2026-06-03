from __future__ import annotations
from common import *
from utils import *
from shell import *
import re
from exercise import *

CompileStatus = Literal['OK', 'FAIL', 'OK_BUT_SOME_MISSING']

@dataclass
class CheckCtx:
    compileTitle: str
    compileStatus: CompileStatus
    compileOutput: Optional[str]
    tests: list[TestContext]
    styleResult: Optional[StyleResult]=None
    outFile: Optional[str] = None
    @staticmethod
    def empty(t: str, outFile: Optional[str]) -> CheckCtx:
        return CheckCtx(t, 'FAIL', None, [], outFile=outFile)
    def appendCompileOutput(self, s: str):
        if self.compileOutput:
            self.compileOutput = self.compileOutput + '\n' + s
        else:
            self.compileOutput = s
    def asDict(self):
        testList = []
        d = {'compileStatus': self.compileStatus, 'tests': testList}
        for t in self.tests:
            testList.append(t.asDict())
        return d
    def serialize(self, path):
        import pickle
        d = self.asDict()
        with open(path, 'wb') as f:
            pickle.dump(d, f)
        print('Dumped test results to ' + abspath(path))

@dataclass
class TestContext:
    sheet: Optional[str]
    assignment: Assignment
    results: list[TestResult]
    def summarizeResults(self) -> TestResult:
        r = TestResult("?", "", False)
        for x in self.results:
            if x.error:
                r.error = True
            else:
                r.totalTests += x.totalTests
                r.testErrors += x.testErrors
                r.testFailures += x.testFailures
        return r
    def asDict(self):
        error = False
        totalTests = 0
        testErrors = 0
        testFailures = 0
        for r in self.results:
            if r.error:
                error = True
            totalTests += r.totalTests
            testErrors += r.testErrors
            testFailures += r.testFailures
        return {'sheet': self.sheet, 'assignment': self.assignment.id,
                'error': error, 'totalTests': totalTests, 'testErrors': testErrors,
                'testFailures': testFailures}

@dataclass
class TestResult:
    testFile: str
    testOutput: str
    error: bool          # Running the test failed with an error
    totalTests: int = 0
    testErrors: int = 0
    testFailures: int = 0
    @property
    def isSuccess(self):
        return not self.error and self.testErrors == 0 and self.testFailures == 0

@dataclass
class StyleResult:
    hasErrors: bool
    styleOutput: Optional[str]

def outputResultsAndExit(ctx: CheckCtx, ecode=None):
    if ctx.outFile:
        ctx.serialize(ctx.outFile)
    print(ctx.compileTitle + ' status: ' + ctx.compileStatus)
    notOkTotal = 0
    hasErrors = False
    totalPoints = 0
    possibleTotalPoints = 0
    if not ctx.tests:
        print('No tests found')
    else:
        print('Test results:')
        maxAssignmentIdLen = max([len(testCtx.assignment.id) for testCtx in ctx.tests])
        maxPoints = max([testCtx.assignment.points for testCtx in ctx.tests])
        maxPointsLen = len(f'{maxPoints:.1f}')
        for testCtx in ctx.tests:
            res = testCtx.summarizeResults()
            assPoints = testCtx.assignment.points
            assPointsFmt = f'{assPoints:.1f}'
            space1 = (maxPointsLen - len(assPointsFmt)) * ' '
            possibleTotalPoints += assPoints
            if res.error:
                zero = f'0.0/{assPoints:.1f} points,'
                shortResStr = f'{zero:15} ERROR'
                hasErrors = True
            else:
                if res.totalTests > 0:
                    notOk = res.testErrors + res.testFailures
                    notOkTotal += notOk
                    ok = res.totalTests - notOk
                    ratio = ok / res.totalTests
                    percentage = round(100 * ratio)
                    if assPoints > 0:
                        points = round(ratio * assPoints, 1)
                        totalPoints = totalPoints + points
                        pointsFmt = f'{points:.1f}'
                        space = (maxPointsLen - len(pointsFmt)) * ' '
                        pointsStr = f'{space}{pointsFmt}/{assPointsFmt} {space1}points,'
                    else:
                        space = (maxPointsLen - 1) * ' '
                        pointsStr = f'{space}?/{assPointsFmt} {space1}points,'
                    percentageStr = f'{percentage}% OK,'
                    rest = f'({res.totalTests} tests, {res.testErrors} errors, {res.testFailures} failures)'
                    shortResStr = f'{pointsStr:15} {percentageStr:10} {rest}'
                else:
                    space = (maxPointsLen - 1) * ' '
                    q = f'{space}?/{assPointsFmt} {space1}points,'
                    shortResStr = f'{q:15} no tests'
            id = testCtx.assignment.id
            space = (maxAssignmentIdLen - len(id)) * ' '
            print(f'Assignment {id}:{space} {shortResStr}')
    if ctx.styleResult != None:
        styleStatusShort = "ERROR" if ctx.styleResult.hasErrors else "OK"
        print('\nCoding style: ' + styleStatusShort)
    print(f'\nTotal points: {totalPoints:.1f}/{possibleTotalPoints:.1f} (preliminary, subject to change!)')
    def printWithTitle(title, msg):
        delim = 2 * '=============================================================================='
        print()
        print(delim)
        print(title)
        print(delim)
        print()
        print(msg)
    if ctx.compileOutput:
        printWithTitle(ctx.compileTitle + ' output', ctx.compileOutput)
    if ctx.styleResult != None and ctx.styleResult.styleOutput != None:
        printWithTitle('Output of style check', ctx.styleResult.styleOutput)
    for testCtx in ctx.tests:
        for testRes in testCtx.results:
            title = f'Output for test of assignment {testCtx.assignment.id} ({testRes.testFile})'
            printWithTitle(title, testRes.testOutput)
            debug(testRes)
    if ecode is not None:
        sys.exit(ecode)
    match ctx.compileStatus:
        case 'FAIL':
            sys.exit(1)
        case 'OK_BUT_SOME_MISSING':
            sys.exit(OK_WITH_WARNINGS_EXIT_CODE)
        case 'OK':
            if notOkTotal > 0 or hasErrors:
                sys.exit(OK_WITH_WARNINGS_EXIT_CODE)
            else:
                sys.exit(0)

def abortIfTestOkRequired(assignment: Assignment, result: TestResult, ctx: CheckCtx):
    if assignment.testOkRequired and not result.isSuccess:
        print(f'Test for assignment {assignment.id} is required to succeed but failed!')
        print()
        print(result.testOutput)
        print()
        print('Aborting')
        outputResultsAndExit(ctx, ecode=1)

def checkScript(assignment: Assignment, ctx: TestContext, sheetDir: str, checkCtx: CheckCtx):
    script = assignment.testScript
    if not script:
        return
    scriptPath = pjoin(sheetDir, script)
    if not isFile(scriptPath):
        abort(f'Script {scriptPath} does not exist')
    debug(f'Running {scriptPath}')
    scriptResult = run(scriptPath, onError='ignore', stderrToStdout=True, captureStdout=True)
    numErrors = 0 if (scriptResult.exitcode == 0) else 1
    testResult = TestResult(script, scriptResult.stdout, False, totalTests=1, testFailures=numErrors)
    ctx.results.append(testResult)
    abortIfTestOkRequired(assignment, testResult, checkCtx)
