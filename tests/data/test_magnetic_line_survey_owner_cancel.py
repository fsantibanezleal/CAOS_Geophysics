"""Owner marker custody plus actual native workload termination and drain."""
import os
from pathlib import Path
import sys
import threading
import time

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'data-pipeline'))
sys.path.insert(0,str(Path(__file__).parent))
import magnetic_line_survey as core
import magnetic_line_survey_runtime as runtime
from test_magnetic_line_survey_runtime import probe_plan


def test_fixed_cancel_marker_refuses_malformed_and_alias(tmp_path):
    assert not runtime.cancellation_requested(tmp_path)
    marker=tmp_path/'cancel.request'
    for payload in (b'',b'cancel',runtime.CANCEL_BYTES+b'x'):
        marker.write_bytes(payload)
        with pytest.raises(core.SurveyError):
            runtime.cancellation_requested(tmp_path)
    marker.write_bytes(runtime.CANCEL_BYTES)
    assert runtime.cancellation_requested(tmp_path)
    os.link(marker,tmp_path/'alias')
    with pytest.raises(core.SurveyError):
        runtime.cancellation_requested(tmp_path)


def test_actual_owner_cancel_on_native_workload(tmp_path):
    path=probe_plan(tmp_path,rows=8201,sources=66,mode='cancel')
    done=threading.Event()
    written=[]
    def monitor():
        deadline=time.monotonic()+120
        while not done.wait(.05) and time.monotonic()<deadline:
            if (path.parent/'native-ready.json').is_file():
                runtime.request_cancellation(path.parent)
                written.append(True)
                return
    thread=threading.Thread(target=monitor)
    thread.start()
    try:
        receipt=runtime.run_worker(Path(sys.base_prefix)/'python.exe',
            Path(os.environ['GEOPHYSICS_EXISTING_PACKAGE_ROOT']),path.parent,path)
    finally:
        done.set()
        thread.join(2)
    assert written and not thread.is_alive()
    assert receipt['verdict']=='cancelled'
    assert receipt['active_processes']==0 and receipt['total_processes']==1
    assert receipt['stop_cpu_s']<=10 and receipt['stop_wall_s']<=10
    assert receipt['scratch_bytes']==runtime.owned_bytes(path.parent)
