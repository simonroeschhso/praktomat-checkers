from testUtils import *

wyppDir = '/wypp/'

pythonTestDir = f'{praktomatTestsLocal}/python-prog1/'
python2TestDir = f'{praktomatTestsLocal}/python-prog2/'
localTestDir = f'{thisDir}/python-wypp'

def test_python01():
    expectOk(f'python3 {checkScript} {checkScriptArgs} python --wypp {wyppDir} --sheet 01 --assignment 1,4',
             submissionDir=localTestDir)

def test_python02():
    expectFail(f'python3 {checkScript} {checkScriptArgs} python --wypp {wyppDir} --sheet 01 --assignment 2',
               121, submissionDir=localTestDir)

def test_python03():
    expectFail(f'python3 {checkScript} {checkScriptArgs} python --wypp {wyppDir} --sheet 01 --assignment 2',
               121, submissionDir=localTestDir)

def test_python04():
    expectFail(f'python3 {checkScript} {checkScriptArgs} python --wypp {wyppDir} --sheet 01 --assignment 1,2',
               121, submissionDir=localTestDir)

def test_python05():
    expectFail(f'python3 {checkScript} {checkScriptArgs} python --wypp {wyppDir} --sheet 01 --assignment 3',
               1, submissionDir=localTestDir)

def test_python06():
    expectFail(f'python3 {checkScript} {checkScriptArgs} python --wypp {wyppDir} --sheet 01 --assignment 1,2,3',
               1, submissionDir=localTestDir)

def test_python07():
    pythonTests = [('solution-good', 0), ('solution-wrapped', 0), ('solution-partial', 121), ('solution-partial-missing', 121),
                ('solution-fail', 121), ('solution-error', 1), ('solution-with-own-test-errors', 121),
                ('solution-timeout', 1)]
    for d, ecode in pythonTests:
        print()
        print(d)
        sheetDirLocal = f'{praktomatCheckersLocal}/multi-checker/tests/python-wypp/03'
        submissionDir = f'{localTestDir}/03/{d}/'
        cmd = f'python3 {checkScript} {checkScriptArgs} python --wypp {wyppDir} --sheet 03'
        env = {'PRAKTOMAT_CHECKER_TEST_TIMEOUT': '2'}
        if ecode == 0:
            res = expectOk(cmd, external=sheetDirLocal, submissionDir=submissionDir, env=env)
        else:
            res = expectFail(cmd, ecode, external=sheetDirLocal, submissionDir=submissionDir, env=env)
        if d == 'solution-timeout':
            if 'timeout' not in res.stdout.lower():
                fail(f'expected timeout in output\n\n---\n{res.stdout}\n---')

def test_python08():
    expectOk(f'python3 {checkScript} {checkScriptArgs} python --wypp {wyppDir} --sheet 09',
        external=f'{pythonTestDir}/09', submissionDir=f'{pythonTestDir}/09/solution/')

def test_python09():
    expectOk(f'python3 {checkScript} {checkScriptArgs} python --wypp {wyppDir} --sheet labortest_2',
        external=f'{pythonTestDir}/labortest_2', submissionDir=f'{pythonTestDir}/labortest_2/solution/')

def test_python10():
    expectFail(f'python3 {checkScript} {checkScriptArgs} python --wypp {wyppDir} --sheet labortest_2',
        121, external=f'{pythonTestDir}/labortest_2', submissionDir=f'{pythonTestDir}/labortest_2/solution-partial/')

def test_python11():
    expectFail(f'python3 {checkScript} {checkScriptArgs} python --wypp {wyppDir} --sheet labortest_2',
        1, external=f'{pythonTestDir}/labortest_2', submissionDir=f'{pythonTestDir}/labortest_2/solution-nofiles/')

def test_python12():
    expectFail(f'python3 {checkScript} {checkScriptArgs} python --wypp {wyppDir} --sheet abschlussprojekt',
        external=f'{pythonTestDir}/abschlussprojekt', submissionDir=f'{pythonTestDir}abschlussprojekt/solution-fail')

def test_python13():
    expectFail(f'python3 {checkScript} {checkScriptArgs} python --wypp {wyppDir} --sheet abschlussprojekt',
        121, external=f'{pythonTestDir}/abschlussprojekt', submissionDir=f'{pythonTestDir}abschlussprojekt/solution-simple')

def test_python14():
    expectOk(f'python3 {checkScript} {checkScriptArgs} python --wypp {wyppDir} --sheet abschlussprojekt',
        external=f'{pythonTestDir}/abschlussprojekt', submissionDir=f'{pythonTestDir}abschlussprojekt/solution')

def test_python15():
    expectOk(f'python3 {checkScript} {checkScriptArgs} python --wypp {wyppDir} --sheet 10-dicts-exceptions',
        external=f'{pythonTestDir}/10-dicts-exceptions', submissionDir=f'{pythonTestDir}/solutions/10-dicts-exceptions')

def test_python16():
    expectOk(f'python3 {checkScript} {checkScriptArgs} python --wypp {wyppDir} --sheet 10-dicts-exceptions',
        external=f'{pythonTestDir}/10-dicts-exceptions', submissionDir=f'{pythonTestDir}/solutions/10-dicts-exceptions/subdir')

def test_python17():
    prog2Sheets = ['P01-intro', 'P02-higher-order-funs', 'P03-OO', 'P04-Listen', 'P05-Sorting',
                'P06-Sorting2', 'P07-Design-Patterns', 'P08-Trees', 'P09-Functional-Iterator',
                'P11-Threads', 'P12-Hashing']
    prog2SheetsIncomplete = ['P01-intro', 'P06-Sorting2']
    prog2Sheets = ['P06-Sorting2']
    for s in prog2Sheets:
        cmd = f'python3 {checkScript} {checkScriptArgs} python --wypp {wyppDir} --sheet {s}'
        external=f'{python2TestDir}/{s}'
        dir=f'{python2TestDir}{s}/solution'
        if s in prog2SheetsIncomplete:
            expectFail(cmd, external=external, submissionDir=dir, ecode=121)
        else:
            expectOk(cmd, external=external, submissionDir=dir)

