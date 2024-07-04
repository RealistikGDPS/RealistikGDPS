from __future__ import annotations

from typing import NamedTuple

from pydantic import BaseModel
from pydantic import ConfigDict

from rgdps.common.colour import Colour


class DatabaseModel(BaseModel):
    """An expansion of Pydantic's `BaseModel` froviding extended functionality
    for RealistikGDPS."""

    model_config = ConfigDict(json_encoders={
        Colour: lambda c: c.as_format_str(),
    })


class SearchResults[T](NamedTuple):
    results: list[T]
    total: int
    page_size: int
