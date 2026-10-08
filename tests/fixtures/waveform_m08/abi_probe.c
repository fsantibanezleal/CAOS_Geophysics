/* Bounded selected-SDK layout probe; no Job/launch/query/kill or permissions.
   Newly compiled output must be reviewed before this executable is run. */
#include <Windows.h>
#include <Psapi.h>
#include <stddef.h>
#include <stdio.h>

typedef struct M08_PID_LIST {
    DWORD NumberOfAssignedProcesses;
    DWORD NumberOfProcessIdsInList;
    ULONG_PTR ProcessIdList[2];
} M08_PID_LIST;

typedef BOOL (WINAPI *M08_ENUM)(HANDLE, HMODULE *, DWORD, LPDWORD);
typedef DWORD (WINAPI *M08_NAME)(HANDLE, HMODULE, LPWSTR, DWORD);
typedef BOOL (WINAPI *M08_MEMORY)(LPMEMORYSTATUSEX);
_Static_assert(_Generic(&K32EnumProcessModules, M08_ENUM: 1, default: 0), "K32EnumProcessModules signature");
_Static_assert(_Generic(&K32GetModuleFileNameExW, M08_NAME: 1, default: 0), "K32GetModuleFileNameExW signature");
_Static_assert(_Generic(&GlobalMemoryStatusEx, M08_MEMORY: 1, default: 0), "GlobalMemoryStatusEx signature");
_Static_assert(offsetof(JOBOBJECT_BASIC_PROCESS_ID_LIST, ProcessIdList) == offsetof(M08_PID_LIST, ProcessIdList), "PID prefix");
_Static_assert(sizeof(JOBOBJECT_BASIC_PROCESS_ID_LIST) == 16, "SDK one-element PID list");
_Static_assert(sizeof(void *) == 8, "x64 only");

static void value(const char *name, size_t measured) {
    (void)printf("%s=%llu\n", name, (unsigned long long)measured);
}

int main(void) {
    value("HANDLE.size", sizeof(HANDLE));
    value("SIZE_T.size", sizeof(SIZE_T));
    value("BOOL.size", sizeof(BOOL));
    value("DWORD.size", sizeof(DWORD));
    value("MEMORY_STATUS.size", sizeof(MEMORYSTATUSEX));
    value("MEMORY_STATUS.align", _Alignof(MEMORYSTATUSEX));
    value("MEMORY_STATUS.length", offsetof(MEMORYSTATUSEX, dwLength));
    value("MEMORY_STATUS.load", offsetof(MEMORYSTATUSEX, dwMemoryLoad));
    value("MEMORY_STATUS.total_physical", offsetof(MEMORYSTATUSEX, ullTotalPhys));
    value("MEMORY_STATUS.available_physical", offsetof(MEMORYSTATUSEX, ullAvailPhys));
    value("MEMORY_STATUS.total_commit", offsetof(MEMORYSTATUSEX, ullTotalPageFile));
    value("MEMORY_STATUS.available_commit", offsetof(MEMORYSTATUSEX, ullAvailPageFile));
    value("MEMORY_STATUS.total_virtual", offsetof(MEMORYSTATUSEX, ullTotalVirtual));
    value("MEMORY_STATUS.available_virtual", offsetof(MEMORYSTATUSEX, ullAvailVirtual));
    value("MEMORY_STATUS.reserved", offsetof(MEMORYSTATUSEX, ullAvailExtendedVirtual));
    value("FILETIME.size", sizeof(FILETIME));
    value("FILETIME.align", _Alignof(FILETIME));
    value("FILETIME.low", offsetof(FILETIME, dwLowDateTime));
    value("FILETIME.high", offsetof(FILETIME, dwHighDateTime));
    value("SECURITY.size", sizeof(SECURITY_ATTRIBUTES));
    value("SECURITY.align", _Alignof(SECURITY_ATTRIBUTES));
    value("SECURITY.length", offsetof(SECURITY_ATTRIBUTES, nLength));
    value("SECURITY.descriptor", offsetof(SECURITY_ATTRIBUTES, lpSecurityDescriptor));
    value("SECURITY.inherit", offsetof(SECURITY_ATTRIBUTES, bInheritHandle));
    value("BASIC_LIMIT.size", sizeof(JOBOBJECT_BASIC_LIMIT_INFORMATION));
    value("BASIC_LIMIT.align", _Alignof(JOBOBJECT_BASIC_LIMIT_INFORMATION));
    value("BASIC_LIMIT.process_user", offsetof(JOBOBJECT_BASIC_LIMIT_INFORMATION, PerProcessUserTimeLimit));
    value("BASIC_LIMIT.job_user", offsetof(JOBOBJECT_BASIC_LIMIT_INFORMATION, PerJobUserTimeLimit));
    value("BASIC_LIMIT.flags", offsetof(JOBOBJECT_BASIC_LIMIT_INFORMATION, LimitFlags));
    value("BASIC_LIMIT.min_ws", offsetof(JOBOBJECT_BASIC_LIMIT_INFORMATION, MinimumWorkingSetSize));
    value("BASIC_LIMIT.max_ws", offsetof(JOBOBJECT_BASIC_LIMIT_INFORMATION, MaximumWorkingSetSize));
    value("BASIC_LIMIT.active", offsetof(JOBOBJECT_BASIC_LIMIT_INFORMATION, ActiveProcessLimit));
    value("BASIC_LIMIT.affinity", offsetof(JOBOBJECT_BASIC_LIMIT_INFORMATION, Affinity));
    value("BASIC_LIMIT.priority", offsetof(JOBOBJECT_BASIC_LIMIT_INFORMATION, PriorityClass));
    value("BASIC_LIMIT.scheduling", offsetof(JOBOBJECT_BASIC_LIMIT_INFORMATION, SchedulingClass));
    value("ACCOUNT.size", sizeof(JOBOBJECT_BASIC_ACCOUNTING_INFORMATION));
    value("ACCOUNT.align", _Alignof(JOBOBJECT_BASIC_ACCOUNTING_INFORMATION));
    value("ACCOUNT.user", offsetof(JOBOBJECT_BASIC_ACCOUNTING_INFORMATION, TotalUserTime));
    value("ACCOUNT.kernel", offsetof(JOBOBJECT_BASIC_ACCOUNTING_INFORMATION, TotalKernelTime));
    value("ACCOUNT.period_user", offsetof(JOBOBJECT_BASIC_ACCOUNTING_INFORMATION, ThisPeriodTotalUserTime));
    value("ACCOUNT.period_kernel", offsetof(JOBOBJECT_BASIC_ACCOUNTING_INFORMATION, ThisPeriodTotalKernelTime));
    value("ACCOUNT.faults", offsetof(JOBOBJECT_BASIC_ACCOUNTING_INFORMATION, TotalPageFaultCount));
    value("ACCOUNT.total", offsetof(JOBOBJECT_BASIC_ACCOUNTING_INFORMATION, TotalProcesses));
    value("ACCOUNT.active", offsetof(JOBOBJECT_BASIC_ACCOUNTING_INFORMATION, ActiveProcesses));
    value("ACCOUNT.terminated", offsetof(JOBOBJECT_BASIC_ACCOUNTING_INFORMATION, TotalTerminatedProcesses));
    value("IO_COUNTERS.size", sizeof(IO_COUNTERS));
    value("IO_COUNTERS.align", _Alignof(IO_COUNTERS));
    value("IO_COUNTERS.read_ops", offsetof(IO_COUNTERS, ReadOperationCount));
    value("IO_COUNTERS.write_ops", offsetof(IO_COUNTERS, WriteOperationCount));
    value("IO_COUNTERS.other_ops", offsetof(IO_COUNTERS, OtherOperationCount));
    value("IO_COUNTERS.read_bytes", offsetof(IO_COUNTERS, ReadTransferCount));
    value("IO_COUNTERS.write_bytes", offsetof(IO_COUNTERS, WriteTransferCount));
    value("IO_COUNTERS.other_bytes", offsetof(IO_COUNTERS, OtherTransferCount));
    value("EXTENDED.size", sizeof(JOBOBJECT_EXTENDED_LIMIT_INFORMATION));
    value("EXTENDED.align", _Alignof(JOBOBJECT_EXTENDED_LIMIT_INFORMATION));
    value("EXTENDED.basic", offsetof(JOBOBJECT_EXTENDED_LIMIT_INFORMATION, BasicLimitInformation));
    value("EXTENDED.io", offsetof(JOBOBJECT_EXTENDED_LIMIT_INFORMATION, IoInfo));
    value("EXTENDED.process_memory", offsetof(JOBOBJECT_EXTENDED_LIMIT_INFORMATION, ProcessMemoryLimit));
    value("EXTENDED.job_memory", offsetof(JOBOBJECT_EXTENDED_LIMIT_INFORMATION, JobMemoryLimit));
    value("EXTENDED.peak_process", offsetof(JOBOBJECT_EXTENDED_LIMIT_INFORMATION, PeakProcessMemoryUsed));
    value("EXTENDED.peak_job", offsetof(JOBOBJECT_EXTENDED_LIMIT_INFORMATION, PeakJobMemoryUsed));
    value("STARTUP.size", sizeof(STARTUPINFOW));
    value("STARTUP.align", _Alignof(STARTUPINFOW));
    value("STARTUP.cb", offsetof(STARTUPINFOW, cb));
    value("STARTUP.reserved", offsetof(STARTUPINFOW, lpReserved));
    value("STARTUP.desktop", offsetof(STARTUPINFOW, lpDesktop));
    value("STARTUP.title", offsetof(STARTUPINFOW, lpTitle));
    value("STARTUP.x", offsetof(STARTUPINFOW, dwX));
    value("STARTUP.y", offsetof(STARTUPINFOW, dwY));
    value("STARTUP.x_size", offsetof(STARTUPINFOW, dwXSize));
    value("STARTUP.y_size", offsetof(STARTUPINFOW, dwYSize));
    value("STARTUP.x_chars", offsetof(STARTUPINFOW, dwXCountChars));
    value("STARTUP.y_chars", offsetof(STARTUPINFOW, dwYCountChars));
    value("STARTUP.fill", offsetof(STARTUPINFOW, dwFillAttribute));
    value("STARTUP.flags", offsetof(STARTUPINFOW, dwFlags));
    value("STARTUP.show", offsetof(STARTUPINFOW, wShowWindow));
    value("STARTUP.reserved_bytes", offsetof(STARTUPINFOW, cbReserved2));
    value("STARTUP.reserved_ptr", offsetof(STARTUPINFOW, lpReserved2));
    value("STARTUP.stdin", offsetof(STARTUPINFOW, hStdInput));
    value("STARTUP.stdout", offsetof(STARTUPINFOW, hStdOutput));
    value("STARTUP.stderr", offsetof(STARTUPINFOW, hStdError));
    value("STARTUP_EX.size", sizeof(STARTUPINFOEXW));
    value("STARTUP_EX.align", _Alignof(STARTUPINFOEXW));
    value("STARTUP_EX.startup", offsetof(STARTUPINFOEXW, StartupInfo));
    value("STARTUP_EX.attributes", offsetof(STARTUPINFOEXW, lpAttributeList));
    value("PROCESS.size", sizeof(PROCESS_INFORMATION));
    value("PROCESS.align", _Alignof(PROCESS_INFORMATION));
    value("PROCESS.process", offsetof(PROCESS_INFORMATION, hProcess));
    value("PROCESS.thread", offsetof(PROCESS_INFORMATION, hThread));
    value("PROCESS.pid", offsetof(PROCESS_INFORMATION, dwProcessId));
    value("PROCESS.tid", offsetof(PROCESS_INFORMATION, dwThreadId));
    value("PID_LIST.size", sizeof(M08_PID_LIST));
    value("PID_LIST.align", _Alignof(M08_PID_LIST));
    value("PID_LIST.assigned", offsetof(M08_PID_LIST, NumberOfAssignedProcesses));
    value("PID_LIST.count", offsetof(M08_PID_LIST, NumberOfProcessIdsInList));
    value("PID_LIST.ids", offsetof(M08_PID_LIST, ProcessIdList));
    return ferror(stdout) ? 1 : 0;
}
