# -*- coding: utf-8 -*-
"""
Module containing command line interface to financeager backend.
"""
from __future__ import unicode_literals, print_function

import argparse
import traceback
import os

from financeager import offline, communication, CONFIG_DIR
from .entries import CategoryEntry
from .model import Model
from .config import Configuration

if not os.path.isdir(CONFIG_DIR):
    os.makedirs(CONFIG_DIR)


def get_option(section, option=None):
    """Get an option of the financeager configuration or a dictionary of section
    contents if no option given.
    """
    config_filepath = os.path.join(CONFIG_DIR, "config")
    _config = Configuration(filepath=config_filepath)

    if option is None:
        return dict(_config._parser.items(section))
    else:
        return _config.get(section, option)


def main(**kwargs):
    """Main entry point of the application. If used from the command line, all
    arguments and options are parsed and passed.
    On the other hand this method can be used in scripts. Kwargs have to be
    passed analogously to what the command line interface would accept (consult
    the help via `financeager [command] --help`), e.g. `{"command": "add",
    "name": "champagne", "value": "99"}.
    """

    cl_kwargs = kwargs or _parse_command()

    command = cl_kwargs.pop("command")
    backend_name = get_option("SERVICE", "name")
    communication_module = communication.module(backend_name)

    if command == "start":
        if cl_kwargs.get("host") is None:
            cl_kwargs["host"] = get_option("SERVICE:FLASK", "host")
        communication_module.launch_server(**cl_kwargs)
        return

    if backend_name == "flask":
        cl_kwargs["http_config"] = get_option("SERVICE:FLASK")

    proxy = communication_module.proxy()
    try:
        print(communication.run(
            proxy, command,
            default_category=get_option("FRONTEND", "default_category"),
            date_format=get_option("FRONTEND", "date_format"),
            **cl_kwargs))
        if offline.recover(proxy):
            print("Recovered offline backup.")
    except offline.OfflineRecoveryError:
        print("Offline backup recovery failed!")
    except communication.PreprocessingError as e:
        print(e)
    except (communication_module.CommunicationError) as e:
        print("Error running command '{}':\n{}".format(
            command, traceback.format_exc()))
        if offline.add(command, **cl_kwargs):
            print("Stored '{}' request in offline backup.".format(command))


def _parse_command(args=None):
    """Parse the given list of args and return the result as dict."""

    parser = argparse.ArgumentParser()

    period_args = ("-p", "--period")
    period_kwargs = dict(default=None, help="name of period to modify or query")

    subparsers = parser.add_subparsers(title="subcommands", dest="command",
            help="list of available subcommands")

    add_parser = subparsers.add_parser("add",
            help="add an entry to the database")

    add_parser.add_argument("name", help="entry name")
    add_parser.add_argument("value", type=float, help="entry value")
    add_parser.add_argument("-c", "--category", default=None,
            help="entry category")
    add_parser.add_argument("-d", "--date", default=None, help="entry date")

    add_parser.add_argument("-t", "--table-name", default=None,
            help="""table to add the entry to. With 'recurrent', specify at
least a frequency, start date and end date are optional. Default:
'standard'""")
    add_parser.add_argument("-f", "--frequency", help="frequency of recurrent "
            "entry; one of yearly, half-yearly, quarterly, monthly, weekly, "
            "daily.")
    add_parser.add_argument("-s", "--start", default=None,
            help="start date of recurrent entry")
    add_parser.add_argument("-e", "--end", default=None,
            help="end date of recurrent entry")

    add_parser.add_argument(*period_args, **period_kwargs)

    start_parser = subparsers.add_parser("start", help="start period server")
    start_parser.add_argument("-d", "--debug", action="store_true",
            help="start webservice in debug mode")
    start_parser.add_argument("-i", "--host-ip", default=None, dest="host",
            help="IP address and port of server, format 'XXX.XXX.XXX.XXX:port'")

    get_parser = subparsers.add_parser("get",
            help="show information about single entry")
    get_parser.add_argument("eid", help="entry ID")
    get_parser.add_argument("-t", "--table-name", default=None,
            help="Table to get the entry from. Default: 'standard'.")
    get_parser.add_argument(*period_args, **period_kwargs)

    rm_parser = subparsers.add_parser("rm",
            help="remove an entry from the database")
    rm_parser.add_argument("eid", help="entry ID")
    rm_parser.add_argument("-t", "--table-name", default=None,
            help="Table to remove the entry from. Default: 'standard'.")
    rm_parser.add_argument(*period_args, **period_kwargs)

    update_parser = subparsers.add_parser("update",
            help="update one or more fields of an database entry")
    update_parser.add_argument("eid", type=int, help="entry ID")
    update_parser.add_argument("-t", "--table-name",
            help="Table containing the entry. Default: 'standard'")
    update_parser.add_argument("-n", "--name", help="new name")
    update_parser.add_argument("-v", "--value", type=float, help="new value")
    update_parser.add_argument("-c", "--category", help="new category")
    update_parser.add_argument("-d", "--date",
            help="new date (for standard entries only)")
    update_parser.add_argument("-f", "--frequency",
            help="new frequency (for recurrent entries only)")
    update_parser.add_argument("-s", "--start",
            help="new start date (for recurrent entries only)")
    update_parser.add_argument("-e", "--end",
            help="new end date (for recurrent entries only)")
    update_parser.add_argument(*period_args, **period_kwargs)

    copy_parser = subparsers.add_parser("copy",
            help="copy an entry from one period to another")
    copy_parser.add_argument("eid", help="entry ID")
    copy_parser.add_argument(
        "-s", "--source", default=None, dest="source_period",
        help="period to copy the entry from")
    copy_parser.add_argument(
        "-d", "--destination", default=None, dest="destination_period",
        help="period to copy the entry to")
    copy_parser.add_argument("-t", "--table-name", default=None,
            help="Table to copy the entry from/to. Default: 'standard'.")

    print_parser = subparsers.add_parser("print",
            help="show the period database")
    print_parser.add_argument(
        "-f", "--filters", default=None, nargs="+", help="filter for name, "
        "date and/or category substring, e.g. name=beer category=groceries")
    print_parser.add_argument("-s", "--stacked-layout", action="store_true",
            help="if true, display earnings and expenses in stacked layout, "
                              "otherwise side-by-side")
    print_parser.add_argument("--entry-sort",
                              choices=["name", "value", "date", "eid"],
                              default=CategoryEntry.BASE_ENTRY_SORT_KEY)
    print_parser.add_argument("--category-sort",
                              choices=["name", "value"],
                              default=Model.CATEGORY_ENTRY_SORT_KEY)
    print_parser.add_argument(*period_args, **period_kwargs)

    subparsers.add_parser("list", help="list all databases")

    return vars(parser.parse_args(args=args))


if __name__ == "__main__":
    main()
