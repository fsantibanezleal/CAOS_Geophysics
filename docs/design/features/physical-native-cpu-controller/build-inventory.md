# I01 read-only Windows build inventory and separate execution review

Date: 2026-10-03. Status: INVENTORIED, compiler/linker/ABI/core tests NOT_RUN.
That status is the original pre-execution checkpoint. Subsequent actual I01
measurements are separately pinned in [the measured receipt](../../../validation/native-i01-abi-pure-20261004.json)
and [worker operations](worker-operations.md); no original inventory observation
or requested proposal is rewritten as native operation/admission proof.
This packet is the prerequisite requested by MAIN, not a build-execution grant.
Read [approval](approval.md), [contracts](contracts.md), [design](design.md),
[validation](validation-plan.md) and [review packet](review-packet.md).
Approval was persisted FIRST at914a4bbe3593f7b138b1c4cf829c434b1505edb7.
No new C/header/test/probe existed at that commit or at this inventory milestone.

## 1. Scope, exact tools and available bytes

MAIN FULL read the original seven-doc67c621c83a10cc6ec036463f6ef9be06c7ee42ac
and authorized only I01 core/test authoring plus optional new ABI probe. H06
compiler/linker/compiled-binary execution still needs a NEW exact MAIN decision.
H01/H02/H04/H05 are unaffected and CLOSED. Native platform launch/query/kill,
provisioning, application integration, environments and profile remain untouched.

Read-only metadata: PowerShell7.6.5, culture es-CL, 64-bit process;
Environment.OSVersion reports Microsoft Windows NT10.0.26300.0. That is an
observed version string, not an effective credential/security or OS feature probe.
Primary root inventory completed2026-10-03T15:56:49.2228942Z. Selected additional
static libraries/runtime files and bounded PE import directories were then read.
No cl.exe/link.exe/dumpbin/help/vcvars/installer or generated binary was invoked.

Aliases below resolve EXACTLY, no glob/latest/PATH lookup or alternative version:

```text
MSVC_ROOT = C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.43.34808
MSVC_BIN = MSVC_ROOT\bin\Hostx64\x64
MSVC_INCLUDE = MSVC_ROOT\include
MSVC_LIB = MSVC_ROOT\lib\x64
SDK_ROOT = C:\Program Files (x86)\Windows Kits\10
SDK_UCRT_INCLUDE = SDK_ROOT\Include\10.0.22621.0\ucrt
SDK_SHARED_INCLUDE = SDK_ROOT\Include\10.0.22621.0\shared
SDK_UM_INCLUDE = SDK_ROOT\Include\10.0.22621.0\um
SDK_UCRT_LIB = SDK_ROOT\Lib\10.0.22621.0\ucrt\x64
SDK_UM_LIB = SDK_ROOT\Lib\10.0.22621.0\um\x64
SYSTEM32 = C:\Windows\System32
PYTHON_BASE = C:\Program Files\WindowsApps\PythonSoftwareFoundation.Python.3.12_3.12.2800.0_x64__qbz5n2kfra8p0
```

Private SOURCE, OUTPUT and read-only PYTHON absolute paths are supplied in the
handoff, not selected by untrusted wire/input. OUTPUT is a proposed NEW absent
private root outside public repository; it has NOT been created. Python is the
already approved read-only CPython3.12.10 interpreter, SHA-256
0b471133e110cfb53a061cad528ce8e517d7b9ac41a0a396c39ad795a487fc14.

Each root was resolved and denied reparse entries before accepting its inventory.
Manifest input is sorted full file paths using PowerShell Sort-Object
-CaseSensitive under the recorded es-CL culture. Per file UTF8 record:
relative path with slash separators, NUL, invariant decimal byte count, NUL,
lowercase SHA-256, LF. No BOM. SHA-256 over concatenated records. This algorithm
and culture must match on recheck; it is not a claim of cross-culture ordering.

| Root | Recursive files | Bytes | Manifest SHA-256 |
| --- | ---: | ---: | --- |
| MSVC_BIN | 90 | 88183442 | e542bd3c0904a135cc7076f28b01d4c38bbbb083449a9ee2a3730dc7d0e2baf0 |
| MSVC_INCLUDE | 361 | 16162316 | 1c6bc6eae5bd45ff5ec2af648b0a8bd766f130493dadb444119bc66350ac93ed |
| SDK_UCRT_INCLUDE | 66 | 1055527 | f2f0a232540f5e15f9e8e0b4a5623921993e8c12f7faf4fd368854e9b5768263 |
| SDK_SHARED_INCLUDE | 303 | 11723353 | 1e009330a4fbcafe40dd6fb339d9491011f0e1044e9658bb060cec53f1bb88a8 |
| SDK_UM_INCLUDE | 2214 | 126821714 | bbbbb4c06ab0cffba3def705705c13847a3e3411183437680da137c54f0c4a73 |

MSVC_BIN includes90 recursive files, not the earlier71 immediate files. Pinning
the whole compiler directory includes compiler stages, PDB helpers, TBB and
auxiliary DLLs that cl/link may load by name. No assertion that all90 were loaded.
Actual /showIncludes output must later identify exactly the used headers within
the four pinned include roots. Header tree availability is not an ABI result.

## 2. Concrete binaries, headers, libraries and CRT candidates

File version is PE metadata only, not an execution/version-banner receipt.
Import/static libraries have no PE version resource; their version binding is
the exact path and content hash, not an invented embedded version.

| Alias/file | Bytes | File version | SHA-256 |
| --- | ---: | --- | --- |
| MSVC_BIN/cl.exe | 867912 | 19.43.34810.0 | 9beec04038c74406e4c055593edc07ddda7b166272d77cbf85507d5a6be29ff0 |
| MSVC_BIN/link.exe | 3204680 | 14.43.34810.0 | dfdc692e2837fc67f0da929f1b3330a55ed723b009157a6a604da643a824ccd1 |
| MSVC_BIN/c1.dll | 3362344 | 19.43.34810.0 | 2ced26f549c974b73e3aae74561a56dee030226dc636f945c2f01c1c24e8b660 |
| MSVC_BIN/c2.dll | 10266160 | 19.43.34810.0 | 40511f8285bfdbf4cd159b6352f2aed44a09202e41a457b5c557c1b32c9ac2f2 |
| MSVC_BIN/msobj140.dll | 139296 | 14.43.34810.0 | b7fb7d61d00f50d105c50bad332043172103927ddb3f0b3f12e78c8ffcefab2a |
| MSVC_BIN/mspdb140.dll | 346656 | 14.43.34810.0 | 77fc5cdb106572da9ab1a916129c735bf05d46f0817680adaa60c9b22547f7f8 |
| MSVC_BIN/mspdbcore.dll | 1318432 | 14.43.34810.0 | c64a51699b25f516ab79d6a142bde1622909a85eca23c4b2fab26bc77b6aa75d |
| MSVC_BIN/mspdbsrv.exe | 185424 | 14.43.34810.0 | 2596a42aca02724648f685fdd29260fa65fc1f0dac2aea9e6458711a39f2f843 |
| MSVC_BIN/msvcp140.dll | 576112 | 14.43.34810.0 | 0948751c296eedc894f59b5145db90c3d3b864ab70b15e30499087ca9cd94583 |
| MSVC_BIN/vcruntime140.dll | 120448 | 14.43.34810.0 | ea47efaaebffc729a373956ac4263a451797103fc77891dc577e65999dd77a9d |
| MSVC_BIN/vcruntime140_1.dll | 49792 | 14.43.34810.0 | 38b6b62aa814aa6d570e9f8f8f2a1a0e5487358964b9f1080c33ad1398b0b68e |
| MSVC_LIB/msvcrt.lib | 8029964 | No PE version resource | 213863f3899bd68355b645b26a29df9b3ac649cd23c96f3b3842a1f8b5ac3089 |
| MSVC_LIB/vcruntime.lib | 286164 | No PE version resource | 7d58cc0ca6dcabf552126752861fa6368575d126ebe34e25b3fbe566ed86fde8 |
| MSVC_LIB/oldnames.lib | 157422 | No PE version resource | 533735074def7e97179650450c79a7e5e9433e0e593cabbd55f802a7d09bc00f |
| SDK_UCRT_LIB/ucrt.lib | 285588 | No PE version resource | 7ef4eac926bf597d2f243f16cdfed7e0db22cb3ca34a1d7e088a84c994a03d66 |
| SDK_UM_LIB/kernel32.lib | 313500 | No PE version resource | 25346e02cffca92abff07000d54e1830fe0d8861c31a114eda472547fe9f2f00 |
| SDK_UM_INCLUDE/Windows.h | 7511 | No PE version resource | b337d661d03a4abefb7b86a2742ce1ad5d19b57cd8b858bd13e7bbcc1dbeeaaa |
| SDK_UM_INCLUDE/winnt.h | 816803 | No PE version resource | 2c8a4932205b4d41a03a8112e6f95d5a337044a393511e17a3324ea96e801cce |
| SDK_UM_INCLUDE/jobapi2.h | 2974 | No PE version resource | 398ef4f8277a1edb58e41c5e8233e8dce7744522ba8e989d904e93991a254c71 |
| SDK_UM_INCLUDE/processthreadsapi.h | 36694 | No PE version resource | a692be0b6e83ad600dccf2ca09131f1c1b599ad1c8073afdc1620d1c23703a1a |
| SYSTEM32/ucrtbase.dll | 1377512 | 10.0.26100.9444 (WinBuild.160101.0800) | 5c52e3a303baaac0e0af8bd9b96134993da34bc9d834a31ef37e1d2cdc7fe192 |
| SYSTEM32/vcruntime140.dll | 123472 | 14.50.35719.0 | 184146852727a9db4eea06178716bec3cdbb1015c911f6b0f915b184ad7775b2 |
| SYSTEM32/vcruntime140_1.dll | 47264 | 14.50.35719.0 | e6bfb3662ab4b1969a73441dbe35c96d51441b6bff8cf1fe7430bd5b246ca605 |
| SYSTEM32/kernel32.dll | 861984 | 10.0.26100.9549 (WinBuild.160101.0800) | 4f7e85e01b521aa002692b1e868bee9a3a9ba19b815ce5d16d2e959fb0289feb |
| SYSTEM32/KernelBase.dll | 4254808 | 10.0.26100.9278 (WinBuild.160101.0800) | bffbb14b005b7b2764dbde1a95512aeb95662215fc33c780618435cde6661d6a |
| SYSTEM32/ntdll.dll | 2554168 | 10.0.26100.9549 (WinBuild.160101.0800) | a378d703c3f155d71b57ac53891b5905dc1036d3e763d82980705d1e2a8dd17d |
| SYSTEM32/apisetschema.dll | 204152 | 10.0.26100.9549 (WinBuild.160101.0800) | 568c72f6216d83a716d6fa9bec59ae8d93e6728062d969ac362013f3910c0007 |
| MSVC_BIN/msvcp140_atomic_wait.dll | 50256 | 14.43.34810.0 | 4993c91f8952ece76f6f0438cb98811cdfd840e03e8a2c8200d6954977046a17 |
| MSVC_BIN/tbbmalloc.dll | 114224 | 2021.4 | 534ac1288c43355c3c01bca35b1ce5b2cd3bd012f51ad8d4d23a5eb12a141415 |
| MSVC_BIN/msvcdis140.dll | 1752600 | 14.43.34810.0 | 016d53c0da034f9253265695d9e6fda62939ac07377c18815d85cd96538eb513 |
| MSVC_BIN/pgodb140.dll | 88120 | 14.43.34808.0 | a668eaa4b540a40b82f1113852794dcd95db7bd4924d848bc6c7fe0b409d38fa |
| MSVC_LIB/libcmt.lib | 6531258 | No PE version resource | 2f85dcc9697707be63ce7842cfa4ad0dbc1fddabfcd1c4e6c0afcb372fdff83c |
| MSVC_LIB/libvcruntime.lib | 2080514 | No PE version resource | e8060e3d69ea5303431e92cdbdff68b73f3a3739526db27f52b2e61897bf7b2e |
| SDK_UCRT_LIB/libucrt.lib | 42450418 | No PE version resource | 742bf3739ddb2e3fcd94bd7a1618aea1c832a08d1304f0a70fc59f5ae13307b9 |
| PYTHON_BASE/vcruntime140.dll | 120400 | 14.42.34438.0 | 052ad6a20d375957e82aa6a3c441ea548d89be0981516ca7eb306e063d5027f4 |
| PYTHON_BASE/vcruntime140_1.dll | 49776 | 14.42.34438.0 | 6a99bc0128e0c7d6cbbf615fcc26909565e17d4ca3451b97f8987f9c6acbc6c8 |
| SYSTEM32/advapi32.dll | 791056 | 10.0.26100.8875 | 74fefade3065de4bf2b870777369222fbc2908ddcad2aa4cb63a33f1eef9979d |
| SYSTEM32/ole32.dll | 1720576 | 10.0.26100.8875 | 1053ffb858cddbe29eaaa6a5b0836b88c7cd11fbd58605288600e507c06db443 |
| SYSTEM32/psapi.dll | 42864 | 10.0.26100.8521 | 6c8ebe6621224d11ded0c920873d67b5255fd515e8c4ea803cd587c8232bee5c |
| SYSTEM32/version.dll | 55192 | 10.0.26100.1150 | cea99f212af557a9613150c5509631403ed0f05f5d9a06ac42039bd59b40e39a |
| SYSTEM32/user32.dll | 1974768 | 10.0.26100.8875 | f285937030bcb325cad39ee5be4818f6666241229adeadea4ff1ae469dfd7ef3 |
| SYSTEM32/imagehlp.dll | 137832 | 10.0.26100.4202 | 58117bbc51c4a56b6c4789e190f33a540b7734e394ada9652e2832e3d2e16588 |
| SYSTEM32/mscoree.dll | 430080 | 10.0.26100.3624 | 07f1ea065c452d37da2ad56ce505184e41947c42a560d8235276e0fb8b758701 |
| SYSTEM32/oleaut32.dll | 916152 | 10.0.26100.9549 | 92f48fb8a5f59a507037b55fcfcc4980904ad38443469e289842b3e35e74c234 |
| SYSTEM32/shlwapi.dll | 440968 | 10.0.26100.8875 | 2708f3d0191400173c2d0917ae189e7089b8bec7e1f35f8f85be383fa610d94c |
| SYSTEM32/xmllite.dll | 295088 | 10.0.26100.9549 | a342608c9370e468cf5c003aa0b9c982af5f2bfea8977f757a2283adf7c8d8d5 |
| SYSTEM32/dbghelp.dll | 2317640 | 10.0.26100.9549 | 2d2ec94891162a61d86789133623b47d64d74c15d6be99473b25ad7a6468cf39 |
| SYSTEM32/bcrypt.dll | 195080 | 10.0.26100.8875 | 9956c503e5adfef784f57ceb361eec14b5e2c83b4308405459590f96c797a471 |
| SYSTEM32/ws2_32.dll | 553552 | 10.0.26100.8875 | d82732cf85c19e632ccaf08bd6be0c70142eafbfcd515c24495261d12aaec570 |

The static I01 candidate link closure is EXACTLY five explicit files:
MSVC_LIB/libcmt.lib, MSVC_LIB/libvcruntime.lib, SDK_UCRT_LIB/libucrt.lib,
MSVC_LIB/oldnames.lib and SDK_UM_LIB/kernel32.lib. /NODEFAULTLIB forbids silently
adding library search/defaults. An unresolved symbol or extra required library
stops for a new reviewed inventory, not an automatic link retry/fallback.

The three /MD libraries are retained in the table because design section7
proposes /MD for the LATER native runner. They are NOT the selected I01 link set.
Compiler/tool DLLs still use their own dynamic CRT even when the new test output
uses static CRT; this does not make the build tools independent of Windows DLLs.

## 3. Actual static inspection versus unresolved loaded closure

A bounded read-only PE32+ parser inspected imports/delay-imports of cl/link,
c1/c2, compiler-local msvcp140/vcruntime140/vcruntime140_1, System32 UCRT/VC
runtime candidates and python312.dll. It used no LoadLibrary, native API or
compiler. File cap32MiB, section cap96, import directory64KiB,256 descriptors,
256-byte names, range-checked RVA-to-file offsets. All inspected files were x64.
This is static byte inspection, not a universal PE validator or loaded graph.

Observed selected dependencies:

- cl.exe directly names msvcp140/vcruntime140/vcruntime140_1, kernel32,
  advapi32, ole32 and thirteen CRT API sets; delays psapi/version.
- link.exe names the same three CRT DLLs plus tbbmalloc, kernel32, advapi32,
  psapi/user32 and twelve CRT API sets. Delays imagehlp/mscoree/msvcdis140/
  ole32/oleaut32/pgodb140.
- c1.dll names CRT DLLs, kernel32/ntdll/advapi32/ole32/oleaut32/psapi/shlwapi;
  delays mscoree/xmllite. c2.dll additionally names msvcp140_atomic_wait and
  tbbmalloc; delays dbghelp/mscoree/msobj140/ole32/oleaut32/pgodb140.
- Compiler-local and System32 vcruntime140 DLLs name kernel32 and CRT API sets.
  System32 ucrtbase names29 core API-set contracts, not29 files guessed by name.
- python312.dll directly names vcruntime140 and CRT API sets, plus kernel32,
  advapi32/bcrypt/version/ws2_32 and the core path API set.

B05/B06 explain why absolute top-level paths and PATH pinning alone do not bind
every loaded dependency: already-loaded modules, KnownDLLs, API sets and
redirection may intervene. API-set names are contracts, not missing files to
download. The selected System32/apisetschema bytes are hashed; no live mapping,
KnownDLL registry, forwarder graph or dynamic LoadLibrary graph was asserted.
All direct named system files listed above were found and hashed. Transitive/
delay/dynamic loaded closure remains NOT_RUN, requiring approved build-time
evidence. A name/path/version match alone cannot promote a runtime profile.

Concrete conflict: Python's app-local vcruntime is14.42.34438, compiler-local
14.43.34810, System3214.50.35719. B08 requires a runtime at least as new as the
build tools. Do NOT assume a /MD test DLL loaded into this Python would select
System32's newer DLL. No runtime/DLL was copied, replaced, installed or loaded
to resolve the conflict. No global environment, loader policy or trust changed.

**Separate proposal requiring MAIN approval:** for I01 deterministic tests and
the standalone ABI probe ONLY, select /MT with the exact static five-library
closure above. The future runner's /MD design stays unchanged and CLOSED.
No CRT-owned allocation, FILE/locale/errno state, exception or deallocation
crosses the Python/C interface: fixed caller-owned buffers and integer values
only. The core contains no heap/I/O/clock/OS calls. Ordinary tool/DLL CRT startup
is not a Job Object/cgroup control and is not claimed to execute zero OS calls.
The resulting PE imports still need inspection before loading. Unexpected VC/
UCRT dynamic dependency or an unresolved dependency stops review, no fallback.

## 4. Proposed exact compile/link commands, NOT EXECUTED

MAIN must first approve this inventory, /MT I01-only choice, output boundary,
compiled pure test/ABI execution and the unapproved wire/finality amendments
identified in approval.md. Any rejected amendment is resolved in docs first.
Compiler execution approval is NOT platform-controller or host authority.

The following are argument arrays, not shell-concatenated commands. SOURCE and
OUTPUT are the exact private handoff roots; the root must be absent initially.
Future input receipt binds the approved full source commit plus SHA-256 of
controller.h/controller.c/abi_probe.c and the three authorized tests. Those files
are NOT_CREATED now: no command below can honestly be called executed/ready-built.
No working-tree drift or substitute source is accepted.

```powershell
$taskVc = 'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.43.34808'
$taskSdk = 'C:\Program Files (x86)\Windows Kits\10'
$taskCl = Join-Path $taskVc 'bin\Hostx64\x64\cl.exe'
$taskLink = Join-Path $taskVc 'bin\Hostx64\x64\link.exe'
$taskIncludeArgs = @(
  ('/I' + (Join-Path $taskVc 'include')),
  ('/I' + (Join-Path $taskSdk 'Include\10.0.22621.0\ucrt')),
  ('/I' + (Join-Path $taskSdk 'Include\10.0.22621.0\shared')),
  ('/I' + (Join-Path $taskSdk 'Include\10.0.22621.0\um'))
)
$taskCommon = @('/nologo','/c','/TC','/std:c17','/MT','/Zl','/X',
  '/W4','/WX','/sdl','/GS','/guard:cf','/O2','/showIncludes',
  '/DUNICODE','/D_UNICODE','/D_WIN32_WINNT=0x0A00') + $taskIncludeArgs
$taskLibraries = @(
  (Join-Path $taskVc 'lib\x64\libcmt.lib'),
  (Join-Path $taskVc 'lib\x64\libvcruntime.lib'),
  (Join-Path $taskSdk 'Lib\10.0.22621.0\ucrt\x64\libucrt.lib'),
  (Join-Path $taskVc 'lib\x64\oldnames.lib'),
  (Join-Path $taskSdk 'Lib\10.0.22621.0\um\x64\kernel32.lib')
)
$taskCoreCompile = $taskCommon + @(
  ('/Fo' + (Join-Path $taskOutput 'core.obj')),
  (Join-Path $taskSource 'scripts\native_physical_cpu\controller.c'))
$taskProbeCompile = $taskCommon + @(
  ('/Fo' + (Join-Path $taskOutput 'abi.obj')),
  (Join-Path $taskSource 'scripts\native_physical_cpu\abi_probe.c'))
$taskLinkCommon = @('/NOLOGO','/MACHINE:X64','/NODEFAULTLIB','/Brepro',
  '/DYNAMICBASE','/NXCOMPAT','/HIGHENTROPYVA','/guard:cf',
  '/INCREMENTAL:NO','/OPT:REF','/OPT:ICF','/MANIFEST:NO')
$taskCoreLink = $taskLinkCommon + @('/DLL',
  ('/OUT:' + (Join-Path $taskOutput 'core.dll')),
  ('/IMPLIB:' + (Join-Path $taskOutput 'core.lib')),
  (Join-Path $taskOutput 'core.obj')) + $taskLibraries
$taskProbeLink = $taskLinkCommon + @('/SUBSYSTEM:CONSOLE',
  ('/OUT:' + (Join-Path $taskOutput 'abi.exe')),
  (Join-Path $taskOutput 'abi.obj')) + $taskLibraries
# FUTURE approved child launches, in order:
# cl.exe with taskCoreCompile; link.exe with taskCoreLink.
# cl.exe with taskProbeCompile; link.exe with taskProbeLink.
# Run abi.exe with NO arguments, private bounded stdout.
# Load the pinned core.dll only for the three pure supplied-vector test files.
```

No response file, shell, vcvars, compiler discovery, default library lookup,
manifest tool, PDB/debug helper output request, DLL installation or download.
Exports are to be explicit in controller.h; no new .def/helper/package path.
Do not suppress warnings, add /FORCE or adjust packing/options to make ABI pass.

Historical initial proposal below is retained, not the amended execution recipe.
Contracts section8 now specifies the operator Python capture, separate NEW tool
TEMP scratch, separate NEW external outcome custody, and combined output/scratch
observation bounds. The four compiler/linker argv and five pinned libraries above
are unchanged. ABI/probe/DLL execution remains a separate held review operation.

Child-only process environment was originally proposed, not applied: clear inherited
CL/_CL_/LINK/INCLUDE/LIB/LIBPATH and injection/path override variables; PATH only
MSVC_BIN and SYSTEM32; SystemRoot exactly C:\Windows; TMP/TEMP and working
directory exactly the NEW private OUTPUT. No persistent/user environment edit.
Use ProcessStartInfo.ArgumentList, UseShellExecute=false, bounded captured pipes.
No stdout/stderr raw log in public repo. Compiler/tool execution itself is an
approved subprocess, not science launch/controller implementation. No extra
environment setup executable. An unsupported minimal environment stops review.

Before each future action: exact input hash/tree recheck, non-reparse regular
files/roots and source pin, no existing output file, exclusive new output custody.
90s per compile/link stage, 5s ABI run, output<=2MiB per tool stream, <=4096 ABI
stdout, no ABI stderr accepted; private total output64MiB/32 files. At most one
tool stage active. Unexpected timeout/output/helper artifact/digest change fails
and retains private evidence, never auto-deletes or kills arbitrary processes.
If safely enforcing these bounds would require an unapproved launcher/controller,
MAIN must provide a separately approved execution mechanism; none is invented.
No controller/no-escape timing proof is claimed from bounded build commands.

Expected output allowlist: core.obj/core.dll/core.lib/core.exp, abi.obj/abi.exe,
private bounded build/ABI receipts/streams and pytest-owned child artifacts.
Only the exact new output root is written, never repository/interpreter/toolchain.
No backup removal/production/private state/drill or host installation.

Proposed future test command after test-first RED and core implementation:

```text
<READ_ONLY_PYTHON> -B -m pytest -q -p no:cacheprovider
  tests/worker_accounting/native/test_contract.py
  tests/worker_accounting/native/test_bounds.py
  tests/worker_accounting/native/test_scope.py
  --basetemp <NEW_PRIVATE_OUTPUT>/pytest
  --junitxml <NEW_PRIVATE_OUTPUT>/unit.xml
```

The test runner must bind the exact reviewed DLL path/hash without compiling,
installing or choosing fallback DLLs inside tests. Any test-only path transport
is child-local and reviewed, never controller configuration or runtime authority.
No source/test command has run yet. Actual test count/timing/results are unset.

## 5. Expected ABI probe, never measured from typedef reading

The separately authorized NEW abi_probe.c, when authored test-first, must report
actual sizeof, alignment and offsetof from real SDK types, without packed
replicas. Do NOT certify layout by guessed Python structures/static assertions.

Expected x64 targets: LARGE_INTEGER8, basic accounting48, basic limits64,
extended limits144, STARTUPINFOW104, STARTUPINFOEXW112, PROCESS_INFORMATION24.
Expected accounting offsets TotalUserTime0/TotalKernelTime8,
TotalProcesses36/ActiveProcesses40/TotalTerminatedProcesses44.
Report every field subsequently used by the future platform bindings, including
basic limits PerJobUserTimeLimit/LimitFlags/ActiveProcessLimit/Affinity and
extended BasicLimitInformation, and compare with reviewed targets. Unexpected
value fails ABI gate rather than changing packing or guessing from pointer width.
Scalar DWORD/BOOL4, SIZE_T/ULONG_PTR/pointer8 and signed LARGE_INTEGER semantics
are expected, not measured. No CreateJobObject/QueryInformationJobObject/
CreateProcess/clock/process-measurement invocation in this probe. Header/type
declarations are not actual API-call permission.

Windows ABI compile/run NOT_RUN. Linux compiler/sysroot/UAPI/libc NOT_INVENTORIED/
NOT_RUN and H02 CLOSED. No Windows result can approve Linux ABI or native gate.
Compiled supplied-vector PASS, if obtained later, still proves no real counters,
containment, job CPU limits, observer timing, parent tail or durable release.

## 6. Fresh official source receipt appendix

Actual bounded HTTPS reads via the approved interpreter -B, four readers,
15s per request, max1MiB; response bodies memory-only, not repository mirrors.
All200, requested equals final URL, no executable/download/install request.
These eight build receipts supplement, not replace, the original34 native
research receipts. Digests are HTTPS byte provenance, not signature verification.

| ID | Official requested/final URL | UTC completion | Bytes | SHA-256 |
| --- | --- | --- | ---: | --- |
| B01 | [runtime flags](https://learn.microsoft.com/en-us/cpp/build/reference/md-mt-ld-use-run-time-library?view=msvc-170) | 2026-10-03T16:04:52.412781+00:00 | 51107 | 6aea2613ee67041c8cc586cc6a734c066121a14587840dfa6d72ecd36042f3a9 |
| B02 | [explicit library selection](https://learn.microsoft.com/en-us/cpp/build/reference/nodefaultlib-ignore-libraries?view=msvc-170) | 2026-10-03T16:04:52.688997+00:00 | 50573 | 5587ed39fc89fb1276b5efad6d42fdf931508540f40f0ab36d0f8ad4028fffeb |
| B03 | [actual include paths](https://learn.microsoft.com/en-us/cpp/build/reference/showincludes-list-include-files?view=msvc-170) | 2026-10-03T16:04:52.388330+00:00 | 48548 | 3a0ac43fb721c0d920a4a76a441e802ddc8644294df0c2d915e40a82b80ea5e6 |
| B04 | [CRT library composition](https://learn.microsoft.com/en-us/cpp/c-runtime-library/crt-library-features?view=msvc-170) | 2026-10-03T16:04:52.412781+00:00 | 64755 | b3b35f3a5e47846fa83bebb82c76856bb158374024525f97743e1e66941a1291 |
| B05 | [DLL search and loaded modules](https://learn.microsoft.com/en-us/windows/win32/dlls/dynamic-link-library-search-order) | 2026-10-03T16:04:52.634863+00:00 | 63810 | ecf5f31efc88b3d5c1bed7e279b5227dad5711004f155963d2519c8914f23509 |
| B06 | [API-set contract routing](https://learn.microsoft.com/en-us/windows/win32/apiindex/windows-apisets) | 2026-10-03T16:04:52.657945+00:00 | 56798 | 56ca145d908728c3a33d47b3112b43ff8c2306570062f6cf752203e40f2e4004 |
| B07 | [PE import byte layout](https://learn.microsoft.com/en-us/windows/win32/debug/pe-format) | 2026-10-03T16:04:52.704001+00:00 | 281720 | 6b8a2a4c36b85be9307ef36b6ca85635a7cbfe2ae808c6e5cc94fb9d0d5d7fd9 |
| B08 | [runtime version requirement](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170) | 2026-10-03T16:04:52.721538+00:00 | 65446 | e789b23ad81537a66924bf7ed5db72bac7f9fe4fdb424cc2181fcfd6679ddc2e |

## 7. Exact next decision, not an implementation completion claim

MAIN reviews this full inventory/recipe and the separately flagged DRAINED
timestamp/50ms final-settle amendment BEFORE compiler/test-binary execution
or adoption of that amendment. /MT is an explicit I01-only request, not a silent
change to the approved future runner. No guessed provider/fallback or package.

After that decision: author the three golden/cap/state/safeerror tests first,
record real RED evidence, author bounded core only, record compiled pure GREEN
and separately measured ABI output at exact source/toolchain pins. Continue
until independently reviewable I01 evidence, without any OS-controller source.
Current status remains source/tests/probe NOT_CREATED, compiler/ABI tests NOT_RUN.
Protected pure3bed source/test and every app/worker/db/ops/manifest remain unchanged.
