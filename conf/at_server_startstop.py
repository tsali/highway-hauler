"""
Highway Hauler — Server start/stop hooks.
"""

from evennia.utils import logger


def at_server_start():
    """Called every time the server starts up."""
    logger.log_info("Highway Hauler server starting up.")

    # Ensure the ContractExpiryScript is running
    from evennia.utils.search import search_script
    from typeclasses.scripts import ContractExpiryScript

    existing = search_script("contract_expiry")
    if not existing:
        from evennia.utils import create
        script = create.create_script(
            ContractExpiryScript,
            key="contract_expiry",
            persistent=True,
        )
        logger.log_info(f"Created ContractExpiryScript: {script}")
    else:
        logger.log_info("ContractExpiryScript already running.")


def at_server_stop():
    """Called when the server shuts down."""
    logger.log_info("Highway Hauler server shutting down.")
