"""Bounded private Linux qualification context, not a public launch broker.

Encoding/recipe preparation does not launch, create units/accounts, or grant a
method runtime. Native code independently repeats every byte validation.
"""
import re
import struct

MAX_BYTES = 32768
HEADER = struct.Struct("<4sHHIIIIII16s16s")
ENV_KEYS = frozenset({"LANG", "LC_ALL", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                      "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "PYTHONHASHSEED"})


class ContextError(ValueError):
    """Safe fixed error, never include a private context value."""


def reject():
    raise ContextError("linux_context_invalid")


def identity(value):
    if type(value) is not str or not re.fullmatch(r"[0-9a-f]{32}", value) or value == "0" * 32:
        reject()
    return bytes.fromhex(value)


def text(value, cap=1024, path=False):
    if type(value) is not str or not value or "\0" in value:
        reject()
    invalid = False
    try:
        raw = value.encode("utf-8", "strict")
    except UnicodeError:
        invalid = True
    if invalid:
        reject()
    if len(raw) > cap:
        reject()
    if path and (not value.startswith("/") or value == "/" or
                 any(part in ("", ".", "..") for part in value[1:].split("/"))):
        reject()
    return raw


def encode_context(*, budget_class, uid, gid, attempt, object_id,
                   executable, argv0, cwd, arguments, environment):
    if (type(budget_class) is not int or budget_class not in (1, 2) or
            any(type(v) is not int or not 1 <= v < 2**32 - 1 for v in (uid, gid))):
        reject()
    attempt_raw, object_raw = identity(attempt), identity(object_id)
    if type(arguments) is not list or not 1 <= len(arguments) <= 32:
        reject()
    if type(environment) is not list or len(environment) > 32:
        reject()
    # Validate individual and combined bounds before the final byte construction.
    fields = [text(executable, path=True), text(argv0, path=True), text(cwd, path=True)]
    args = [text(v) for v in arguments]
    env = [text(v) for v in environment]
    if sum(map(len, args)) > 16384 or sum(map(len, env)) > 4096:
        reject()
    keys = set()
    for value in environment:
        key, separator, unused = value.partition("=")
        if not separator or key not in ENV_KEYS or key in keys:
            reject()
        keys.add(key)
    fields.extend(args)
    fields.extend(env)
    length = sum(4 + len(v) for v in fields)
    if length + HEADER.size > MAX_BYTES:
        reject()
    return HEADER.pack(b"LCX1", 1, budget_class, uid, gid, len(args), len(env),
                       length, 0, attempt_raw, object_raw) + b"".join(
                           struct.pack("<I", len(v)) + v for v in fields)


def decode_context(raw):
    if type(raw) is not bytes or not HEADER.size <= len(raw) <= MAX_BYTES:
        reject()
    magic, version, cls, uid, gid, argc, envc, count, reserved, attempt, obj = HEADER.unpack_from(raw)
    if magic != b"LCX1" or version != 1 or reserved or count != len(raw) - 64:
        reject()
    if not 1 <= argc <= 32 or not 0 <= envc <= 32:
        reject()
    fields, offset = [], 64
    for _ in range(3 + argc + envc):
        if offset + 4 > len(raw):
            reject()
        size = struct.unpack_from("<I", raw, offset)[0]
        offset += 4
        if not 1 <= size <= 1024 or size > len(raw) - offset:
            reject()
        invalid = False
        try:
            value = raw[offset:offset + size].decode("utf-8", "strict")
        except UnicodeError:
            invalid = True
        if invalid:
            reject()
        fields.append(value)
        offset += size
    if offset != len(raw):
        reject()
    result = dict(budget_class=cls, uid=uid, gid=gid, attempt=attempt.hex(),
                  object_id=obj.hex(), executable=fields[0], argv0=fields[1], cwd=fields[2],
                  arguments=fields[3:3 + argc], environment=fields[3 + argc:])
    if encode_context(**result) != raw:
        reject()
    return result


def unit_arguments(systemd_run, controller, context, attempt, parent, budget_class):
    identity(attempt)
    for value in (systemd_run, controller, context):
        text(value, path=True)
    if parent != "geophysics-cpu-parent-" + attempt + ".service" or type(budget_class) is not int:
        reject()
    if budget_class not in (1, 2):
        reject()
    # Fixed qualification recipe. Secure production launch is separately reviewed.
    properties = [
        "Type=exec", "ExitType=main", "Delegate=cpu memory pids",
        "DelegateSubgroup=observer", "KillMode=control-group", "KillSignal=SIGKILL", "SendSIGKILL=yes",
        # System-manager default root; explicit User=root triggers v255's
        # seccomp UID setup path, dropping CAP_SETUID before NNP exec.
        # lc_prepare independently verifies the actual root IDs/three caps.
        "TimeoutStopSec=1s", "Restart=no",
        "CPUAccounting=yes", "MemoryAccounting=yes", "TasksAccounting=yes",
        "BindsTo=" + parent, "After=" + parent,
        "RuntimeMaxSec=" + ("120s" if budget_class == 1 else "300s"),
        "NoNewPrivileges=yes", "PrivateNetwork=yes", "PrivateTmp=yes",
        "PrivateDevices=yes", "RestrictAddressFamilies=AF_UNIX",
        "LockPersonality=yes", "ProtectHome=yes",
        "CapabilityBoundingSet=CAP_SETUID CAP_SETGID CAP_SETPCAP", "UMask=0077",
    ]
    return [systemd_run, "--quiet", "--pipe", "--wait",
            "--unit=geophysics-cpu-qual-" + attempt + ".service"] + [
                "--property=" + prop for prop in properties] + [controller, context]
