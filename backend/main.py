"""FastAPI backend for WarRoom."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ValidationError
from typing import List, Dict, Any
import uuid
import json
import asyncio
from datetime import datetime

from . import storage
from .case_runner import ask_case_from_message, new_run_id
from .compare_runner import run_compare_case
from .council import run_full_council, generate_conversation_title, stage1_collect_responses, stage2_collect_rankings, stage3_synthesize_final, calculate_aggregate_rankings
from .critique_runner import run_critique_case
from .decide_runner import run_decide_case
from .evaluate_runner import run_evaluate_case
from .war_room_runner import run_war_room_case
from .run_storage import save_run_record
from .schemas.case import CaseInput
from .schemas.run import RunRecord

app = FastAPI(title="WarRoom API")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""
    pass


class SendMessageRequest(BaseModel):
    """Request to send a message in a conversation."""
    content: str


class EvaluateCaseRequest(BaseModel):
    """Request to evaluate one candidate output against a task."""
    task: str
    candidate_output: str
    criteria: List[str] = Field(default_factory=list)


class CritiqueCaseRequest(BaseModel):
    """Request to critique one candidate output or artifact against a task."""
    task: str
    candidate_output: str | None = None
    artifact: str | None = None
    criteria: List[str] = Field(default_factory=list)


class CompareCandidateRequest(BaseModel):
    """Candidate input for compare cases."""
    id: str
    title: str
    content: str


class CompareCaseRequest(BaseModel):
    """Request to compare candidates against a task."""
    task: str
    candidates: List[CompareCandidateRequest]
    criteria: List[str] = Field(default_factory=list)


class DecideCaseRequest(BaseModel):
    """Request to deterministically decide from scores or source artifacts."""
    source_run_id: str | None = None
    evaluation_payload: Dict[str, Any] | None = None
    thresholds: Dict[str, Any] = Field(default_factory=dict)
    rules: Dict[str, Any] = Field(default_factory=dict)


class WarRoomCaseRequest(BaseModel):
    """Request to run the War Room workflow."""
    task: str
    context: str | None = None
    stakes: str | None = None
    criteria: List[str] = Field(default_factory=list)
    candidate_output: str | None = None
    candidates: List[CompareCandidateRequest] = Field(default_factory=list)
    respondent_aliases: List[str] = Field(default_factory=list)
    synthesizer_alias: str | None = None


class ConversationMetadata(BaseModel):
    """Conversation metadata for list view."""
    id: str
    created_at: str
    title: str
    message_count: int


class Conversation(BaseModel):
    """Full conversation with all messages."""
    id: str
    created_at: str
    title: str
    messages: List[Dict[str, Any]]


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "WarRoom API"}


@app.get("/api/conversations", response_model=List[ConversationMetadata])
async def list_conversations():
    """List all conversations (metadata only)."""
    return storage.list_conversations()


@app.post("/api/conversations", response_model=Conversation)
async def create_conversation(request: CreateConversationRequest):
    """Create a new conversation."""
    conversation_id = str(uuid.uuid4())
    conversation = storage.create_conversation(conversation_id)
    return conversation


@app.get("/api/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str):
    """Get a specific conversation with all its messages."""
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete one local conversation JSON file. Run artifacts are untouched."""
    try:
        deleted = storage.delete_conversation(conversation_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"deleted": True, "conversation_id": conversation_id}


@app.post("/api/conversations/{conversation_id}/message")
async def send_message(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and run the 3-stage council process.
    Returns the complete response with all stages.
    """
    # Check if conversation exists
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    # Add user message
    storage.add_user_message(conversation_id, request.content)

    # If this is the first message, generate a title
    if is_first_message:
        title = await generate_conversation_title(request.content)
        storage.update_conversation_title(conversation_id, title)

    # Run the ask case through the inherited 3-stage council process.
    case_input = ask_case_from_message(request.content, case_id=conversation_id)
    run_id = new_run_id()
    created_at = datetime.utcnow().isoformat()
    stage1_results, stage2_results, stage3_result, metadata = await run_full_council(
        case_input.task
    )
    metadata = {
        **metadata,
        "run_id": run_id,
        "case_id": case_input.id,
        "case_type": case_input.case_type,
    }
    run_record = RunRecord(
        run_id=run_id,
        case_id=case_input.id,
        case_type=case_input.case_type,
        input=case_input,
        status="completed",
        created_at=created_at,
        completed_at=datetime.utcnow().isoformat(),
        independent_responses=stage1_results,
        peer_reviews=stage2_results,
        aggregate_rankings=metadata.get("aggregate_rankings"),
        synthesis=stage3_result,
        errors=[],
    )
    save_run_record(run_record)

    # Add assistant message with all stages
    storage.add_assistant_message(
        conversation_id,
        stage1_results,
        stage2_results,
        stage3_result,
        metadata=metadata,
        run_id=run_id,
    )

    # Return the complete response with metadata
    return {
        "stage1": stage1_results,
        "stage2": stage2_results,
        "stage3": stage3_result,
        "metadata": metadata,
        "run_id": run_id,
    }


@app.post("/api/conversations/{conversation_id}/message/stream")
async def send_message_stream(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and stream the 3-stage council process.
    Returns Server-Sent Events as each stage completes.
    """
    # Check if conversation exists
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    async def event_generator():
        run_id = new_run_id()
        case_input = ask_case_from_message(request.content, case_id=conversation_id)
        created_at = datetime.utcnow().isoformat()
        errors = []
        try:
            yield f"data: {json.dumps({'type': 'run_start', 'run_id': run_id, 'case_type': case_input.case_type})}\n\n"

            # Add user message
            storage.add_user_message(conversation_id, request.content)

            # Start title generation in parallel (don't await yet)
            title_task = None
            if is_first_message:
                title_task = asyncio.create_task(generate_conversation_title(request.content))

            # Stage 1: Collect responses
            yield f"data: {json.dumps({'type': 'stage1_start', 'run_id': run_id})}\n\n"
            stage1_results = await stage1_collect_responses(case_input.task)
            yield f"data: {json.dumps({'type': 'stage1_complete', 'run_id': run_id, 'data': stage1_results})}\n\n"

            # Stage 2: Collect rankings
            yield f"data: {json.dumps({'type': 'stage2_start', 'run_id': run_id})}\n\n"
            stage2_results, label_to_model, label_metadata = await stage2_collect_rankings(case_input.task, stage1_results)
            aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model, label_metadata)
            metadata = {
                "run_id": run_id,
                "case_id": case_input.id,
                "case_type": case_input.case_type,
                "label_to_model": label_to_model,
                "label_metadata": label_metadata,
                "aggregate_rankings": aggregate_rankings,
            }
            yield f"data: {json.dumps({'type': 'stage2_complete', 'run_id': run_id, 'data': stage2_results, 'metadata': metadata})}\n\n"

            # Stage 3: Synthesize final answer
            yield f"data: {json.dumps({'type': 'stage3_start', 'run_id': run_id})}\n\n"
            stage3_result = await stage3_synthesize_final(case_input.task, stage1_results, stage2_results)
            yield f"data: {json.dumps({'type': 'stage3_complete', 'run_id': run_id, 'data': stage3_result})}\n\n"

            # Wait for title generation if it was started
            if title_task:
                title = await title_task
                storage.update_conversation_title(conversation_id, title)
                yield f"data: {json.dumps({'type': 'title_complete', 'run_id': run_id, 'data': {'title': title}})}\n\n"

            run_record = RunRecord(
                run_id=run_id,
                case_id=case_input.id,
                case_type=case_input.case_type,
                input=case_input,
                status="completed",
                created_at=created_at,
                completed_at=datetime.utcnow().isoformat(),
                independent_responses=stage1_results,
                peer_reviews=stage2_results,
                aggregate_rankings=aggregate_rankings,
                synthesis=stage3_result,
                errors=errors,
            )
            save_run_record(run_record)

            # Save complete assistant message
            storage.add_assistant_message(
                conversation_id,
                stage1_results,
                stage2_results,
                stage3_result,
                metadata=metadata,
                run_id=run_id,
            )

            # Send completion event
            yield f"data: {json.dumps({'type': 'complete', 'run_id': run_id})}\n\n"

        except Exception as e:
            errors.append(str(e))
            run_record = RunRecord(
                run_id=run_id,
                case_id=case_input.id,
                case_type=case_input.case_type,
                input=case_input,
                status="failed",
                created_at=created_at,
                completed_at=datetime.utcnow().isoformat(),
                independent_responses=locals().get("stage1_results", []),
                peer_reviews=locals().get("stage2_results", []),
                aggregate_rankings=locals().get("aggregate_rankings"),
                synthesis=locals().get("stage3_result"),
                errors=errors,
            )
            save_run_record(run_record)
            # Send error event
            yield f"data: {json.dumps({'type': 'error', 'run_id': run_id, 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.post("/api/cases/evaluate")
async def evaluate_case(request: EvaluateCaseRequest):
    """Run an evaluate case through independent evaluators and synthesis."""
    try:
        case_input = CaseInput(
            case_type="evaluate",
            task=request.task,
            candidate_output=request.candidate_output,
            criteria=request.criteria,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    record = await run_evaluate_case(case_input)
    artifact = {
        "path": f"data/runs/{record.run_id}/run.json",
        "format": "run.json",
    }
    return {
        "run_id": record.run_id,
        "case_type": record.case_type,
        "status": record.status,
        "evaluations": record.evaluations,
        "synthesis": record.synthesis,
        "artifact": artifact,
        "errors": record.errors,
    }


@app.post("/api/cases/critique")
async def critique_case(request: CritiqueCaseRequest):
    """Run a critique case through independent critics and synthesis."""
    try:
        case_input = CaseInput(
            case_type="critique",
            task=request.task,
            candidate_output=request.candidate_output,
            artifact=request.artifact,
            criteria=request.criteria,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    record = await run_critique_case(case_input)
    artifact = {
        "path": f"data/runs/{record.run_id}/run.json",
        "format": "run.json",
    }
    return {
        "run_id": record.run_id,
        "case_type": record.case_type,
        "status": record.status,
        "critiques": record.critiques,
        "synthesis": record.synthesis,
        "artifact": artifact,
        "errors": record.errors,
    }


@app.post("/api/cases/compare")
async def compare_case(request: CompareCaseRequest):
    """Run a compare case through independent comparers and synthesis."""
    try:
        case_input = CaseInput(
            case_type="compare",
            task=request.task,
            candidates=[
                candidate.model_dump()
                if hasattr(candidate, "model_dump")
                else candidate.dict()
                for candidate in request.candidates
            ],
            criteria=request.criteria,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    record = await run_compare_case(case_input)
    artifact = {
        "path": f"data/runs/{record.run_id}/run.json",
        "format": "run.json",
    }
    return {
        "run_id": record.run_id,
        "case_type": record.case_type,
        "status": record.status,
        "comparisons": record.comparisons,
        "aggregate_rankings": record.aggregate_rankings,
        "synthesis": record.synthesis,
        "artifact": artifact,
        "errors": record.errors,
    }


@app.post("/api/cases/decide")
async def decide_case(request: DecideCaseRequest):
    """Apply deterministic rules and write decision.json."""
    if not request.source_run_id and request.evaluation_payload is None:
        raise HTTPException(
            status_code=422,
            detail="source_run_id or evaluation_payload is required",
        )
    if not request.thresholds and not request.rules:
        raise HTTPException(
            status_code=422,
            detail="thresholds or rules are required",
        )
    try:
        decision = run_decide_case(
            source_run_id=request.source_run_id,
            evaluation_payload=request.evaluation_payload,
            thresholds=request.thresholds,
            rules=request.rules,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return decision


@app.post("/api/cases/war-room")
async def war_room_case(request: WarRoomCaseRequest):
    """Run a War Room case through advisors, peer review, and verdict."""
    try:
        case_input = CaseInput(
            case_type="war_room",
            task=request.task,
            context=request.context,
            stakes=request.stakes,
            criteria=request.criteria,
            candidate_output=request.candidate_output,
            candidates=[
                candidate.model_dump()
                if hasattr(candidate, "model_dump")
                else candidate.dict()
                for candidate in request.candidates
            ],
            respondent_aliases=request.respondent_aliases,
            synthesizer_alias=request.synthesizer_alias,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    record = await run_war_room_case(case_input)
    artifact = {
        "path": f"data/runs/{record.run_id}/run.json",
        "format": "run.json",
    }
    return {
        "run_id": record.run_id,
        "case_type": record.case_type,
        "status": record.status,
        "framed_question": record.framed_question,
        "advisor_responses": record.advisor_responses,
        "peer_reviews": record.peer_reviews,
        "verdict": record.verdict,
        "synthesis": record.synthesis,
        "artifact": artifact,
        "errors": record.errors,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
