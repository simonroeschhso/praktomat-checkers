import sys
from typing import *
from shell import *
import codecs

def bug(msg: str) -> NoReturn:
    print('INTERNAL ERROR: ' + msg)
    sys.exit(1)

def abort(msg: str) -> NoReturn:
    print('FEHLER: ' + msg)
    sys.exit(1)

def readFile(name):
    with open(name, 'r', encoding='utf-8') as f:
        return f.read()

def asList(x: Any) -> list:
    if type(x) == list:
        return x
    if type(x) == tuple:
        return list(x)
    else:
        return [x]

# Adapted from https://github.com/skogsbaer/check-assignments/blob/main/src/fixEncodingCmd.py
# Characters to replace
replacements = ['ä', 'ö', 'ü', 'Ä', 'Ö', 'Ü', 'ß']
# Byte order marks
boms = {codecs.BOM_UTF8: 'utf_8',
        codecs.BOM_UTF16_LE: 'utf_16_le',
        codecs.BOM_UTF16_BE: 'utf_16_be',
        codecs.BOM_UTF32_LE: 'utf_32_le',
        codecs.BOM_UTF32_BE: 'utf_32_be'}
def fixEncoding(path):
    bytes_orig = open(path, 'rb').read()
    bytes = bytes_orig
    for b, enc in boms.items():
        if b == bytes[:len(b)]:
            bytes = bytes[len(b):]
            bytes = bytes.decode(enc).encode('utf_8')
            break
    else:
        # no BOM
        for r in replacements:
            bytes = bytes.replace(r.encode('iso-8859-1'), r.encode('utf-8'))
    if bytes != bytes_orig:
        open(path, 'wb').write(bytes)
        print(f'Fixed encoding of {path}')

def fixEncodingRecursively(startDir: str, ext: str):
    files = run(f"find '{startDir}' -type f -name '*.{ext}'", captureStdout=splitLines).stdout
    for p in files:
        fixEncoding(p)

def findFile(p: str, sourceDir: str, ignoreCase: bool=False) -> Optional[str]:
    cand = pjoin(sourceDir, p)
    if isFile(cand):
        return cand
    if ignoreCase:
        for x in ls(sourceDir):
            if basename(x).lower() == p.lower() and isFile(x):
                return x
    return None

def removeLeading(full: str, leading: str):
    if full.startswith(leading):
        return full[len(leading)+1:]
    else:
        return full

_DEBUG = False

def enableDebug():
    global _DEBUG
    _DEBUG = True

def isDebug():
    return _DEBUG

def debug(msg):
    if _DEBUG:
        print(f'[DEBUG] {msg}')

def findSolutionDirAux(root: str, stopCondition: Optional[Callable], isSolutionRoot: bool) -> Optional[str]:
    if isFile(root):
        return None
    if isNotAWrapperDir(root, isSolutionRoot):
        return root
    if stopCondition is not None and stopCondition(root):
        return root
    for x in ls(root):
        result = findSolutionDirAux(x, stopCondition, False)
        if result is not None:
            return result
    return None

def isNotAWrapperDir(directory: str, isSolutionRoot: bool) -> bool:
    pathnames = ls(directory, '[!.]*')
    if len(pathnames) == 2 and isSolutionRoot:
        # Filter out the script that starts the multi checker
        pathnames = list(filter(lambda x: not (basename(x).startswith('check') and x.endswith('.sh')), pathnames))
    if len(pathnames) > 1:
        return True
    if len(pathnames) == 0:
        return False
    return not isDir(pathnames[0])

def findSolutionDir(root: str, stopCondition: Optional[Callable]=None) -> str:
    """
    Finds the possibly nested solution directory in the given root directory.
    A stop condition can be passed that returns True when a directory name is
    supplied that meets the criteria of being the top-level solution directory.
    Additionally, the search is not going to descend further if a directory
    is not just wrapping another directory. If no matching directory is found,
    the given root directory will be returned.
    """
    result = findSolutionDirAux(root, stopCondition, True)
    if result is not None:
        return result
    else:
        # Nothing was found
        # Default to the given directory
        return root

def withLimitedDir(sourceDir, subdirs, action):
    with tempDir(suffix=basename(sourceDir), delete=False) as tmp:
        for sub in subdirs:
            target = pjoin(tmp, sub)
            mkdir(target, createParents=True)
            shutil.copytree(pjoin(sourceDir, sub), target, dirs_exist_ok=True)
        action(tmp)
