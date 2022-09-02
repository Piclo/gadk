import importlib
import inspect
from abc import ABCMeta
from os import getcwd, makedirs
from os.path import exists
from typing import Generator, Optional, Type

import click
import sys

from gadk import Workflow


def output_to_file(workflow: Workflow):
    """Write the workflow to .github/workflows/{workflow.filename}.yml."""

    makedirs(".github/workflows/", exist_ok=True)
    with open(f".github/workflows/{workflow.filename}.yml", mode="w") as fd:
        fd.write(workflow.render())


def output_to_stdout(workflow: Workflow, trailing_newline: bool = False):
    click.echo(workflow.render(), nl=trailing_newline)


def find_workflows(parent: Type = Workflow) -> Generator[Workflow, None, None]:
    """
    Extract workflows from imported module.

    Typing is mostly disabled for this function because:
        1. Workflow subclasses are expected. If they are not present, `gadk` can do no work.
        2. Workflow subclasses should define a constructor with no arguments. The arguments
           exist for the programmer to name the workflow. `gadk` cannot guess these arguments.
    """
    all_workflow_classes = set()
    for workflow_class in parent.__subclasses__():
        if workflow_class in all_workflow_classes:
            continue

        all_workflow_classes.add(workflow_class)
        if not inspect.isabstract(workflow_class) and type(workflow_class) is not ABCMeta:
            yield workflow_class()

        yield from find_workflows(workflow_class)


def import_workflows():
    # Import actions.py from the current working directory.
    sys.path.insert(0, getcwd())
    importlib.import_module("actions")
    sys.path.pop(0)

    # Sort workflows for consistency.
    return sorted(find_workflows(), key=lambda w: w.name)


def fetch_actual_workflow_contents(workflow_name: str) -> Optional[str]:
    workflow_path = f".github/workflows/{workflow_name}.yml"
    if not exists(workflow_path):
        return None
    else:
        with open(f".github/workflows/{workflow_name}.yml") as fd:
            return fd.read()


def _sync(print_to_stdout: bool):
    # Assume actions.py imports all elements of gadk to get subclasses of Workflow.
    workflows = import_workflows()
    workflow_count = len(workflows)
    for i, workflow in enumerate(workflows, start=1):
        if print_to_stdout:
            output_to_stdout(workflow, trailing_newline=i < workflow_count)
        else:
            output_to_file(workflow)

@click.group(
    invoke_without_command=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.pass_context
@click.option(
    "--print/--no-print",
    default=False,
    help="Print workflow YAML to stdout. By default each workflow is written to .github/workflows/.",
)
@click.version_option()
def cmd(ctx: click.Context, print: bool = False):
    """Generate Github Actions workflows from code."""
    if ctx.invoked_subcommand is None:
        _sync(print)


@cmd.command()
@click.option(
    "--print/--no-print",
    default=False,
    help="Print workflow YAML to stdout. By default each workflow is written to .github/workflows/.",
)
def sync(print: bool):
    """Generate Github Actions workflows from code."""
    _sync(print)


@cmd.command()
def check():
    """Check if generated workflow files are up to date."""
    success = True
    for workflow in import_workflows():
        actual_content = fetch_actual_workflow_contents(workflow.filename)
        if actual_content is None or actual_content != workflow.render():
            click.echo(
                click.style(f"Workflow {workflow.filename} is outdated!", fg="red")
            )
            success = False
        else:
            click.echo(f"Workflow {workflow.filename} is up to date.")

    if not success:
        raise click.exceptions.ClickException(
            "Some workflows are outdated. Please run gadk to sync workflows."
        )


if __name__ == "__main__":
    cmd()
