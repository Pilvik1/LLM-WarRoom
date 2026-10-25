"""Council preset and seat schemas."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator


WorkflowType = Literal["ask", "council", "compare"]


class SeatDefinition(BaseModel):
    """One reasoning seat and the model alias assigned to it."""

    id: str
    name: str
    role_prompt: str
    model_alias: str
    enabled: bool = True


class CouncilPreset(BaseModel):
    """Reusable workflow, seat, reviewer, and synthesizer configuration."""

    id: str
    name: str
    description: str = ""
    workflow_type: WorkflowType
    seats: list[SeatDefinition] = Field(default_factory=list)
    reviewer_aliases: list[str] = Field(default_factory=list)
    synthesizer_alias: str
    built_in: bool = False

    @model_validator(mode="after")
    def validate_assignments(self) -> "CouncilPreset":
        enabled_seats = [seat for seat in self.seats if seat.enabled]
        if not enabled_seats:
            raise ValueError("a council preset requires at least one enabled seat")
        seat_ids = [seat.id for seat in self.seats]
        if len(seat_ids) != len(set(seat_ids)):
            raise ValueError("seat ids must be unique within a preset")
        return self
