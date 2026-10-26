/* Authored expected x64 SDK layout, not measured until approved execution.
 * No Job Object/process/clock calls. Output contains SDK layout integers only. */
#include <Windows.h>
#include <stddef.h>
#include <stdio.h>

static int failed = 0;

static void layout(const char *name, size_t actual, size_t expected)
{
    printf("%s=%zu expected=%zu\n", name, actual, expected);
    if (actual != expected) failed = 1;
}

#define SIZE(type, expected) layout("sizeof." #type, sizeof(type), expected)
#define ALIGN(type, expected) layout("alignof." #type, _Alignof(type), expected)
#define OFFSET(type, member, expected) \
    layout("offsetof." #type "." #member, offsetof(type, member), expected)

int main(void)
{
    SIZE(void *, 8); SIZE(HANDLE, 8); SIZE(SIZE_T, 8); SIZE(ULONG_PTR, 8);
    SIZE(DWORD, 4); SIZE(BOOL, 4); SIZE(LARGE_INTEGER, 8);
    SIZE(JOBOBJECT_BASIC_ACCOUNTING_INFORMATION, 48);
    SIZE(JOBOBJECT_BASIC_LIMIT_INFORMATION, 64);
    SIZE(JOBOBJECT_EXTENDED_LIMIT_INFORMATION, 144);
    SIZE(STARTUPINFOW, 104); SIZE(STARTUPINFOEXW, 112); SIZE(PROCESS_INFORMATION, 24);
    ALIGN(JOBOBJECT_BASIC_ACCOUNTING_INFORMATION, 8);
    ALIGN(JOBOBJECT_BASIC_LIMIT_INFORMATION, 8);
    ALIGN(JOBOBJECT_EXTENDED_LIMIT_INFORMATION, 8);
    ALIGN(STARTUPINFOW, 8); ALIGN(STARTUPINFOEXW, 8); ALIGN(PROCESS_INFORMATION, 8);
    OFFSET(JOBOBJECT_BASIC_ACCOUNTING_INFORMATION, TotalUserTime, 0);
    OFFSET(JOBOBJECT_BASIC_ACCOUNTING_INFORMATION, TotalKernelTime, 8);
    OFFSET(JOBOBJECT_BASIC_ACCOUNTING_INFORMATION, TotalPageFaultCount, 32);
    OFFSET(JOBOBJECT_BASIC_ACCOUNTING_INFORMATION, TotalProcesses, 36);
    OFFSET(JOBOBJECT_BASIC_ACCOUNTING_INFORMATION, ActiveProcesses, 40);
    OFFSET(JOBOBJECT_BASIC_ACCOUNTING_INFORMATION, TotalTerminatedProcesses, 44);
    OFFSET(JOBOBJECT_BASIC_LIMIT_INFORMATION, PerProcessUserTimeLimit, 0);
    OFFSET(JOBOBJECT_BASIC_LIMIT_INFORMATION, PerJobUserTimeLimit, 8);
    OFFSET(JOBOBJECT_BASIC_LIMIT_INFORMATION, LimitFlags, 16);
    OFFSET(JOBOBJECT_BASIC_LIMIT_INFORMATION, MinimumWorkingSetSize, 24);
    OFFSET(JOBOBJECT_BASIC_LIMIT_INFORMATION, MaximumWorkingSetSize, 32);
    OFFSET(JOBOBJECT_BASIC_LIMIT_INFORMATION, ActiveProcessLimit, 40);
    OFFSET(JOBOBJECT_BASIC_LIMIT_INFORMATION, Affinity, 48);
    OFFSET(JOBOBJECT_EXTENDED_LIMIT_INFORMATION, BasicLimitInformation, 0);
    OFFSET(JOBOBJECT_EXTENDED_LIMIT_INFORMATION, IoInfo, 64);
    OFFSET(JOBOBJECT_EXTENDED_LIMIT_INFORMATION, ProcessMemoryLimit, 112);
    OFFSET(JOBOBJECT_EXTENDED_LIMIT_INFORMATION, JobMemoryLimit, 120);
    OFFSET(STARTUPINFOW, cb, 0); OFFSET(STARTUPINFOW, dwFlags, 60);
    OFFSET(STARTUPINFOW, hStdInput, 80); OFFSET(STARTUPINFOW, hStdOutput, 88);
    OFFSET(STARTUPINFOW, hStdError, 96);
    OFFSET(STARTUPINFOEXW, StartupInfo, 0);
    OFFSET(STARTUPINFOEXW, lpAttributeList, 104);
    OFFSET(PROCESS_INFORMATION, hProcess, 0); OFFSET(PROCESS_INFORMATION, hThread, 8);
    OFFSET(PROCESS_INFORMATION, dwProcessId, 16); OFFSET(PROCESS_INFORMATION, dwThreadId, 20);
    return failed;
}
