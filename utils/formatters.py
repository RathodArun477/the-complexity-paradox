"""Formatting utilities for game development data."""

import math
from typing import Union, Optional

Number = Union[int, float]

# Null Handling

def safe_value(value: Optional[Number], fallback: str = "—") -> str:
    """Convert None/NaN/null to display string"""
    if value is None:
        return fallback
    if isinstance(value,float) and math.isnan(value):
        return fallback
    return str(value)

def safe_number(value: Optional[Number], fallback: str="—") -> Union[str,Number]:
    """Return number if valid, otherwise fallback string."""
    if value is None:
        return fallback
    if isinstance(value,float) and math.isnan(value):
        return fallback
    return value

# Time Conversions

def format_months(months: Optional[Number], fallback: str="—") -> str:
    """Full text: '4 years 4 months'"""
    val = safe_number(months,fallback)
    if isinstance(val,str):
        return val
    
    months = int(val)
    years = months // 12
    remaining = months % 12

    if years == 0:
        return f"{remaining} months{'s' if remaining != 1 else ''}"
    if remaining == 0:
        return f"{years} year{'s' if years != 1 else ''}"
    return f"{years} year{'s' if years != 1 else ''} {remaining} months{'s' if remaining != 1 else ''}"

def format_months_short(months: Optional[Number], fallback: str="—") -> str:
    """Short: '4y 4mo' """
    val = safe_number(months,fallback)
    if isinstance(val,str):
        return val
    
    months = int(val)
    years = months // 12
    remaining = months % 12

    if years == 0:
        return f"{remaining}mo"
    if remaining == 0:
        return f"{years}y"
    return f"{years}y {remaining}mo"

# File Size Conversions

def format_file_size(mb: Optional[Number], fallback: str="-") -> str:
    """< 1024 MB -> '500 MB'. >= 1024 MB -> '145.48 GB' (2 decimals)"""
    val = safe_number(mb, fallback)
    if isinstance(val,str):
        return val
    
    if val < 1024:
        #Whole number, no decimals
        return f"{int(val)} MB"
    
    gb = val / 1024
    return f"{gb:.2f} GB"

# Budget Formatting

def format_budget(usd: Optional[Number], fallback: str = "—") -> str:
    """≥ $1M → '$45M', '$2.5M'. < $1M → '$500,000', '$900'."""
    val = safe_number(usd, fallback)
    if isinstance(val, str):
        return val
    
    if val >= 1_000_000_000:
        billions = val / 1_000_000_000
        return f"${billions:.1f}B".replace(".0B", "B")
    
    if val >= 1_000_000:
        millions = val / 1_000_000
        return f"${millions:.1f}M".replace(".0M", "M")
    
    if val >= 1_000:
        return f"${val:,.0f}"
    
    return f"${val:,.0f}"

# Score & Team Size

def format_score(score: Optional[Number], fallback: str = "—") -> str:
    """Plain integer, no decimals."""
    val = safe_number(score, fallback)
    if isinstance(val, str):
        return val
    return f"{int(val)}"


def format_team_size(size: Optional[Number], fallback: str = "—") -> str:
    """Plain integer, no decimals."""
    val = safe_number(size, fallback)
    if isinstance(val, str):
        return val
    return f"{int(val)}"


# ---------- Jinja Registration ----------

def register_filters(app):
    """Register all formatters as Jinja2 filters."""
    app.jinja_env.filters['format_months'] = format_months
    app.jinja_env.filters['format_months_short'] = format_months_short
    app.jinja_env.filters['format_file_size'] = format_file_size
    app.jinja_env.filters['format_budget'] = format_budget
    app.jinja_env.filters['format_score'] = format_score
    app.jinja_env.filters['format_team_size'] = format_team_size
    app.jinja_env.filters['safe_value'] = safe_value