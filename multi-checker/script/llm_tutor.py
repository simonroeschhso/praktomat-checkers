from dataclasses import dataclass
from typing import Optional
import os, sys, shlex

import yaml  # pip install pyyaml
from shell import *
from utils import *
from common import *
from config import *
from exercise import parseExercise


def configError(s):
    abort('Config error: ' + s)

@dataclass
class LlmTutorOptions(Options):
    llm_tutor_dir: str
    solution_dir: str
    pdf_dir: str
    fakeLlm: bool
    configApi: str
    sheet: Optional[str] = None
   
   
# alle strings sind als pfad hier weitergegeben
def runLlmTutor (llmTutorPfad: str, fake_llm: bool, id: str, sampleSolution: str, studentSolution: str, pdf_task:str , configApi:str):
    args = ['python3', llmTutorPfad + '/src/praktomat_entry.py']

    args = args + [
            "--pdf", pdf_task,
            "--model-solution", sampleSolution,
            "--student-solution", studentSolution,
            "--assignment", id,
            "--api", configApi
    ]

    if fake_llm:
            print("Dummy Result: \n")
            print(args , "\n")
            return 
    else:
        print("llmTutorPfad =", llmTutorPfad)
        print("args =", args)
        res = run(args, onError='ignore', stderrToStdout=True, captureStdout=True)
        print(res.stdout)

        if res.exitcode != 0:
            raise RuntimeError('LLM-tutor failed')
    
    

def check(opts: LlmTutorOptions):
    # test dir, pfad zum exercise.yaml (mount a dir tests/llm-tutor > externel)
    exTest_dir = getSheetDir(opts.testDir, opts.sheet)
    exYaml = pjoin(exTest_dir, 'exercise.yaml')
    if isFile(exYaml):
        ex = parseExercise(opts.sheet, exYaml)
    else:
        ex = None

    if ex is not None:
        for assignemnt in ex.assignments:
             
            # pfad zu Musterlösung (mount a dir > tests/llm-tutor/sampleSolution > solution)
            if not assignemnt.tests:
                configError(f'No test file defined for assignment {assignemnt.id}')
            exSampleSolution_pfad = pjoin(getSolutionDir(opts.solution_dir), assignemnt.tests[0])


            # aufgabe pfad extrahieren
            if not assignemnt.extraFiles:
                configError(f'No extra file defined for assignment {assignemnt.id}')
            pdf = pjoin(getPdfDir(opts.pdf_dir), assignemnt.extraFiles[0])

            # student Solution
            print("opts.sourceDir =", opts.sourceDir)
            # nestedSourceDir = findSolutionDir(opts.sourceDir)
            student_pfad = pjoin (opts.sourceDir, assignemnt.src)

            #api 
            api = parseConfig(pjoin(opts.configApi, 'api.yaml'))

            # Result von Sprachmodell
            runLlmTutor(llmTutorPfad=opts.llm_tutor_dir,
                            fake_llm= opts.fakeLlm, 
                            id= assignemnt.id,
                            sampleSolution= exSampleSolution_pfad, 
                            studentSolution= student_pfad,
                            pdf_task= pdf, 
                            configApi = api.llmTutorConfig.apikey)

