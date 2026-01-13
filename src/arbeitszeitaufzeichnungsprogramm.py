from datetime import date
import holidays
import os
import pandas as pd
import argparse
import sys
from pathlib import Path
import calendar
import tomllib
from typing import Dict, Any


def load_config(config_path: Path) -> Dict[str, Any]:
    """
    Load configuration from TOML file, falling back to defaults.

    :param config_path: Path to config.toml file
    :return: Configuration dictionary
    """
    # Load config file if found
    try:
        with open(config_path, 'rb') as f:
            loaded_config = tomllib.load(f)
    except Exception as e:
        raise RuntimeError(f"Failed to load configuration from '{config_path}': {e}")

    # Convert data_path to absolute if it's relative (relative to config file)
    if 'general' in loaded_config and 'data_path' in loaded_config['general']:
        data_path = Path(loaded_config['general']['data_path'])
        if not data_path.is_absolute():
            # Make it relative to the config file's directory
            config_dir = Path(config_path).parent
            loaded_config['general']['data_path'] = config_dir / data_path

    return loaded_config


def dummy_df() -> pd.DataFrame:
    """
    Define columns and their data types
    :return: Empty DataFrame with specified columns and dtypes
    """
    column_spec = {
        'Date': 'str',
        'Is Holiday': 'str',
        'Start Time': 'str',
        'End Time': 'str',
        'Break Time': 'str',
        'Vacation': 'str',
        'Sick Leave': 'str',
        'Notes': 'str'
    }

    return pd.DataFrame(columns=list(column_spec.keys())).astype(column_spec)


def get_filename(date_arg: date, path: Path) -> Path:
    """
    Get the filename for the CSV file based on the date.

    :param date_arg: Date object representing the month and year for which to create the schedule
    :param path: Path to the directory where the CSV file will be saved
    :return: Filename as a string
    """
    return Path(path) / f'schedule_{date_arg.year}-{date_arg.month:02d}.csv'


def create_csv(date_arg: date, _: None, path: Path):
    """
    Create a CSV file with the columns specified in dummy_df.
    The name of the file will be schedule_YYYY-MM.csv.
    
    :param date_arg: Date object representing the month and year for which to create the schedule
    :param _: Dummy parameter to match function signature
    :param path: Path to the directory where the CSV file will be saved
    :return:
    """""

    holidays_here = holidays.country_holidays(config['holidays']['country'], subdiv=config['holidays']['subdivision'],
                                              years=date_arg.year)
    # Create path if it doesn't exist
    path.mkdir(parents=True, exist_ok=True)
    # Assuming the year is the current year
    filename = get_filename(date_arg, path)

    # Check if file already exists
    if os.path.exists(filename):
        raise FileExistsError(f"The file '{filename}' already exists!")

    # Get the number of days in the month
    _, num_days = calendar.monthrange(date_arg.year, date_arg.month)

    # Build all rows at once (more efficient than repeated concat)
    rows = []
    for day in range(1, num_days + 1):
        current_date = date(date_arg.year, date_arg.month, day)
        rows.append({
            'Date': current_date.strftime('%Y-%m-%d'),
            'Is Holiday': str(current_date in holidays_here),
            'Notes': holidays_here.get(current_date, '')
        })

    df = pd.DataFrame(rows, columns=dummy_df().columns)
    df.to_csv(filename, index=False)


def update_field(date_arg: date, column: str, value: Any, filename: Path):
    """
    Update a specific field in the CSV file for a given date.
    :param date_arg: Date object
    :param column: Column name to update
    :param value: New value to set
    :param filename: Path to the CSV file
    :return:
    """

    if not os.path.exists(filename):
        path = Path(os.path.dirname(filename))
        create_csv(date_arg, None, path=path)

    # parse the CSV file with types from dummy_df
    df_month = pd.read_csv(filename, dtype=dummy_df().dtypes.to_dict(), skipinitialspace=True)
    # Update the start time for the given date
    df_month.loc[df_month['Date'] == date_arg.strftime('%Y-%m-%d'), column] = value
    df_month.to_csv(filename, index=False)


def log_start_time(date_arg: date, start_time: str, path: Path):
    """
    Log the start time for a given date in the CSV file.
    :param date_arg: Date object
    :param start_time: Start time as a string
    :param path: Path to the directory containing the CSV file
    :return:
    """
    try:
        time = pd.to_datetime(start_time, format='%H:%M')
    except ValueError:
        raise ValueError(f"Invalid time format '{start_time}'. Expected HH:MM format (e.g., 09:00)")
    update_field(date_arg, 'Start Time', time.strftime('%H:%M'), get_filename(date_arg, path))


def log_end_time(date_arg: date, end_time: str, path: Path):
    """
    Log the end time for a given date in the CSV file.
    :param date_arg: Date object
    :param end_time: End time as a string
    :param path: Path to the directory containing the CSV file
    :return:
    """
    try:
        time = pd.to_datetime(end_time, format='%H:%M')
    except ValueError:
        raise ValueError(f"Invalid time format '{end_time}'. Expected HH:MM format (e.g., 17:00)")
    update_field(date_arg, 'End Time', time.strftime('%H:%M'), get_filename(date_arg, path))


def log_break_time(date_arg: date, break_time: str, path: Path):
    """
    Log the break time for a given date in the CSV file.
    :param date_arg: Date object
    :param break_time: Break time as an integer (minutes) or string in %H:%M format
    :param path: Path to the directory containing the CSV file
    :return:
    """
    try:
        # Check if break_time is a string that can be parsed as an integer (minutes)
        if ':' not in break_time:
            # Convert minutes to HH:MM format
            break_time_int = int(break_time)
            if break_time_int < 0:
                raise ValueError("Break time cannot be negative")
            hours = break_time_int // 60
            minutes = break_time_int % 60
            formatted_time = f'{hours:02d}:{minutes:02d}'
        else:
            # Parse as time string in H:MM or HH:MM format
            time = pd.to_datetime(break_time, format='%H:%M')
            formatted_time = time.strftime('%H:%M')
    except ValueError as e:
        if "cannot be negative" in str(e):
            raise
        raise ValueError(
            f"Invalid break time format '{break_time}'. Expected minutes (e.g., 60) or HH:MM format (e.g., 01:00)")

    update_field(date_arg, 'Break Time', formatted_time, get_filename(date_arg, path))


def log_vacation(date_arg: date, vacation: float, path: Path):
    """
    Log vacation for a given date in the CSV file.
    :param date_arg: Date object
    :param vacation: float representing full or half day vacation (1.0 or 0.5)
    :param path: Path to the directory containing the CSV file
    :return:
    """
    # Ensure vacation is either 1.0 or 0.5
    if vacation not in [0.5, 1.0]:
        raise ValueError("Vacation must be either 0.5 (half day) or 1.0 (full day).")
    update_field(date_arg, 'Vacation', vacation, get_filename(date_arg, path))


def log_sick_leave(date_arg: date, sick_leave: float, path: Path):
    """
    Log sick leave for a given date in the CSV file.
    :param date_arg: Date object
    :param sick_leave: float representing full or half day sick leave (1.0 or 0.5)
    :param path: Path to the directory containing the CSV file
    :return:
    """
    # Ensure sick_leave is either 1.0 or 0.5
    if sick_leave not in [0.5, 1.0]:
        raise ValueError("Sick leave must be either 0.5 (half day) or 1.0 (full day).")
    update_field(date_arg, 'Sick Leave', sick_leave, get_filename(date_arg, path))


def show_csv(date_arg: date, days: int, path: Path):
    """
    Print the contents of the CSV file for the given month.
    :param date_arg: Date object
    :param path: Path to the directory containing the CSV file
    :param days: Number of days to show (shows 'days' entries ending at base_day)
    :return:
    """
    filename = get_filename(date_arg, path)

    # Configure pandas display options to show all columns
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    pd.set_option('display.max_colwidth', None)

    df_month = pd.read_csv(filename, dtype=dummy_df().dtypes.to_dict(), skipinitialspace=True).fillna(
        config['display']['nan_replacement'])

    if days is None:
        print(df_month.to_string(index=False))
    else:
        end_idx = min(len(df_month), date_arg.day)
        start_idx = max(0, end_idx - days)
        print(df_month.iloc[start_idx:end_idx].to_string(index=False))


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.
    :return: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description='Work time tracking program',
        prog='Arbeitszeitaufzeichnungsprogramm'
    )

    # Add subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Start time command
    start_parser = subparsers.add_parser('start', help='Log start time')
    start_parser.add_argument('time', help='Start time in HH:MM format')

    # End time command
    end_parser = subparsers.add_parser('end', help='Log end time')
    end_parser.add_argument('time', help='End time in HH:MM format')

    # Break time command
    break_parser = subparsers.add_parser('break', help='Log break time')
    break_parser.add_argument('time', help='Break time in minutes or HH:MM format')

    # Vacation command
    vacation_parser = subparsers.add_parser('vacation', help='Log vacation')
    vacation_parser.add_argument('time', type=float, choices=[0.5, 1.0], help='Vacation time: 0.5 or 1.0 days')

    # Sick leave command
    sick_parser = subparsers.add_parser('sick', help='Log sick leave')
    sick_parser.add_argument('time', type=float, choices=[0.5, 1.0], help='Sick leave time: 0.5 or 1.0 days')

    # Print/show command
    show_parser = subparsers.add_parser('show', help='Show schedule')
    show_parser.add_argument('time', type=int, help='Number of days to show', default=None)

    # Create command
    create_parser = subparsers.add_parser('create', help='Create a new schedule CSV file')

    # Common arguments for all subcommands
    # Default config path relative to main.py location
    repo_root = Path(__file__).parent.parent

    for sub in subparsers.choices.values():
        sub.add_argument('--date', help='Date in YYYY-MM-DD format (default: today)', default=None)
        sub.add_argument('--config', help='Path to config file', default=repo_root / 'config.toml')

    args = parser.parse_args()

    # If no command provided, show help
    if not args.command:
        parser.print_help()
        sys.exit(1)

    return args


config = {}


def main():
    """
    Main function to handle command-line arguments.
    """

    args = parse_args()
    global config
    config = load_config(args.config)

    # Parse date if provided, otherwise use today
    work_date = date.fromisoformat(args.date) if args.date else date.today()
    arg_time = getattr(args, 'time', None)

    # lambda to print the last N days (from config)
    show_prev_days = lambda: show_csv(work_date,
                                      days=config['general']['show_days_after_log'],
                                      path=config['general']['data_path'],
                                      )

    # Execute the appropriate command
    # Dict mapping commands to functions and strings for printing
    command_map = {
        'start': (log_start_time, f"Logged start time {arg_time} for {work_date}"),
        'end': (log_end_time, f"Logged end time {arg_time} for {work_date}"),
        'break': (log_break_time, f"Logged break time {arg_time} for {work_date}"),
        'vacation': (log_vacation, f"Logged {arg_time} day vacation for {work_date}"),
        'sick': (log_sick_leave, f"Logged {arg_time} day sick leave for {work_date}"),
        'show': (show_csv, ''),
        'create': (create_csv, f"Created schedule for {work_date.year}-{work_date.month:02d}"),
    }

    try:
        fun, msg = command_map[args.command]
        fun(work_date, arg_time, path=config['general']['data_path'])
        if args.command not in ['show', 'create']:
            show_prev_days()
        if msg:
            print(f"\n{msg}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
