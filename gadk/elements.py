from abc import abstractmethod, ABC
from typing import Any, Dict, Optional, Iterable, List, Union

from .constants import *


class Yamlable(ABC):
    @abstractmethod
    def to_yaml(self) -> Any:
        """Return a representation of the object that can be rendered as YAML."""


class Null(Yamlable):
    def to_yaml(self) -> None:
        return None


class Expression(Yamlable):
    def __init__(self, expr: str) -> None:
        super().__init__()
        self._expr = expr

    def to_yaml(self) -> Any:
        return "${{ %s }}" % self._expr


EnvVars = Dict[str, Union[Any, Expression]]


class On(Yamlable):
    def __init__(
        self,
        paths: Optional[Iterable[str]] = None,
        branches: Optional[Iterable[str]] = None,
    ) -> None:
        super().__init__()
        self._paths = paths or []
        self._branches = branches or []

    def to_yaml(self) -> Any:
        on = {}
        if self._branches:
            on["branches"] = list(self._branches)
        if self._paths:
            on["paths"] = list(self._paths)
        return on


class Step(Yamlable, ABC):
    def __init__(
        self,
        *,
        name: Optional[str] = None,
        step_id: Optional[str] = None,
        condition: str = "",
        env: Optional[Dict[str, str]] = None,
    ) -> None:
        super().__init__()
        self._name: Optional[str] = name
        self._id: Optional[str] = step_id
        self._env: Dict[str, str] = env or {}
        self._if: str = condition or ""
        # TODO: add later
        # self._id
        # self._continue_on_error
        # self._timeout_in_minutes

    def __repr__(self):
        slug = (
            f"{self._id=}" if self._id is not None
            else f"{self._name=}" if self._name is not None
            else '(unnamed)'
        )
        return f"<{type(self).__name__} {slug}>"

    def to_yaml(self) -> Any:
        step = {}
        if self._name:
            step["name"] = self._name
        if self._id is not None:
            step["id"] = self._id
        if self._if:
            step["if"] = self._if
        step = self.step_extension(step)
        if self._env:
            from .utils import env_vars_to_yaml

            step["env"] = env_vars_to_yaml(self._env)
        return step

    @abstractmethod
    def step_extension(self, step: Dict) -> Dict:
        pass


class RunStep(Step):
    def __init__(self, cmd: str, workdir: Optional[str] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cmd: str = cmd
        self._workdir: Optional[str] = workdir

    def __repr__(self):
        slug = (
            f"{self._id=}" if self._id is not None
            else f"{self._name=}" if self._name is not None
            else f"{self._cmd=}"
        )
        return f"<{type(self).__name__} {slug}>"

    def step_extension(self, step: Dict) -> Dict:
        step["run"] = self._cmd
        if self._workdir is not None:
            step["working-directory"] = self._workdir

        return step


class UsesStep(Step):
    def __init__(
        self,
        action: str,
        with_args: Optional[Dict] = None,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._action = action
        self._with: Dict[str, str] = with_args or {}

    def __repr__(self):
        slug = (
            f"id={self._id!r}" if self._id is not None
            else f"name={self._name!r}" if self._name is not None
            else f"action={self._action!r}"
        )
        return f"<{type(self).__name__} {slug}>"

    def with_args(self, **kwargs):
        self._with = kwargs

    def step_extension(self, step: Dict) -> Dict:
        step["uses"] = self._action
        if self._with:
            step["with"] = self._with
        return step


class Artifact:
    """Abstraction for the download- and upload-artifact actions."""

    def __init__(self, *, name: str, path: str) -> None:
        super().__init__()
        self._name: str = name
        self.path: str = path

    def as_upload(self) -> UsesStep:
        return UsesStep(
            action=ACTION_UPLOAD, with_args={"name": self._name, "path": self.path}
        )

    def as_download(self) -> UsesStep:
        return UsesStep(
            action=ACTION_DOWNLOAD, with_args={"name": self._name, "path": self.path}
        )


class Job(Yamlable):
    def __init__(
        self,
        *,
        condition: str = "",
        runs_on: str = "ubuntu-latest",
        steps: Optional[List[Step]] = None,
        needs: Optional[Union[List[str], str]] = None,
        outputs: Dict[str, Union[str, Expression]] = None,
        env: Optional[EnvVars] = None,
        default_checkout: bool = True,
    ) -> None:
        super().__init__()
        self._if: str = condition or ""
        self._runs_on: str = runs_on
        self._steps: List[Step] = steps or []
        self._needs: Union[List[str], str] = needs or []
        self._outputs: Dict[str, Union[str, Expression]] = outputs
        self._env: EnvVars = env or {}
        if default_checkout:
            self._steps.insert(0, UsesStep(action=ACTION_CHECKOUT))

    def __repr__(self):
        return f"<{type(self).__name__} {self._steps=}>"

    def add_step(self, step: Step):
        self._steps.append(step)

    def to_yaml(self) -> Any:
        job: Dict[str, Any] = {}
        if self._if:
            job["if"] = self._if
        if self._needs:
            job["needs"] = self._needs
        job["runs-on"] = self._runs_on
        if self._outputs is not None:
            job["outputs"] = {
                output: value.to_yaml() if isinstance(value, Yamlable) else value
                for output, value in self._outputs.items()
            }
        if self._env:
            from .utils import env_vars_to_yaml

            job["env"] = env_vars_to_yaml(self._env)
        if self._steps:
            job["steps"] = [step.to_yaml() for step in self._steps]
        return job


class Workflow(Yamlable):
    def __init__(
            self,
            filename: str,
            name: Optional[str] = None,
            *,
            concurrency_group: Optional[str] = None,
            cancel_in_progress: Optional[Union[bool, str, Expression]] = None,
    ) -> None:
        if cancel_in_progress is not None and concurrency_group is None:
            raise ValueError(
                "cancel_in_progress requires a concurrency_group to be set"
            )

        super().__init__()
        self.filename: str = filename
        self.name: Optional[str] = name
        self.concurrency_group: Optional[str] = concurrency_group
        self.cancel_in_progress: Optional[Union[bool, str, Expression]] = cancel_in_progress
        self._on: Dict[str, Union[On, Null]] = {}
        self.jobs: Dict[str, Job] = {}

    def __repr__(self):
        repr_ = f"<{type(self).__name__}"
        if self.name is not None:
            repr_ = f"{repr_} {self.name=}"

        return f"{repr_} {self.filename=}>"

    def on(
        self,
        pull_request: Optional[On] = None,
        push: Optional[On] = None,
        workflow_dispatch: Optional[Null] = None,
    ):
        if pull_request:
            self._on["pull_request"] = pull_request
        elif "pull_request" in self._on:
            del self._on["pull_request"]
        if push:
            self._on["push"] = push
        elif "push" in self._on:
            del self._on["push"]
        if workflow_dispatch:
            self._on["workflow_dispatch"] = workflow_dispatch
        elif "workflow_dispatch" in self._on:
            del self._on["workflow_dispatch"]

    def to_yaml(self) -> Any:
        workflow: Dict[str, Any] = {}
        if self.name:
            workflow["name"] = self.name
        if self.concurrency_group:
            if self.cancel_in_progress is None:
                workflow["concurrency"] = self.concurrency_group
            else:
                workflow["concurrency"] = {
                    "group": self.concurrency_group,
                    "cancel-in-progress":
                        self.cancel_in_progress.to_yaml()
                        if isinstance(self.cancel_in_progress, Yamlable)
                        else self.cancel_in_progress,
                }
        workflow["on"] = {on_key: on.to_yaml() for on_key, on in self._on.items()}
        if self.jobs:
            workflow["jobs"] = {
                job_name: job.to_yaml() for job_name, job in self.jobs.items()
            }
        return workflow

    def render(self) -> str:
        from .utils import dump_yaml
        header = (
            "# This file is managed by gadk. "
            "For more information see https://pypi.org/project/gadk/."
        )
        return header + "\n" + dump_yaml(self.to_yaml())
