"""
Fine-tuning support for Tastyz Bakery.

Collects high-quality Q&A pairs from the Feedback model,
formats them as OpenAI fine-tuning JSONL, and manages fine-tune jobs.
"""

import json
import logging
import tempfile
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from .models import Feedback, FineTuneJob

logger = logging.getLogger(__name__)

# Minimum number of training examples required by OpenAI
MIN_TRAINING_EXAMPLES = 10


def collect_training_data(min_rating: int = 4, limit: int = 500) -> list[dict]:
    """
    Collect high-quality Q&A pairs from the feedback table.

    Returns list of OpenAI chat fine-tuning format dicts:
    [{"messages": [{"role": "system", ...}, {"role": "user", ...}, {"role": "assistant", ...}]}]
    """
    feedbacks = Feedback.objects.filter(rating__gte=min_rating).order_by("-created_at")[:limit]

    training_data = []
    for fb in feedbacks:
        training_data.append(
            {
                "messages": [
                    {
                        "role": "system",
                        "content": "You are Tastyz AI, a friendly and knowledgeable bakery assistant for Tastyz Bakery in Kampala, Uganda.",
                    },
                    {"role": "user", "content": fb.query},
                    {"role": "assistant", "content": fb.response},
                ]
            }
        )

    logger.info("Collected %d training examples (min_rating=%d)", len(training_data), min_rating)
    return training_data


def export_training_jsonl(training_data: list[dict], output_path: str = "") -> str:
    """
    Write training data to a JSONL file.
    Returns the file path.
    """
    if not output_path:
        output_path = str(Path(settings.BASE_DIR) / "fine_tune_training.jsonl")

    with open(output_path, "w", encoding="utf-8") as f:
        for example in training_data:
            f.write(json.dumps(example) + "\n")

    logger.info("Exported %d examples to %s", len(training_data), output_path)
    return output_path


def submit_fine_tune_job(base_model: str = "gpt-4o-mini-2024-07-18") -> FineTuneJob:
    """
    Collect data, upload to OpenAI, and submit a fine-tuning job.
    """
    import openai

    training_data = collect_training_data()
    if len(training_data) < MIN_TRAINING_EXAMPLES:
        raise ValueError(
            f"Need at least {MIN_TRAINING_EXAMPLES} high-quality examples, "
            f"but only have {len(training_data)}. Get more 4-5★ feedback first."
        )

    # Export to temp file
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8")
    for row in training_data:
        tmp.write(json.dumps(row) + "\n")
    tmp.close()

    client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

    # Upload training file
    with open(tmp.name, "rb") as f:
        upload_resp = client.files.create(file=f, purpose="fine-tune")

    # Create fine-tuning job
    job_resp = client.fine_tuning.jobs.create(
        training_file=upload_resp.id,
        model=base_model,
    )

    # Record in DB
    job = FineTuneJob.objects.create(
        openai_job_id=job_resp.id,
        base_model=base_model,
        training_file_id=upload_resp.id,
        num_examples=len(training_data),
        status=FineTuneJob.Status.RUNNING,
    )
    logger.info(
        "Fine-tune job submitted: %s (base=%s, examples=%d)",
        job_resp.id,
        base_model,
        len(training_data),
    )
    return job


def check_fine_tune_status(job: FineTuneJob) -> FineTuneJob:
    """Check and update the status of a fine-tune job."""
    if not job.openai_job_id:
        return job

    import openai

    client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    resp = client.fine_tuning.jobs.retrieve(job.openai_job_id)

    job.status = resp.status
    if resp.status == "succeeded":
        job.fine_tuned_model = resp.fine_tuned_model or ""
        job.completed_at = timezone.now()
    elif resp.status == "failed":
        job.error_message = str(getattr(resp, "error", "Unknown error"))
        job.completed_at = timezone.now()
    job.save()

    logger.info("Fine-tune job %s status: %s", job.openai_job_id, resp.status)
    return job


def get_fine_tune_stats() -> dict:
    """Return summary statistics for the fine-tune dashboard."""
    jobs = FineTuneJob.objects.all()
    return {
        "total_jobs": jobs.count(),
        "running": jobs.filter(status="running").count(),
        "succeeded": jobs.filter(status="succeeded").count(),
        "failed": jobs.filter(status="failed").count(),
        "total_examples": sum(jobs.values_list("num_examples", flat=True)),
        "available_training_data": Feedback.objects.filter(rating__gte=4).count(),
    }
