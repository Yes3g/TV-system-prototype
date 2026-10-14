"""Run all delivered checks and capture evidence outside the application data."""
import os
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parent.parent
output=Path(os.environ.get('NETVISION_TEST_ARTIFACTS',ROOT/'test-results')).resolve()
output.mkdir(parents=True,exist_ok=True)
commands=[('python-tests',[sys.executable,'-m','unittest','discover','-s','tests','-v']),
          ('javascript-regression',[os.environ.get('NODE','node'),'tests/regression.cjs']),
          ('browser-tests',[sys.executable,'-m','tests.run_browser'])]
for name,cmd in commands:
    result=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
    (output/(name+'.log')).write_text(result.stdout+'\n'+result.stderr)
    print(name, 'PASS' if result.returncode==0 else 'FAIL',flush=True)
    if result.returncode:
        print(result.stdout+'\n'+result.stderr)
        raise SystemExit(result.returncode)
