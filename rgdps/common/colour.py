from __future__ import annotations
from typing import Any


class Colour:
    """An immutable representation of a colour using the RGB specturm."""

    def __init__(
            self,
            red: int,
            green: int,
            blue: int,
    ) -> None:
        self.red = clamp_rgb(red)
        self.green = clamp_rgb(green)
        self.blue = clamp_rgb(blue)

    # Immutability
    def __setattr__(self, name: str, value: Any) -> None:
        raise TypeError("`Colour` is immutable.")


    def as_hex(self) -> str:
        return "#{0:02x}{1:02x}{2:02x}".format(
           clamp_rgb(self.red),
           clamp_rgb(self.green),
           clamp_rgb(self.blue),
        )
    

    def as_format_str(self) -> str:
        return f"{self.red},{self.green},{self.blue}"
    
    @staticmethod
    def from_format_string(format_string: str) -> Colour:
        format_string = format_string.replace(", ", ",").strip()
        colour_components = format_string.split(",")

        if len(colour_components) != 3:
            raise ValueError(f"RGB colour string requires 3 values. Got {len(colour_components)}.")
        
        return Colour(
            red=int(colour_components[0]),
            green=int(colour_components[1]),
            blue=int(colour_components[2]),
        )
    
    @staticmethod
    def default() -> Colour:
        return Colour(255, 255, 255)
    
    # Pydantic Logic
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value):
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            return cls.from_format_string(value)
      
        raise ValueError(f"Invalid value for Colour: {value}")
    
    @classmethod
    def __modify_schema__(cls, field_schema: dict[str, Any]):
        field_schema.update(
            type="string",
            example="255,0,0",
        )
    
def clamp_rgb(value: int) -> int: 
    return max(0, min(value, 255))
