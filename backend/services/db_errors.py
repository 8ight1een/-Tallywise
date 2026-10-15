from sqlalchemy.exc import IntegrityError


def is_constraint_violation(
    exc: IntegrityError,
    sqlstate: str,
    constraint_name: str,
) -> bool:
    db_error = exc.driver_exception

    return (
        getattr(db_error, "sqlstate", None) == sqlstate
        and getattr(db_error, "constraint_name", None) == constraint_name
    )