import pytest

from gadk import *


class TestWorkflow:
    def test_simple_concurrency(self):
        workflow = Workflow("foo", concurrency_group="my_group")
        assert workflow.to_yaml() == {"concurrency": "my_group", "on": {}}

    @pytest.mark.parametrize('cancel_in_progress', [True, "${{ some-expression }}"])
    def test_cancel_in_progress_concurrency(self, cancel_in_progress):
        workflow = Workflow(
            "foo", concurrency_group="my_group", cancel_in_progress=cancel_in_progress
        )
        assert workflow.to_yaml() == {
            "concurrency": {"group": "my_group", "cancel-in-progress": cancel_in_progress},
            "on": {},
        }

    def test_cancel_in_progress_concurrency_expression_obj(self):
        workflow = Workflow(
            "foo", concurrency_group="my_group", cancel_in_progress=Expression("some-expression")
        )
        assert workflow.to_yaml() == {
            "concurrency": {"group": "my_group", "cancel-in-progress": "${{ some-expression }}"},
            "on": {},
        }


class TestWorkflowOn:
    def test_on_only_push(self):
        workflow = Workflow("foo")
        workflow.on(push=On(paths=["src/**"], branches=["develop"]))
        rendered = workflow.to_yaml()
        assert rendered == {
            "on": {"push": {"paths": ["src/**"], "branches": ["develop"],},},
        }

    def test_on_only_pull_request(self):
        workflow = Workflow("foo")
        workflow.on(pull_request=On(paths=["src/**"], branches=["develop"]))
        rendered = workflow.to_yaml()
        assert rendered == {
            "on": {"pull_request": {"paths": ["src/**"], "branches": ["develop"],},},
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
                "push": {"paths": ["src/**"], "branches": ["develop"],},
                "pull_request": {"paths": ["frontend/**"], "branches": ["master"],},
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
                "push": {"paths": ["src/**"], "branches": ["develop"],},
                "pull_request": {"paths": ["frontend/**"], "branches": ["master"],},
                "workflow_dispatch": None,
            },
        }


class TestJob:
    @pytest.mark.parametrize("needs", [
        ["foo"],
        ["foo", "bar"],
    ], ids=["single", "multiple"])
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


@pytest.mark.parametrize("step_cls, step_args, step_kwargs", [
    (RunStep, ("echo foo",), {}),
    (UsesStep, ("foo@v1",), {}),
], ids=("RunStep", "UsesStep"))
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

        assert step_cls(*step_args, env=env, **step_kwargs).to_yaml()["env"] == expected_env

    def test_step_id(self, step_cls, step_args, step_kwargs):
        step = step_cls(*step_args, step_id="foobar", **step_kwargs)
        yaml = step.to_yaml()
        assert "id" in yaml
        assert yaml["id"] == "foobar"
