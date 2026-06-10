from utils import *
from common import *
import python
import haskell
import java
import llm_tutor
import argparse
import re
import traceback
import io

defaultGradleBuildFile = pjoin(os.path.realpath(os.path.dirname(__file__)), 'build.gradle.kts')
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, line_buffering=True)

def parseArgs():
    parser = argparse.ArgumentParser(description='Checker for assignments')
    parser.add_argument('--submission-dir', metavar='DIR', type=str,
                        help='Directories with student submission')
    parser.add_argument('--test-dir', metavar='DIR', type=str,
                        help='Directories with tests and the exercise.yaml')
    parser.add_argument('--result-file', metavar='FILE', type=str,
                        help='File where test results are stored as a pickled python dict.\n' +
                            'See TestCtx.asDict for the format of the dict.')
    parser.add_argument("--config-dir", metavar='DIR', type=str, 
                        help="Directory with API key needed for llm-tutor")
    subparsers = parser.add_subparsers(help='Commands', dest='cmd')
    parser.add_argument('--debug', help='Enable debug output',
                         action='store_true', default=False)
    py = subparsers.add_parser('python', help='Check python assignment')
    py.add_argument('--wypp', metavar='DIR', type=str, help='Path to wypp')
    py.add_argument('--sheet', metavar='X', type=str, help='Identifier for sheet')
    py.add_argument('--assignment', metavar='X', type=str,
                    help='Identifier for assignment(s), multiple assignments separated by commas')
    hs = subparsers.add_parser('haskell', help='Check haskell assignment')
    hs.add_argument('--sheet', metavar='X', type=str, help='Identifier for sheet')
    java = subparsers.add_parser('java', help='Check Java assignment')
    java.add_argument('--sheet', metavar='X', type=str, help='Identifier for sheet')
    java.add_argument('--checkstyle', metavar='JAR', type=str,
                        help='Path to the CheckStyle JAR file',
                        default='/opt/praktomat-addons/checkstyle.jar')
    java.add_argument('--build-gradle', metavar='FILE', type=str,
                        help=f'Path to the build.gradle.kts file',
                        default=defaultGradleBuildFile)
    java.add_argument('--no-checkstyle', action='store_true', default=False,
                      help='Do not run checkstyle over the submissions')
    java.add_argument('--gradle-online', action='store_true', default=False,
                      help='Use gradle in online mode, default is offline')
    java.add_argument('--assignment', metavar='X', type=str,
                      help='Identifier for assignment(s), multiple assignments separated by commas')
    
    llm = subparsers.add_parser('llm-tutor', help='Run LLM tutor feedback check')
    llm.add_argument('--llm-tutor-dir', metavar='DIR', type=str, help='Path to llm-tutor-dir')
    llm.add_argument('--solution-dir', metavar='DIR', type=str,
                        help='Directories with sample solution')
    llm.add_argument('--pdf-dir', metavar='DIR', type=str,
                        help='Directories with assignment pdfs')
    llm.add_argument('--sheet', metavar='X', type=str, help='Identifier for sheet')
    llm.add_argument('--fake-llm', action= 'store_true',default=False, 
                     help='used just to test the system')

    (known, other) = parser.parse_known_args()
    if '--debug' in other:
        known.debug = True
    if other:
       print(f'WARNING: ignoring unknown commandline arguments: {other}')
    return known

# "Labortest 2, Gruppe A" -> ["labortest_2", labortest_2_gruppe_a"]
def candsFromTitle(origTitle: str) -> list[str]:
    comps = []
    for x in origTitle.split(','):
        x = x.strip()
        x = replaceAll(["/", "\\", " ", "\t"], "_", x)
        x = x.lower()
        comps.append(x)
    cands = []
    for i in range(len(comps)):
        c = "_".join(comps[:i+1])
        cands.append(c)
    cands.reverse()
    return cands

_numRe = re.compile(r'\b\d+\b')
def getSheetFromEnv(testDir: str) -> Optional[str]:
    task_id = os.environ.get('TASK_ID_CUSTOM')
    if task_id is not None and task_id != '':
        return task_id
    taskTitle = os.environ.get('TASK_TITLE')
    if taskTitle is None:
        return None
    origTitle = taskTitle.strip()
    cands = candsFromTitle(origTitle)
    if cands:
        return None
    m = _numRe.search(origTitle)
    if m:
        cands.append(m.group(0).zfill(2))
    for c in cands: # first search for the more specific
        d = getSheetDir(testDir, c)
        if isDir(d):
            return c
    return cands[-1]  # prefer the more generic

def getAssignments(s: str|None) -> list[str] | None:
    assignments = None
    if s:
        l = []
        for x in s.split(','):
            x = x.strip()
            if x:
                l.append(x)
        if l:
            assignments = l
    return assignments

def main():
    args = parseArgs()
    if args.debug:
        enableDebug()
    cmd = args.cmd
    if not cmd:
        abort('command not given on commandline')
    testDir = args.test_dir
    if testDir is not None:
        testDir = abspath(testDir)
    submissionDir = args.submission_dir or '.'
    submissionDir = submissionDir.rstrip('/')
    submissionDir = abspath(submissionDir)
    resultFile = args.result_file
    debug(f'Running checks with args={args}')
    if isDebug():
        print('Current user: ', end='')
        run('whoami')
        print('Ulimits:')
        run('ulimit -a')
        print('Environment:')
        run('env')
        print('Block size: ', end='')
        run('stat -fc %s .', onError='ignore')
    if cmd == 'python':
        wypp = args.wypp
        if not wypp:
            wypp = '/wypp'
        sheet = args.sheet
        if not sheet:
            if testDir is None:
                raise ValueError("testDir is required")
            sheet = getSheetFromEnv(testDir)
        assignments = getAssignments(args.assignment)
        opts = python.PythonOptions(submissionDir, testDir, resultFile, sheet, assignments, wypp)
        debug(f'Running python checks, options: {opts}')
        python.check(opts)
    elif cmd == 'haskell':
        sheet = args.sheet
        if not sheet:
            if testDir is None:
                raise ValueError("testDir is required")
            sheet = getSheetFromEnv(testDir)
        opts = haskell.HaskellOptions(submissionDir, testDir, resultFile, sheet)
        debug(f'Running haskell checks, options: {opts}')
        haskell.check(opts)
    elif cmd == 'java':
        sheet = args.sheet
        if not sheet:
            if testDir is None:
                raise ValueError("testDir is required")
            sheet = getSheetFromEnv(testDir)
        offline = not args.gradle_online
        assignments = getAssignments(args.assignment)
        opts = java.JavaOptions(
            sourceDir=submissionDir,
            testDir=testDir,
            resultFile=resultFile,
            sheet=sheet,
            runCheckstyle=not args.no_checkstyle,
            checkstylePath=args.checkstyle,
            gradleBuildFile=args.build_gradle,
            gradleOffline=offline,
            assignments=assignments)
        debug(f'Running Java checks, options: {opts}')
        java.check(opts)
    elif cmd == 'llm-tutor':
        sheet = args.sheet
        if not sheet:
            if testDir is None:
                raise ValueError("testDir is required")
            sheet = getSheetFromEnv(testDir)

        if not args.llm_tutor_dir:
            llm_tutor_dir = '/llm-tutor'
        else:
            llm_tutor_dir = args.llm_tutor_dir
            
        # sheet optional; für deinen Durchstoß nicht nötig
        opts = llm_tutor.LlmTutorOptions(
            llm_tutor_dir = llm_tutor_dir,
            solution_dir= args.solution_dir,
            pdf_dir= args.pdf_dir,
            fakeLlm= args.fake_llm,
            sheet=sheet,
            sourceDir=submissionDir,
            testDir=testDir,
            resultFile=resultFile,
            configApi = args.config_dir
          
        )
        debug(f'Running LLM tutor checks, options: {opts}')
        llm_tutor.check(opts)
    else:
        bug(f'invalid kind: {cmd}')

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(traceback.format_exc())
        bug('checker raised an unexpected exception, this is a bug!')

