import inspect
from importlib import import_module
import click
from dateutil.parser import parse
import re
from datetime import datetime, timedelta


def validate_date(date_string: str) -> bool:
    """Check if date is valid"""
    pattern = "^\d{4}-\d{2}-\d{2}$"
    if re.match(pattern, date_string):
        return True
    else:
        return False
    
def generate_date_range(partial_date: str) -> list[str,str]:
    """Check date input and generate date min/max values

    Args:
        partial_date (_type_): _description_

    Raises:
        ValueError: _description_

    Returns:
        _type_: _description_
    """
    patterns = {
        'YYYY': r'^\d{4}$',
        'YYYY-MM': r'^\d{4}-\d{2}$',
        'YYYY-MM-DD': r'^\d{4}-\d{2}-\d{2}$'
    }

    # Year only
    if re.match(patterns['YYYY'], partial_date):
        min_date = f"{partial_date}-01-01"
        max_date = f"{partial_date}-12-31"
    # Year and month
    elif re.match(patterns['YYYY-MM'], partial_date):  # Format: YYYY-MM
        min_date = f"{partial_date}-01"
        max_date = f"{partial_date}-{(datetime.strptime(partial_date, '%Y-%m').month + 1) % 12 or 12:02d}-01"
        max_date = (datetime.strptime(max_date, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
    # Full date
    elif re.match(patterns['YYYY-MM-DD'], partial_date):  # Format: YYYY-MM-DD
        min_date = partial_date
        max_date = partial_date
    else:
        try:
            min_date = max_date = parse(partial_date).strftime('%Y-%m-%d %H:%M:%S')
        except:
            raise ValueError(f"Invalid date format for {partial_date}. Please use YYYY, YYYY-MM, or a valid date format.")

    return min_date, max_date


def list_parsers():
    module = import_module("api2gn.var.config.parsers")
    parsers = []
    for name, obj in inspect.getmembers(module):
        if hasattr(obj, "__module__"):
            if obj.__module__ == "api2gn.var.config.parsers" and inspect.isclass(obj):
                parsers.append(obj)
    return parsers


def get_parser(name):
    selected_parser = None
    for parser in list_parsers():
        if parser.name == name:
            selected_parser = parser
    if not selected_parser:
        click.secho(f"Cannot find parser {name}")
        return None
    module = import_module("api2gn.var.config.parsers")
    return getattr(module, selected_parser.__name__)
