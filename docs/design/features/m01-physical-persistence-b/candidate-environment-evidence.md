# Local API regression environment, measured2026-10-03

Authorization was committed/pushed as c541c9f BEFORE creation/install. Creation and the exact two-file requirements install both exited0, with no version fallback, requirements edits or changes to the prior environment. `python -m pip check` exited0: No broken requirements found. Compatibility imports of fastapi/sqlalchemy/alembic/httpx/numpy/scipy completed, exit0. Complete unchanged tests/api is running; no PASS asserted yet. The prior collection errors and both102PASS/1FAIL subsets plus isolated retry remain separately retained in candidate-schema-evidence.json.

Interpreter: CPython3.12.10 tags/v3.12.10:0cc8128, Apr8 2025,12:21:36, MSCv.1943 AMD64. New interpreter `.venv-api-oct3/Scripts/python.exe`; base executable is the existing Microsoft Store Python3.12 alias. Read-only in-memory `select sqlite_version(),sqlite_source_id()` returned3.49.1 and `2025-02-18 13:38:58 873d4e274b4988d260ba8354a9718324a1c26187a4ab4c1cc0227c03d0f10e70`. Imported `_sqlite3` extension belongs to Microsoft Store PythonSoftwareFoundation.Python.3.12_3.12.2800.0_x64; actual extension126184bytes, SHA25664b51df2805c58b023a875e8ae3be7ac7f61ef664f32ca6c90f6315da47ef0bc. This is limited driver provenance, NOT a complete loaded-DLL/patch proof or independently reviewed supported tuple. No target/host/WAL probe, upgrade or install outside the authorized new environment occurred.

SQLite3.49.1 is in the upstream affected range of the already retained B WAL source. Physical supported-patch registry remains EMPTY; all physical WAL/native/death/provider/CPU/host gates CLOSED/NOT_RUN. Protected legacy regression execution is distinct from physical admission. No environment metadata becomes a native ACK.

## Full resolved freeze

Actual `python -m pip freeze --all`, exit0 (includes bootstrap pip; names/spelling retained):

```text
aiosqlite==0.22.1
alembic==1.20.0
annotated-doc==0.0.5
annotated-types==0.8.0
anyio==4.15.1
argon2-cffi==25.1.0
argon2-cffi-bindings==26.1.0
bcrypt==5.0.0
certifi==2026.7.22
cffi==2.1.1
click==8.5.0
colorama==0.4.6
contourpy==1.4.0
cryptography==50.0.2
cycler==0.12.1
defusedxml==0.7.1
dnspython==2.8.0
email-validator==2.3.0
fastapi==0.141.1
fastapi-users==15.0.5
fastapi-users-db-sqlalchemy==7.0.0
fonttools==4.66.1
greenlet==3.5.6
h11==0.16.0
httpcore==1.0.9
httpx==0.28.1
idna==3.20
iniconfig==2.3.0
kiwisolver==1.5.1
loguru==0.7.3
makefun==1.16.0
Mako==1.4.3
MarkupSafe==3.0.4
matplotlib==3.11.2
mt_metadata==1.0.10
numpy==2.2.6
packaging==26.3
pandas==3.0.6
pillow==12.3.0
pip==25.0.1
pluggy==1.6.0
psutil==7.2.2
pwdlib==0.3.0
pycparser==3.0
pydantic==2.13.5
pydantic_core==2.46.5
Pygments==2.21.0
PyJWT==2.15.1
pyparsing==3.3.3
pyproj==3.8.0
pytest==9.1.1
python-dateutil==2.9.0.post0
python-multipart==0.0.32
ruff==0.15.18
scipy==1.15.2
six==1.17.0
SQLAlchemy==2.0.54
starlette==1.7.0
typing-inspection==0.4.4
typing_extensions==4.16.0
tzdata==2026.5
uvicorn==0.54.0
win32_setctime==1.2.0
xarray==2026.9.0
```
