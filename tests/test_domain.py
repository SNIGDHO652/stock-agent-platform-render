"""Validation tests for public request models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.domain import AnalysisRequest


def test_request_normalizes_name_and_horizons() -> None:
    request = AnalysisRequest(
        company_name="  Microsoft   Corporation ",
        horizons=[60, 5, 20, 5],
    )
    assert request.company_name == "Microsoft Corporation"
    assert request.horizons == [5, 20, 60]


def test_request_rejects_invalid_horizon() -> None:
    with pytest.raises(ValidationError):
        AnalysisRequest(company_name="Example", horizons=[0, 300])
