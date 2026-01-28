import logging


logger = logging.getLogger("auth.email")


def send_verification_email(email: str, token: str) -> None:
    logger.info("Verify email for %s with token: %s", email, token)


def send_password_reset_email(email: str, token: str) -> None:
    logger.info("Password reset for %s with token: %s", email, token)
