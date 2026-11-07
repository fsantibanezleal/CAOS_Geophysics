"""Measured workflow budget; sampled enforcement, not an OS resource reservation."""
import ctypes
import os
from pathlib import Path
import threading
import time

import joint_survey_intake as intake
from joint_survey_serialization import _external


MAX_SECONDS=1800.
MAX_RSS=2*1024**3
MAX_SCRATCH=256*1024**2


class _WindowsCounters(ctypes.Structure):
    # One stable type. ctypes.POINTER caches its argument type globally; defining
    # a new Structure on EVERY sample leaks those classes in that cache.
    _fields_=[('cb',ctypes.c_ulong),('PageFaultCount',ctypes.c_ulong),
        ('PeakWorkingSetSize',ctypes.c_size_t),('WorkingSetSize',ctypes.c_size_t),
        ('QuotaPeakPagedPoolUsage',ctypes.c_size_t),('QuotaPagedPoolUsage',ctypes.c_size_t),
        ('QuotaPeakNonPagedPoolUsage',ctypes.c_size_t),('QuotaNonPagedPoolUsage',ctypes.c_size_t),
        ('PagefileUsage',ctypes.c_size_t),('PeakPagefileUsage',ctypes.c_size_t)]


if os.name=='nt':
    _kernel=ctypes.WinDLL('kernel32',use_last_error=True);_psapi=ctypes.WinDLL('psapi',use_last_error=True)
    _kernel.GetCurrentProcess.restype=ctypes.c_void_p
    _psapi.GetProcessMemoryInfo.argtypes=[ctypes.c_void_p,ctypes.POINTER(_WindowsCounters),ctypes.c_ulong]


def process_rss_bytes():
    if os.name=='nt':
        counters=_WindowsCounters();counters.cb=ctypes.sizeof(counters)
        if not _psapi.GetProcessMemoryInfo(_kernel.GetCurrentProcess(),ctypes.byref(counters),counters.cb):
            raise OSError(ctypes.get_last_error(),'actual process RSS unavailable')
        return int(counters.WorkingSetSize)
    # Linux deployment profile only. Do not substitute ru_maxrss as current RSS.
    with Path('/proc/self/statm').open('r',encoding='ascii') as stream: resident=int(stream.read().split()[1])
    return resident*os.sysconf('SC_PAGE_SIZE')


def scratch_bytes(root):
    total=0
    def walk(directory):
        nonlocal total
        intake._ordinary(directory,directory=True)
        with os.scandir(directory) as entries:
            for entry in entries:
                path=directory/entry.name
                info=path.lstat()
                if entry.is_dir(follow_symlinks=False): walk(path)
                else:
                    intake._ordinary(path);total+=info.st_size
    walk(root)
    return total


class JointResourceBudget:
    """One original absolute deadline shared by all fits and final export."""
    def __init__(self,scratch_root):
        self.root=_external(scratch_root,existing=True)
        self.started=time.monotonic();self.deadline=self.started+MAX_SECONDS
        self.peak_rss=0;self.peak_scratch=0;self.samples=0;self.failure=None;self._failure_exported=False
        self._stop=threading.Event();self._lock=threading.Lock();self._thread=None

    def _sample(self):
        rss=process_rss_bytes();disk=scratch_bytes(self.root);now=time.monotonic()
        with self._lock:
            self.samples+=1;self.peak_rss=max(self.peak_rss,rss);self.peak_scratch=max(self.peak_scratch,disk)
            if now>self.deadline: self.failure='workflow_deadline'
            elif rss>MAX_RSS: self.failure='workflow_rss'
            elif disk>MAX_SCRATCH: self.failure='workflow_scratch'

    def _monitor(self):
        while not self._stop.wait(.05):
            try: self._sample()
            except Exception as exc:
                with self._lock: self.failure='resource_measurement_'+type(exc).__name__

    def checkpoint(self):
        self._sample()
        with self._lock:
            if self.failure is not None: raise RuntimeError(self.failure)

    def __enter__(self):
        self.checkpoint();self._thread=threading.Thread(target=self._monitor,name='joint-resource-sampler',daemon=True)
        self._thread.start();return self

    def __exit__(self,exc_type,exc,tb):
        self._stop.set()
        if self._thread is not None: self._thread.join(timeout=2.)
        if exc_type is None and not self._failure_exported: self.checkpoint()

    def receipt(self,*,workflow_completed):
        self.checkpoint()
        return self._receipt(workflow_completed)

    def failure_receipt(self):
        """Already measured adverse state; no new scientific work or fake PASS."""
        self._failure_exported=True
        return self._receipt(False)

    def _receipt(self,workflow_completed):
        with self._lock:
            return {'schema':'joint-survey-resource-receipt-1','elapsed_seconds':time.monotonic()-self.started,
                'peak_sampled_rss_bytes':self.peak_rss,'peak_sampled_scratch_bytes':self.peak_scratch,
                'samples':self.samples,'sampling_seconds':.05,'deadline_seconds':MAX_SECONDS,
                'rss_limit_bytes':MAX_RSS,'scratch_limit_bytes':MAX_SCRATCH,
                'workflow_completed':workflow_completed,'complete_workflow_resource_pass':workflow_completed and self.failure is None,
                'os_reservation':False,'hard_realtime_interruption':False}
