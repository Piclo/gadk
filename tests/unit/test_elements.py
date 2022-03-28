from gadk import *


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


class TestStep:
    def test_env_is_rendered(self):
        env = {
            "DEPLOY_ENV": "prod",
            "DEPLOY_SECRET": Expression("secrets.KEY"),
        }
        expected_env = {
            "DEPLOY_ENV": "prod",
            "DEPLOY_SECRET": "${{ secrets.KEY }}",
        }

        assert RunStep("build", env=env).to_yaml()["env"] == expected_env
        assert UsesStep(ACTION_UPLOAD, env=env).to_yaml()["env"] == expected_env
