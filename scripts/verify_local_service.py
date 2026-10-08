"""Read-only Unix-socket API readiness; no secret, login, upload or job."""

from __future__ import annotations

import argparse
import http.client
import json
import socket


class UnixConnection(http.client.HTTPConnection):
    def __init__(self, path: str):
        super().__init__("geophysics.ml.fasl-work.com", timeout=10)
        self.path = path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(self.path)


def verify(path: str) -> None:
    for route, expected in (("/api/auth/config", 200), ("/api/projects", 401)):
        connection = UnixConnection(path)
        try:
            connection.request("GET", route, headers={"Host": "geophysics.ml.fasl-work.com",
                               "X-Forwarded-Proto": "https", "Accept": "application/json"})
            response = connection.getresponse()
            raw = response.read(4097)
            if (response.status != expected or len(raw) > 4096
                    or response.getheader("Content-Encoding") not in (None, "identity")
                    or not response.getheader("Content-Type", "").startswith("application/json")):
                raise ValueError("API readiness transport/status boundary failed")
            body = json.loads(raw)
            if route.endswith("config") and body != {"mode": "local", "registration_enabled": False,
                                                        "mail_flows_enabled": False}:
                raise ValueError("wrong auth profile")
            if not isinstance(body, dict):
                raise ValueError("API readiness body is not an object")
        finally:
            connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--socket", required=True)
    args = parser.parse_args()
    verify(args.socket)
    print("Unix API config/project boundary passed; not full release acceptance.")


if __name__ == "__main__":
    main()
