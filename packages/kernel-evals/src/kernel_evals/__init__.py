"""Evaluation primitives for Agent Kernel."""

from kernel_evals.datasets import EvalDatasetError, RagEvalDataset, load_rag_eval_dataset
from kernel_evals.models import EvalAssertionResult, EvalCaseResult, EvalReport
from kernel_evals.rag import RagEvalCase, RagEvalRunner
from kernel_evals.reporting import eval_report_to_dict

__all__ = [
    "EvalDatasetError",
    "EvalAssertionResult",
    "EvalCaseResult",
    "EvalReport",
    "RagEvalCase",
    "RagEvalDataset",
    "RagEvalRunner",
    "eval_report_to_dict",
    "load_rag_eval_dataset",
]
