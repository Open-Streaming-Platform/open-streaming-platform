#!/usr/bin/env python3
"""
jinja2-render-json
Fork of jinja2-render (https://github.com/pklaus/jinja2-render)

Tool for Rendering Jinja2 from JSON Input
"""


def main():
    import argparse, sys, os, subprocess, json

    ## Command Line Argument Parsing
    parser = argparse.ArgumentParser(
        description="Render a Jinja2 template from the command line.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-c",
        dest="contexts",
        default="{}",
        help="JSON Dict containing values",
    )
    parser.add_argument(
        "-f",
        default="Dockerfile.jinja2",
        dest="template",
        help="The Jinja2 template to use.",
    )
    parser.add_argument(
        "-o",
        default="Dockerfile",
        dest="output",
        help="The output file to write to.",
    )

    try:
        import jinja2
    except ImportError:
        parser.error("Python package jinja2 is missing.")

    args = parser.parse_args()

    if sys.version_info[0:3] < (3, 6):
        parser.error("Minimum Python version is 3.6 - Exiting.")

    import importlib.util

    try:
        contexts_raw = args.contexts
    except FileNotFoundError:
        parser.error("Cannot find JSON Data")
        contexts_raw = "{}"

    CONTEXTS = json.loads(contexts_raw)

    loader = jinja2.FileSystemLoader(".")
    j2_env = jinja2.Environment(loader=loader, trim_blocks=True, lstrip_blocks=True)
    template = j2_env.get_template(args.template)

    with open(args.output, "wt") as f:
        f.write(template.render(**CONTEXTS))


if __name__ == "__main__":
    main()
