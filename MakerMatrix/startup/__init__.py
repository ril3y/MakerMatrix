"""
Application startup orchestration.

Provides StartupStep / run_startup_steps for the FastAPI lifespan handler so
each step (DB create, default printers, supplier registration, etc.) has a
single shape: name + required flag + async run().

This replaces a ~170-line lifespan body that mixed required/optional setup
behind ad-hoc try/except patterns.
"""

from MakerMatrix.startup.steps import StartupStep, run_startup_steps

__all__ = ["StartupStep", "run_startup_steps"]
