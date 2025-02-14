from pathlib import Path
from textwrap import dedent
from typing import List, Literal, Optional, Type, Union

import pytest

from gadk import *


class TestWorkflow:
    def test_env(self):
        workflow = Workflow("foo", env={"var1": "value1", "var2": "value2"})
        yaml = workflow.to_yaml()
        assert "env" in yaml
        assert yaml["env"] == {"var1": "value1", "var2": "value2"}

    def test_simple_concurrency(self):
        workflow = Workflow("foo", concurrency_group="my_group")
        assert workflow.to_yaml() == {"concurrency": "my_group", "on": {}}

    @pytest.mark.parametrize("cancel_in_progress", [True, "${{ some-expression }}"])
    def test_cancel_in_progress_concurrency(self, cancel_in_progress):
        workflow = Workflow(
            "foo", concurrency_group="my_group", cancel_in_progress=cancel_in_progress
        )
        assert workflow.to_yaml() == {
            "concurrency": {
                "group": "my_group",
                "cancel-in-progress": cancel_in_progress,
            },
            "on": {},
        }

    def test_cancel_in_progress_concurrency_expression_obj(self):
        workflow = Workflow(
            "foo",
            concurrency_group="my_group",
            cancel_in_progress=Expression("some-expression"),
        )
        assert workflow.to_yaml() == {
            "concurrency": {
                "group": "my_group",
                "cancel-in-progress": "${{ some-expression }}",
            },
            "on": {},
        }

    def test_permissions(self):
        workflow = Workflow("foo", permissions={"id-token": "write", "contents": "read"})
        assert workflow.to_yaml() == {
            "permissions": {
                "contents": "read",
                "id-token": "write",
            },
            "on": {},
        }


class TestWorkflowOn:
    def test_on_only_push(self):
        workflow = Workflow("foo")
        workflow.on(push=On(paths=["src/**"], branches=["develop"]))
        rendered = workflow.to_yaml()
        assert rendered == {
            "on": {
                "push": {
                    "paths": ["src/**"],
                    "branches": ["develop"],
                },
            },
        }

    def test_on_only_pull_request(self):
        workflow = Workflow("foo")
        workflow.on(pull_request=On(paths=["src/**"], branches=["develop"]))
        rendered = workflow.to_yaml()
        assert rendered == {
            "on": {
                "pull_request": {
                    "paths": ["src/**"],
                    "branches": ["develop"],
                },
            },
        }

    def test_on_only_workflow_dispatch(self):
        workflow = Workflow("foo")
        workflow.on(workflow_dispatch=Null())
        rendered = workflow.to_yaml()
        assert rendered == {
            "on": {"workflow_dispatch": None},
        }

    def test_on_both_push_and_pull_request(self):
        workflow = Workflow("foo")
        workflow.on(
            push=On(paths=["src/**"], branches=["develop"]),
            pull_request=On(paths=["frontend/**"], branches=["master"]),
        )
        rendered = workflow.to_yaml()
        assert rendered == {
            "on": {
                "push": {
                    "paths": ["src/**"],
                    "branches": ["develop"],
                },
                "pull_request": {
                    "paths": ["frontend/**"],
                    "branches": ["master"],
                },
            },
        }

    def test_on_push_and_pull_and_workflow_dispatch(self):
        workflow = Workflow("foo")
        workflow.on(
            push=On(paths=["src/**"], branches=["develop"]),
            pull_request=On(paths=["frontend/**"], branches=["master"]),
            workflow_dispatch=Null(),
        )
        rendered = workflow.to_yaml()
        assert rendered == {
            "on": {
                "push": {
                    "paths": ["src/**"],
                    "branches": ["develop"],
                },
                "pull_request": {
                    "paths": ["frontend/**"],
                    "branches": ["master"],
                },
                "workflow_dispatch": None,
            },
        }

    def test_on_schedule(self):
        workflow = Workflow("foo")
        workflow.on(schedules=["0 7 * * 1-5"])  # Monday-Friday at 07:00
        assert workflow.to_yaml() == {"on": {"schedule": [{"cron": "0 7 * * 1-5"}]}}


class TestJob:
    def test_name(self):
        job = Job(name="foo")
        yaml = job.to_yaml()
        assert "name" in yaml
        assert yaml["name"] == "foo"

    @pytest.mark.parametrize(
        "needs",
        [
            ["foo"],
            ["foo", "bar"],
            "foobar",
        ],
        ids=["single", "multiple", "string"],
    )
    def test_needs(self, needs):
        job = Job(needs=needs)
        yaml = job.to_yaml()
        assert "needs" in yaml
        assert yaml["needs"] == needs

    def test_outputs(self):
        job = Job(outputs={"string-output": "foo", "expr-output": Expression("bar")})
        yaml = job.to_yaml()
        assert "outputs" in yaml
        assert yaml["outputs"] == {"string-output": "foo", "expr-output": "${{ bar }}"}

    def test_matrix(self):
        matrix = {"version": ["1.1", "2.2"], "env": ["dev", "prod"]}
        job = Job(matrix=matrix)
        yaml = job.to_yaml()
        assert "strategy" in yaml
        assert yaml["strategy"] == {"matrix": matrix}

    def test_matrix_expression(self):
        matrix = Expression("some-job.some-step.dynamic-matrix")
        job = Job(matrix=matrix)
        yaml = job.to_yaml()
        assert "strategy" in yaml
        assert yaml["strategy"] == {"matrix": matrix.to_yaml()}

    def test_matrix_include(self):
        matrix = {
            "version": ["1.1", "2.2"],
            "env": ["dev", "prod"],
            "include": [
                {"version": "1.1", "env": "prod"},
                {"version": "2.2", "env": "dev"},
                {"version": "2.2", "env": "prod"},
            ],
        }
        job = Job(matrix=matrix)
        yaml = job.to_yaml()
        assert "strategy" in yaml
        assert yaml["strategy"] == {"matrix": matrix}

    def test_matrix_exclude(self):
        matrix = {
            "version": ["1.1", "2.2"],
            "env": ["dev", "prod"],
            "exclude": [
                {"version": "2.2", "env": "prod"},
            ],
        }
        job = Job(matrix=matrix)
        yaml = job.to_yaml()
        assert "strategy" in yaml
        assert yaml["strategy"] == {"matrix": matrix}

    def test_fail_fast(self):
        matrix = {"a": [1, 2]}
        job = Job(matrix=matrix, fail_fast=True)
        yaml = job.to_yaml()
        assert "strategy" in yaml
        assert yaml["strategy"] == {"matrix": matrix, "fail-fast": True}

    def test_fail_fast_without_matrix(self):
        with pytest.raises(ValueError):
            Job(fail_fast=True)

    def test_max_parallel(self):
        matrix = {"a": [1, 2]}
        job = Job(matrix=matrix, max_parallel=2)
        yaml = job.to_yaml()
        assert "strategy" in yaml
        assert yaml["strategy"] == {"matrix": matrix, "max-parallel": 2}


@pytest.mark.parametrize(
    "step_cls, step_args, step_kwargs",
    [
        (RunStep, ("echo foo",), {}),
        (UsesStep, ("foo@v1",), {}),
    ],
    ids=("RunStep", "UsesStep"),
)
class TestStep:
    def test_env_is_rendered(self, step_cls, step_args, step_kwargs):
        env = {
            "DEPLOY_ENV": "prod",
            "DEPLOY_SECRET": Expression("secrets.KEY"),
        }
        expected_env = {
            "DEPLOY_ENV": "prod",
            "DEPLOY_SECRET": "${{ secrets.KEY }}",
        }

        assert (
            step_cls(*step_args, env=env, **step_kwargs).to_yaml()["env"]
            == expected_env
        )

    def test_step_id(self, step_cls, step_args, step_kwargs):
        step = step_cls(*step_args, step_id="foobar", **step_kwargs)
        yaml = step.to_yaml()
        assert "id" in yaml
        assert yaml["id"] == "foobar"

    @pytest.mark.parametrize("continue_on_error", [None, True, False])
    def test_continue_on_error(
        self, step_cls: Type[Step], step_args, step_kwargs, continue_on_error: bool
    ):
        step = step_cls(*step_args, continue_on_error=continue_on_error, **step_kwargs)
        yaml = step.to_yaml()
        if continue_on_error is None:
            assert "continue-on-error" not in yaml
        else:
            assert "continue-on-error" in yaml
            assert yaml["continue-on-error"] == continue_on_error


class TestRunStep:
    def test_working_directory__empty(self):
        step = RunStep("echo foo")
        yaml = step.to_yaml()
        assert "working-directory" not in yaml

    def test_working_directory(self):
        step = RunStep("echo foo", workdir="foo/bar")
        yaml = step.to_yaml()
        assert "working-directory" in yaml
        assert yaml["working-directory"] == "foo/bar"


class TestCacheStep:
    @pytest.mark.parametrize(
        "paths",
        [
            ["cache-dir-1", "cache-dir-2"],
            [Path("cache-dir-1"), Path("cache-dir-2")],
        ],
        ids=["str", "Path"],
    )
    def test_ctor(self, paths: List[Union[str, Path]]):
        step = CacheStep(
            "Cache the cache directory",
            paths,
            "cache-key-${{ hashFiles('**/lockfiles') }}",
            ["cache-key-"],
        )
        yaml = step.to_yaml()
        assert yaml == {
            "name": "Cache the cache directory",
            "uses": "actions/cache@v4",
            "with": {
                "path": dedent(
                    """\
                    cache-dir-1
                    cache-dir-2"""
                ),
                "key": "cache-key-${{ hashFiles('**/lockfiles') }}",
                "restore-keys": "cache-key-",
            },
        }

    def test_simple(self):
        step = CacheStep.simple(
            "Cache dependencies", "cache-dir", "cache-deps", ["lockfile1", "lockfile2"]
        )
        yaml = step.to_yaml()
        assert yaml == {
            "name": "Cache dependencies",
            "uses": "actions/cache@v4",
            "with": {
                "path": "cache-dir",
                "key": "cache-deps-${{ hashFiles('lockfile1', 'lockfile2') }}",
                "restore-keys": "cache-deps-",
            },
        }


class TestArtifact:
    def test_upload(self):
        artifact = Artifact(name="my-artifact", path="foo/bar")
        upload_step = artifact.as_upload()
        assert isinstance(upload_step, UsesStep)
        assert vars(upload_step) == vars(
            UsesStep(
                name=f"Upload artifact 'my-artifact'",
                action=ACTION_UPLOAD,
                with_args={"name": "my-artifact", "path": "foo/bar"},
            )
        )

    def test_download(self):
        artifact = Artifact(name="my-artifact", path="foo/bar")
        download_step = artifact.as_download()
        assert isinstance(download_step, UsesStep)
        assert vars(download_step) == vars(
            UsesStep(
                name=f"Download artifact 'my-artifact'",
                action=ACTION_DOWNLOAD,
                with_args={"name": "my-artifact", "path": "foo/bar"},
            )
        )

    def test_download_dest_path(self):
        artifact = Artifact(name="my-artifact", path="foo/bar")
        download_step = artifact.as_download(dest_path="baz")
        assert isinstance(download_step, UsesStep)
        assert vars(download_step) == vars(
            UsesStep(
                name=f"Download artifact 'my-artifact'",
                action=ACTION_DOWNLOAD,
                with_args={"name": "my-artifact", "path": "baz"},
            )
        )

    @pytest.mark.parametrize("if_no_files_found", [None, "error", "warn", "ignore"])
    def test_if_no_files_found(
        self, if_no_files_found: Optional[Literal["error", "warn", "ignore"]]
    ):
        artifact = Artifact(name="my-artifact", path="foo/bar")
        if if_no_files_found is None:
            upload_step = artifact.as_upload()
        else:
            upload_step = artifact.as_upload(if_no_files_found=if_no_files_found)

        expected_args = {"name": "my-artifact", "path": "foo/bar"}
        if if_no_files_found is not None:
            expected_args["if-no-files-found"] = if_no_files_found
        assert vars(upload_step) == vars(
            UsesStep(
                name=f"Upload artifact 'my-artifact'",
                action=ACTION_UPLOAD,
                with_args=expected_args,
            )
        )
