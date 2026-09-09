from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from virasat.api import schemas
from virasat.api.deps import clear_session, current_officer, get_db, issue_session, verify_password
from virasat.db.models import AuditLog, Officer

router = APIRouter(prefix="/auth", tags=["auth"])


def _out(o: Officer) -> schemas.OfficerOut:
    return schemas.OfficerOut(
        id=o.id,
        username=o.username,
        display_name=o.display_name,
        role=o.role.value,
        locale=o.locale,
    )


@router.post("/login", response_model=schemas.OfficerOut)
def login(
    body: schemas.LoginIn, response: Response, db: Session = Depends(get_db)
) -> schemas.OfficerOut:
    officer = db.scalar(select(Officer).where(Officer.username == body.username))
    if officer is None or not verify_password(body.password, officer.password_hash):
        raise HTTPException(401, "invalid credentials")
    issue_session(response, officer)
    db.add(AuditLog(actor=f"officer:{officer.username}", action="login", payload={}))
    return _out(officer)


@router.post("/logout", status_code=204, response_model=None)
def logout(response: Response, officer: Officer = Depends(current_officer)) -> None:
    clear_session(response)


@router.get("/me", response_model=schemas.OfficerOut)
def me(officer: Officer = Depends(current_officer)) -> schemas.OfficerOut:
    return _out(officer)
