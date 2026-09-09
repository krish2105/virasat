"""`uv run seed-admin USERNAME` — create the first admin officer (password prompted)."""

from __future__ import annotations

import argparse
import getpass

from virasat.api.deps import hash_password
from virasat.db.models import Officer, Role
from virasat.db.session import session_scope


def create_officer(username: str, password: str, display_name: str, role: Role) -> None:
    with session_scope() as s:
        if s.query(Officer).filter_by(username=username).first():
            raise SystemExit(f"seed-admin: officer '{username}' already exists")
        s.add(
            Officer(
                username=username,
                password_hash=hash_password(password),
                display_name=display_name,
                role=role,
            )
        )


def main() -> None:
    parser = argparse.ArgumentParser(prog="seed-admin")
    parser.add_argument("username")
    parser.add_argument("--name", default="Heritage Officer")
    parser.add_argument("--role", choices=[r.value for r in Role], default="admin")
    parser.add_argument("--password", help="omit to be prompted")
    args = parser.parse_args()
    password = args.password or getpass.getpass("password: ")
    create_officer(args.username, password, args.name, Role(args.role))
    print(f"seed-admin: created {args.role} '{args.username}'")


if __name__ == "__main__":
    main()
