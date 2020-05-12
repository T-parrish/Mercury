from sqlalchemy import Table, Column, Enum, DateTime, Boolean, Text, ForeignKey

from sqlalchemy.dialects.postgresql import UUID

from . import TaskTypes
from . import metadata

# Tasks are stored in DB upon creation of a task object through the
# Mediator, task status is updated upon completion of said task.
tasks = Table(
    "tasks", metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
    Column("owner", UUID(as_uuid=True), ForeignKey('users.id', ondelete="CASCADE"), nullable=False),
    Column("task_type", Enum(TaskTypes)),
    Column("time_start", DateTime),
    Column("time_finished", DateTime),
    Column("error", Text()),
    Column("success", Boolean)
)
