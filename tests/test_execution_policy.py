"""Offline execution-policy regression tests; no providers or live tools run.

Run from the repository root: python -m unittest discover -s tests -v
Only the optional anthropic import is stubbed. Agent, registry, shell, and
Authorizer code under test are real; every subprocess and tool side effect is
replaced with a mock. Config/memory are synthetic objects, never loaded from disk.
"""
from __future__ import annotations

import importlib
from pathlib import Path
import subprocess
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from jarvis import tools
from jarvis.auth import Authorizer
from jarvis.tools import shell
from jarvis.tools.base import Tool, ToolContext, ToolResult


# Do not import the provider SDK or inspect its configuration, even if installed.
_anthropic_stub = ModuleType("anthropic")
_anthropic_stub.Anthropic = Mock(side_effect=AssertionError("provider construction forbidden"))
with patch.dict(sys.modules, {"anthropic": _anthropic_stub}):
    agent_module = importlib.import_module("jarvis.agent")
Agent = agent_module.Agent


def tool_block(name: str, tool_input=None, call_id: str = "synthetic-call"):
    return SimpleNamespace(type="tool_use", name=name, input=tool_input, id=call_id)


class OfflineCase(unittest.TestCase):
    def setUp(self):
        self.workspace = Path.cwd() / "synthetic-unused-workspace"
        self.config = SimpleNamespace(
            api_key="unused-synthetic-placeholder",
            user_name="Synthetic operator",
            workspace=self.workspace,
        )
        self.memory = SimpleNamespace(summary=Mock(return_value="synthetic memory"))
        self.confirm = Mock(return_value=True)
        self.ctx = ToolContext(self.config, self.memory, self.workspace, self.confirm)
        self.run = self.enterContext(patch.object(subprocess, "run"))
        self.run.return_value = SimpleNamespace(returncode=0, stdout="synthetic stdout", stderr="")
        self.popen = self.enterContext(
            patch.object(subprocess, "Popen", side_effect=AssertionError("live subprocess forbidden"))
        )


class ToolPolicyTests(OfflineCase):
    def setUp(self):
        super().setUp()
        self.tool_runs = {}
        for tool in tools.ALL_TOOLS:
            handler = Mock(return_value=ToolResult(f"synthetic result: {tool.name}"))
            self.enterContext(patch.object(tool, "run", handler))
            self.tool_runs[tool.name] = handler
        self.client = Mock()
        self.client.messages.stream.side_effect = AssertionError("provider request forbidden")
        self.client_factory = self.enterContext(
            patch.object(agent_module.anthropic, "Anthropic", return_value=self.client)
        )
        # platform.uname() can invoke the Windows `ver` shell command lazily.
        # Keep workstation metadata synthetic so that probe never runs either.
        for attribute, value in (("system", "FixtureOS"), ("release", "0"), ("machine", "fixture")):
            self.enterContext(patch.object(agent_module.platform, attribute, return_value=value))
        self.enterContext(patch.object(agent_module, "build_system_prompt", return_value="synthetic prompt"))

    def tearDown(self):
        self.run.assert_not_called()
        self.popen.assert_not_called()
        self.client.messages.stream.assert_not_called()

    def make_agent(self, excluded=()):
        return Agent(self.config, self.memory, self.confirm, exclude_tool_tags=excluded)

    def test_default_agent_allows_every_advertised_custom_tool(self):
        agent = self.make_agent()
        names = {tool.name for tool in tools.ALL_TOOLS}
        self.assertIsInstance(agent._allowed_tool_names, frozenset)
        self.assertEqual(agent._allowed_tool_names, names)
        self.assertTrue({tool["name"] for tool in agent_module.SERVER_TOOLS}.isdisjoint(names))
        payload = {"fixture": "synthetic"}
        results = agent._execute_pending_tools([tool_block(name, payload, name) for name in sorted(names)])
        self.assertEqual(len(results), len(names))
        self.assertTrue(all(not item["is_error"] for item in results))
        for handler in self.tool_runs.values():
            handler.assert_called_once_with(payload, agent._ctx)

    def test_read_only_agent_rejects_shell_and_file_write_before_execution(self):
        agent = self.make_agent(("destructive", "shell"))
        advertised = {item["name"] for item in agent._tool_schemas}
        for name in ("shell_exec", "write_file"):
            with self.subTest(name=name):
                self.assertNotIn(name, advertised)
                result = agent._execute_pending_tools([tool_block(name, {"fixture": "synthetic"})])[0]
                self.assertTrue(result["is_error"])
                self.assertIn(name, result["content"])
                self.tool_runs[name].assert_not_called()
        self.confirm.assert_not_called()

    def test_read_only_agent_still_executes_an_allowed_tool(self):
        agent = self.make_agent(("destructive", "shell"))
        result = agent._execute_pending_tools([tool_block("read_file", {"path": "fixture.txt"})])[0]
        self.assertFalse(result["is_error"])
        self.tool_runs["read_file"].assert_called_once_with({"path": "fixture.txt"}, agent._ctx)

    def test_unknown_model_tool_name_is_an_error(self):
        agent = self.make_agent()
        result = agent._execute_pending_tools([tool_block("synthetic_unknown_tool")])[0]
        self.assertTrue(result["is_error"])
        self.assertIn("Unknown tool", result["content"])
        for handler in self.tool_runs.values():
            handler.assert_not_called()

    def test_tool_registered_after_agent_creation_is_not_authorized(self):
        agent = self.make_agent()
        handler = Mock(return_value=ToolResult("must not execute"))
        late_tool = Tool("synthetic_late_tool", "fixture", {}, handler)
        with patch.dict(tools.TOOL_BY_NAME, {late_tool.name: late_tool}):
            result = agent._execute_pending_tools([tool_block(late_tool.name)])[0]
        self.assertTrue(result["is_error"])
        handler.assert_not_called()

    def test_empty_allowlist_denies_a_registered_tool(self):
        result = tools.dispatch("read_file", {}, self.ctx, allowed_tool_names=frozenset())
        self.assertTrue(result.is_error)
        self.tool_runs["read_file"].assert_not_called()

    def test_explicit_allowlist_executes_only_its_members(self):
        allow = frozenset({"read_file"})
        allowed = tools.dispatch("read_file", {}, self.ctx, allowed_tool_names=allow)
        denied = tools.dispatch("write_file", {}, self.ctx, allowed_tool_names=allow)
        self.assertFalse(allowed.is_error)
        self.assertTrue(denied.is_error)
        self.tool_runs["read_file"].assert_called_once_with({}, self.ctx)
        self.tool_runs["write_file"].assert_not_called()

    def test_unknown_tool_remains_unknown_even_if_named_in_allowlist(self):
        name = "synthetic_unknown_tool"
        result = tools.dispatch(name, {}, self.ctx, allowed_tool_names=frozenset({name}))
        self.assertTrue(result.is_error)
        self.assertIn("Unknown tool", result.content)

    def test_dispatch_requires_an_explicit_execution_policy(self):
        with self.assertRaises(TypeError):
            tools.dispatch("read_file", {}, self.ctx)
        self.tool_runs["read_file"].assert_not_called()

    def test_no_custom_schemas_means_no_custom_execution_permission(self):
        with patch.object(tools, "schemas_for_api", return_value=[]):
            agent = self.make_agent()
        self.assertEqual(agent._allowed_tool_names, frozenset())
        result = agent._execute_pending_tools([tool_block("read_file")])[0]
        self.assertTrue(result["is_error"])
        self.tool_runs["read_file"].assert_not_called()

    def test_mutating_schema_list_cannot_expand_execution_permissions(self):
        agent = self.make_agent(("destructive", "shell"))
        agent._tool_schemas.append({"name": "shell_exec"})
        result = agent._execute_pending_tools([tool_block("shell_exec")])[0]
        self.assertTrue(result["is_error"])
        self.tool_runs["shell_exec"].assert_not_called()

    def test_agent_policies_do_not_leak_between_instances(self):
        unrestricted = self.make_agent()
        read_only = self.make_agent(("destructive", "shell"))
        self.assertFalse(unrestricted._execute_pending_tools([tool_block("shell_exec")])[0]["is_error"])
        self.assertTrue(read_only._execute_pending_tools([tool_block("shell_exec")])[0]["is_error"])
        self.tool_runs["shell_exec"].assert_called_once()

    def test_mixed_blocks_skip_server_tools_and_preserve_result_envelopes(self):
        agent = self.make_agent(("destructive", "shell"))
        content = [
            SimpleNamespace(type="text", text="synthetic"),
            SimpleNamespace(type="server_tool_use", name="web_search"),
            SimpleNamespace(type="server_tool_result"),
            tool_block("read_file", None, "allowed-id"),
            tool_block("shell_exec", {}, "denied-id"),
            tool_block("synthetic_unknown_tool", {}, "unknown-id"),
            tool_block("web_search", {}, "server-name-as-client-id"),
        ]
        results = agent._execute_pending_tools(content)
        self.assertEqual(
            [item["tool_use_id"] for item in results],
            ["allowed-id", "denied-id", "unknown-id", "server-name-as-client-id"],
        )
        self.assertEqual([item["is_error"] for item in results], [False, True, True, True])
        self.assertIn("Unknown tool", results[-1]["content"])
        self.assertTrue(all(set(item) == {"type", "tool_use_id", "content", "is_error"} for item in results))
        self.assertTrue(all(item["type"] == "tool_result" for item in results))
        self.tool_runs["read_file"].assert_called_once_with({}, agent._ctx)
        self.tool_runs["shell_exec"].assert_not_called()

    def test_allowed_handler_exception_is_returned_as_tool_error(self):
        self.tool_runs["read_file"].side_effect = ValueError("synthetic failure")
        result = tools.dispatch("read_file", {}, self.ctx, allowed_tool_names=frozenset({"read_file"}))
        self.assertTrue(result.is_error)
        self.assertIn("ValueError", result.content)
        self.assertIn("synthetic failure", result.content)

    def test_excluded_shell_does_not_consume_server_one_shot_grant(self):
        authorizer = Authorizer()
        authorizer.set_mode("one_shot")
        agent = Agent(
            self.config, self.memory, authorizer.confirm, exclude_tool_tags=("destructive", "shell")
        )
        result = agent._execute_pending_tools([tool_block("shell_exec", {"command": "echo synthetic"})])[0]
        self.assertTrue(result["is_error"])
        self.assertEqual(authorizer.state.mode, "one_shot")
        self.assertIsNone(authorizer.last_check)
        self.tool_runs["shell_exec"].assert_not_called()


class ShellApprovalTests(OfflineCase):
    def test_all_shell_commands_require_approval_even_without_blacklist_tokens(self):
        for command in ("echo synthetic", "fixture_mutator synthetic", "git status"):
            with self.subTest(command=command):
                self.confirm.reset_mock()
                self.run.reset_mock()
                result = shell._shell_exec({"command": command}, self.ctx)
                self.assertFalse(result.is_error)
                self.confirm.assert_called_once_with(
                    "shell_exec", f"$ {command}\ncwd={self.workspace}\ntimeout=60s"
                )
                self.run.assert_called_once()

    def test_confirm_field_never_bypasses_operator_refusal(self):
        self.confirm.return_value = False
        for fields in ({}, {"confirm": False}, {"confirm": True}):
            with self.subTest(fields=fields):
                self.confirm.reset_mock()
                result = shell._shell_exec({"command": "echo synthetic", **fields}, self.ctx)
                self.assertTrue(result.is_error)
                self.confirm.assert_called_once()
        self.run.assert_not_called()

    def test_only_boolean_true_is_approval(self):
        for answer in (None, 0, 1, "yes", [], {"approved": True}):
            with self.subTest(answer=answer):
                self.confirm.return_value = answer
                result = shell._shell_exec({"command": "echo synthetic"}, self.ctx)
                self.assertTrue(result.is_error)
        self.run.assert_not_called()

    def test_unavailable_approval_callback_fails_closed(self):
        self.ctx.confirm_destructive = None
        result = shell._shell_exec({"command": "echo synthetic"}, self.ctx)
        self.assertTrue(result.is_error)
        self.run.assert_not_called()

    def test_approval_callback_exception_fails_closed(self):
        for error in (
            RuntimeError("synthetic unavailable"), EOFError("synthetic EOF"), KeyboardInterrupt()
        ):
            with self.subTest(error=type(error).__name__):
                self.confirm.side_effect = error
                result = shell._shell_exec({"command": "echo synthetic"}, self.ctx)
                self.assertTrue(result.is_error)
        self.run.assert_not_called()

    def test_approved_call_discloses_and_uses_exact_parameters(self):
        payload = {"command": "  echo synthetic  ", "cwd": "fixture-child", "timeout": 7, "confirm": False}
        workdir = (self.workspace / "fixture-child").resolve()
        result = shell._shell_exec(payload, self.ctx)
        self.assertFalse(result.is_error)
        self.confirm.assert_called_once_with("shell_exec", f"$ echo synthetic\ncwd={workdir}\ntimeout=7s")
        self.run.assert_called_once_with(
            "echo synthetic", shell=True, cwd=str(workdir), capture_output=True, text=True, timeout=7
        )
        self.assertIn("synthetic stdout", result.content)

    def test_blank_command_does_not_prompt_or_spawn(self):
        result = shell._shell_exec({"command": "  "}, self.ctx)
        self.assertTrue(result.is_error)
        self.confirm.assert_not_called()
        self.run.assert_not_called()

    def test_timeout_after_approval_preserves_tool_error(self):
        self.run.side_effect = subprocess.TimeoutExpired("synthetic fixture", 2)
        result = shell._shell_exec({"command": "echo synthetic", "timeout": 2}, self.ctx)
        self.assertTrue(result.is_error)
        self.assertIn("timed out after 2s", result.content)
        self.confirm.assert_called_once()

    def test_nonzero_exit_preserves_stdout_stderr_and_error_status(self):
        self.run.return_value = SimpleNamespace(returncode=3, stdout="synthetic out", stderr="synthetic err")
        result = shell._shell_exec({"command": "echo synthetic"}, self.ctx)
        self.assertTrue(result.is_error)
        for text in ("FAIL exit=3", "synthetic out", "synthetic err"):
            self.assertIn(text, result.content)

    def test_output_limits_are_preserved_after_approval(self):
        self.run.return_value = SimpleNamespace(returncode=0, stdout="a" * (shell.MAX_OUTPUT + 5), stderr="")
        result = shell._shell_exec({"command": "echo synthetic"}, self.ctx)
        self.assertFalse(result.is_error)
        self.assertIn("stdout truncated", result.content)
        self.assertNotIn("a" * (shell.MAX_OUTPUT + 1), result.content)

    def test_server_default_deny_blocks_every_shell_command(self):
        authorizer = Authorizer()
        self.ctx.confirm_destructive = authorizer.confirm
        result = shell._shell_exec({"command": "echo synthetic"}, self.ctx)
        self.assertTrue(result.is_error)
        self.assertEqual(authorizer.state.mode, "deny")
        self.assertEqual(authorizer.last_check[0], "shell_exec")
        self.run.assert_not_called()

    def test_server_one_shot_grant_is_consumed_by_one_shell_call(self):
        authorizer = Authorizer()
        authorizer.set_mode("one_shot")
        self.ctx.confirm_destructive = authorizer.confirm
        first = shell._shell_exec({"command": "echo synthetic"}, self.ctx)
        second = shell._shell_exec({"command": "echo synthetic"}, self.ctx)
        self.assertFalse(first.is_error)
        self.assertTrue(second.is_error)
        self.assertEqual(authorizer.state.mode, "deny")
        self.run.assert_called_once()

    def test_server_session_grant_expires_before_next_shell_call(self):
        authorizer = Authorizer()
        self.ctx.confirm_destructive = authorizer.confirm
        with patch("jarvis.auth.time.time", return_value=100):
            authorizer.set_mode("session", ttl_seconds=10)
        with patch("jarvis.auth.time.time", return_value=105):
            first = shell._shell_exec({"command": "echo synthetic"}, self.ctx)
            second = shell._shell_exec({"command": "echo synthetic"}, self.ctx)
        with patch("jarvis.auth.time.time", return_value=111):
            expired = shell._shell_exec({"command": "echo synthetic"}, self.ctx)
        self.assertFalse(first.is_error)
        self.assertFalse(second.is_error)
        self.assertTrue(expired.is_error)
        self.assertEqual(authorizer.state.mode, "deny")
        self.assertEqual(self.run.call_count, 2)


if __name__ == "__main__":
    unittest.main()
