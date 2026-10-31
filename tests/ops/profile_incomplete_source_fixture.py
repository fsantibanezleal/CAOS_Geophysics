"""Fixed trusted owner sources in external fixtures; never a default mount."""
from contextlib import contextmanager
import hashlib
import importlib.util
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SOURCE = '637f4aa873bf73187f1c88d452fd4bf49b2d61ee'
PINS = {
    'profile_linux_exec':'1b0d720f067a4e57ffe4b7f1b048205ccb9165e908d35b829f57efc1172711ed',
    'profile_linux_worker':'f4f6278289155b74d7bdbaf78c75d66556f321dd37023d782d8f020325d9e421',
    'profile_linux_recovery':'ad3fff15ef730f40c20209f5bf9226685f6db300af1a73bfa2c865ff6b4ce874',
    'profile_incomplete_recovery':'e8daa7d2c8fefee5f8de28ff279e49f90f37bef12d8f67366bf8a4d36098bbf6',
}


@contextmanager
def owner_source(output, monkeypatch):
    import app
    import app.projects  # Close the existing projects/worker import cycle first.
    assert output.is_absolute() and not output.exists()
    assert all(not (p/'.git').exists() for p in (output,*output.parents))
    bodies={}
    for name,digest in PINS.items():
        body=subprocess.check_output(['git','-C',str(ROOT),'show',SOURCE+':app/'+name+'.py'])
        assert hashlib.sha256(body).hexdigest()==digest,name
        bodies[name]=body
    output.mkdir()
    for name,body in bodies.items():
        target=output/(name+'.py')
        with target.open('xb') as stream: stream.write(body)
        assert hashlib.sha256(target.read_bytes()).hexdigest()==PINS[name]
        qualified='app.'+name
        spec=importlib.util.spec_from_file_location(qualified,target)
        module=importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules,qualified,module)
        monkeypatch.setattr(app,name,module,raising=False)
        spec.loader.exec_module(module)
    yield
