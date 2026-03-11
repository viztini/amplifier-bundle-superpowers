# Superpowers Bundle Update — Implementation Plan

> **Execution:** Use the subagent-driven-development workflow to implement this plan.

**Goal:** Update the Amplifier superpowers ecosystem across 3 repos: fix staged sub-recipe composition in the recipe engine, fix @-mention resolution in mode bodies, then update superpowers content (skills, modes, agents, context, recipes).

**Architecture:** Three work streams in dependency order. Work Stream 1 (amplifier-bundle-recipes) adds child session management and approval forwarding to support staged sub-recipe composition. Work Stream 2 (amplifier-bundle-modes) adds `load_mentions()` processing to mode body injection. Work Stream 3 (amplifier-bundle-superpowers) leverages both fixes to restructure skills, enrich modes with @-mentioned shared content, update agents, and restructure the full-development-cycle recipe to compose the SDD recipe directly.

**Tech Stack:** Python 3.12, pytest + pytest-asyncio, YAML recipes, Markdown mode/agent/context files

**Design document:** `docs/superpowers/specs/2026-03-11-superpowers-update-design.md`

---

# Work Stream 1: Recipe Engine Fix

**Repo:** `/home/bkrabach/dev/superpowers-3/amplifier-bundle-recipes`
**Branch:** `feature/staged-sub-recipe-composition`
**Source:** `modules/tool-recipes/amplifier_module_tool_recipes/`
**Tests:** `modules/tool-recipes/tests/`
**Run tests from:** `modules/tool-recipes/`

Before starting, create the branch:
```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-recipes
git checkout -b feature/staged-sub-recipe-composition
```

---

## Task 1.1: Add `resume_session_id` to `ApprovalGatePausedError`

**Files:**
- Modify: `modules/tool-recipes/amplifier_module_tool_recipes/executor.py:46-58`
- Test: `modules/tool-recipes/tests/test_staged_sub_recipe.py` (create)

**Step 1: Write the failing test**

Create `modules/tool-recipes/tests/test_staged_sub_recipe.py`:

```python
"""Tests for staged sub-recipe composition.

Tests cover:
- ApprovalGatePausedError with resume_session_id
- Child session management in _execute_recipe_step
- Flat and staged execution loop APE handling
- Approval forwarding and denial forwarding
- Resume cascade
- Validator warning for parallel foreach + recipe steps
"""

import pytest
from amplifier_module_tool_recipes.executor import ApprovalGatePausedError


class TestApprovalGatePausedErrorResumeSessionId:
    """ApprovalGatePausedError must support an optional resume_session_id."""

    def test_default_resume_session_id_is_none(self):
        """Without resume_session_id, it defaults to None."""
        error = ApprovalGatePausedError(
            session_id="parent-session",
            stage_name="my-stage",
            approval_prompt="Approve?",
        )
        assert error.resume_session_id is None, (
            "Default resume_session_id should be None"
        )

    def test_resume_session_id_preserved(self):
        """When resume_session_id is set, it is preserved on the error."""
        error = ApprovalGatePausedError(
            session_id="parent-session",
            stage_name="my-stage",
            approval_prompt="Approve?",
            resume_session_id="child-session",
        )
        assert error.resume_session_id == "child-session", (
            "resume_session_id should be preserved"
        )

    def test_existing_fields_unchanged(self):
        """Existing fields still work with the new parameter."""
        error = ApprovalGatePausedError(
            session_id="parent-session",
            stage_name="my-stage",
            approval_prompt="Approve?",
            resume_session_id="child-session",
        )
        assert error.session_id == "parent-session"
        assert error.stage_name == "my-stage"
        assert error.approval_prompt == "Approve?"
```

**Step 2: Run test to verify it fails**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-recipes/modules/tool-recipes
python -m pytest tests/test_staged_sub_recipe.py::TestApprovalGatePausedErrorResumeSessionId -v
```
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'resume_session_id'`

**Step 3: Write minimal implementation**

In `modules/tool-recipes/amplifier_module_tool_recipes/executor.py`, replace lines 46-58:

```python
class ApprovalGatePausedError(Exception):
    """Raised when execution pauses at an approval gate.

    This is not a failure - it signals that the recipe has paused
    waiting for human approval before continuing to the next stage.
    Callers should catch this and handle it appropriately (e.g., notify user).
    """

    def __init__(
        self,
        session_id: str,
        stage_name: str,
        approval_prompt: str,
        resume_session_id: str | None = None,
    ):
        self.session_id = session_id
        self.stage_name = stage_name
        self.approval_prompt = approval_prompt
        self.resume_session_id = resume_session_id
        super().__init__(f"Execution paused at stage '{stage_name}' awaiting approval")
```

**Step 4: Run test to verify it passes**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-recipes/modules/tool-recipes
python -m pytest tests/test_staged_sub_recipe.py::TestApprovalGatePausedErrorResumeSessionId -v
```
Expected: PASS (3 tests)

**Step 5: Run full test suite to check for regressions**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-recipes/modules/tool-recipes
python -m pytest tests/ -v
```
Expected: All existing tests still pass (the new parameter defaults to None, so all existing callers are unaffected).

**Step 6: Commit**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-recipes
git add modules/tool-recipes/amplifier_module_tool_recipes/executor.py modules/tool-recipes/tests/test_staged_sub_recipe.py
git commit -m "feat: add resume_session_id to ApprovalGatePausedError"
```

---

## Task 1.2: Update `_execute_recipe_step()` — child session management

**Files:**
- Modify: `modules/tool-recipes/amplifier_module_tool_recipes/executor.py:2192-2280`
- Test: `modules/tool-recipes/tests/test_staged_sub_recipe.py`

**Step 1: Write the failing test**

Append to `modules/tool-recipes/tests/test_staged_sub_recipe.py`:

```python
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from amplifier_module_tool_recipes.executor import RecipeExecutor, RecursionState
from amplifier_module_tool_recipes.models import Recipe, Step


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator with async spawn capability."""
    coordinator = MagicMock()
    coordinator.session = MagicMock()
    coordinator.config = {"agents": {}}
    coordinator.hooks = None
    coordinator.get_capability.return_value = AsyncMock()
    return coordinator


@pytest.fixture
def mock_session_manager():
    """Create a mock session manager."""
    manager = MagicMock()
    manager.create_session.return_value = "child-session-id"
    manager.load_state.return_value = {
        "current_step_index": 0,
        "context": {},
        "completed_steps": [],
        "started": "2025-01-01T00:00:00",
    }
    manager.is_cancellation_requested.return_value = False
    manager.is_immediate_cancellation.return_value = False
    return manager


class TestExecuteRecipeStepChildSession:
    """_execute_recipe_step must manage child sessions for staged sub-recipes."""

    @pytest.mark.asyncio
    async def test_saved_child_session_passed_as_session_id(
        self, mock_coordinator, mock_session_manager, tmp_path
    ):
        """When context has _child_session_{step_id}, pass it as session_id to resume child."""
        # Create a staged sub-recipe file
        sub_recipe_yaml = tmp_path / "staged-sub.yaml"
        sub_recipe_yaml.write_text("""
name: staged-sub
description: A staged sub-recipe
version: "1.0.0"
stages:
  - name: "do-work"
    steps:
      - id: work
        agent: test-agent
        prompt: "Do work"
        output: result
""")

        step = Step(
            id="call-sub",
            type="recipe",
            recipe="staged-sub.yaml",
            step_context={},
        )

        # Pre-populate context with a saved child session reference
        context = {"_child_session_call-sub": "saved-child-session-123"}

        executor = RecipeExecutor(mock_coordinator, mock_session_manager)

        # Mock execute_recipe to track how it's called
        with patch.object(executor, "execute_recipe", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = {"result": "done"}

            await executor._execute_recipe_step(
                step=step,
                context=context,
                project_path=tmp_path,
                recursion_state=RecursionState(recipe_stack=["parent"]),
                parent_recipe_path=tmp_path / "parent.yaml",
            )

            # Verify execute_recipe was called with the saved session_id
            call_kwargs = mock_exec.call_args
            assert call_kwargs.kwargs.get("session_id") == "saved-child-session-123", (
                "Should pass saved child session_id to resume the child"
            )

    @pytest.mark.asyncio
    async def test_ape_saves_child_session_in_context(
        self, mock_coordinator, mock_session_manager, tmp_path
    ):
        """When child raises ApprovalGatePausedError, save its session_id in context."""
        sub_recipe_yaml = tmp_path / "staged-sub.yaml"
        sub_recipe_yaml.write_text("""
name: staged-sub
description: A staged sub-recipe
version: "1.0.0"
stages:
  - name: "gated"
    steps:
      - id: work
        agent: test-agent
        prompt: "Do work"
    approval:
      required: true
      prompt: "Approve?"
""")

        step = Step(
            id="call-sub",
            type="recipe",
            recipe="staged-sub.yaml",
            step_context={},
        )
        context = {}

        executor = RecipeExecutor(mock_coordinator, mock_session_manager)

        # Mock execute_recipe to raise APE (simulating child hitting a gate)
        child_ape = ApprovalGatePausedError(
            session_id="child-session-456",
            stage_name="gated",
            approval_prompt="Approve?",
        )
        with patch.object(executor, "execute_recipe", new_callable=AsyncMock) as mock_exec:
            mock_exec.side_effect = child_ape

            with pytest.raises(ApprovalGatePausedError):
                await executor._execute_recipe_step(
                    step=step,
                    context=context,
                    project_path=tmp_path,
                    recursion_state=RecursionState(recipe_stack=["parent"]),
                    parent_recipe_path=tmp_path / "parent.yaml",
                )

        # Context should now have the saved child session reference
        assert context.get("_child_session_call-sub") == "child-session-456", (
            "Child session_id should be saved in context as _child_session_{step_id}"
        )
```

**Step 2: Run test to verify it fails**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-recipes/modules/tool-recipes
python -m pytest tests/test_staged_sub_recipe.py::TestExecuteRecipeStepChildSession -v
```
Expected: FAIL — the current `_execute_recipe_step` passes `session_id=None` always, and doesn't catch `ApprovalGatePausedError`.

**Step 3: Write minimal implementation**

In `modules/tool-recipes/amplifier_module_tool_recipes/executor.py`, replace the `_execute_recipe_step` method (lines 2192-2280) with:

```python
    async def _execute_recipe_step(
        self,
        step: Step,
        context: dict[str, Any],
        project_path: Path,
        recursion_state: RecursionState,
        parent_recipe_path: Path | None = None,
        rate_limiter: RateLimiter | None = None,
        orchestrator_config: OrchestratorConfig | None = None,
        parent_session_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Execute a recipe composition step by loading and running a sub-recipe.

        For staged sub-recipes, manages child sessions:
        - Checks for saved child session from previous pause (_child_session_{step_id})
        - Catches ApprovalGatePausedError and saves child session reference
        - On resume, passes saved session_id to resume child instead of creating new

        Args:
            step: Step with type="recipe" and recipe path
            context: Current context variables
            project_path: Current project directory
            recursion_state: Recursion tracking state
            parent_recipe_path: Path to parent recipe file (for relative resolution)
            rate_limiter: Optional rate limiter (inherited from parent recipe)
            orchestrator_config: Optional orchestrator config (inherited from parent recipe)
            parent_session_id: Parent's session ID for cancellation checks

        Returns:
            Sub-recipe's final context dict
        """
        assert step.recipe is not None, "Recipe step must have recipe path"

        # Substitute variables in recipe path (e.g., {{test_recipe}} in foreach loops)
        recipe_path_str = self.substitute_variables(step.recipe, context)

        # Handle @mention paths (e.g., @recipes:examples/code-review.yaml)
        if recipe_path_str.startswith("@"):
            mention_resolver = self.coordinator.get_capability("mention_resolver")
            if mention_resolver is None:
                raise FileNotFoundError(
                    f"Cannot resolve @mention path '{recipe_path_str}': mention_resolver capability not available"
                )
            sub_recipe_path = mention_resolver.resolve(recipe_path_str)
            if sub_recipe_path is None:
                raise FileNotFoundError(
                    f"Sub-recipe @mention not found: {recipe_path_str}"
                )
        else:
            # Resolve sub-recipe path relative to parent recipe's directory (not project_path)
            # This allows recipes to reference sibling recipes naturally
            if parent_recipe_path is not None:
                base_dir = parent_recipe_path.parent
            else:
                base_dir = project_path

            sub_recipe_path = base_dir / recipe_path_str
            if not sub_recipe_path.exists():
                raise FileNotFoundError(f"Sub-recipe not found: {sub_recipe_path}")

        # Load sub-recipe
        sub_recipe = Recipe.from_yaml(sub_recipe_path)

        # Build sub-recipe context from step's context field (with variable substitution)
        # Context isolation: sub-recipe gets ONLY explicitly passed context
        sub_context: dict[str, Any] = {}
        if step.step_context:
            for key, value in step.step_context.items():
                # Recursively substitute variables in all values (strings, dicts, lists)
                sub_context[key] = self._substitute_variables_recursive(value, context)

        # Create child recursion state (with step-level override if present)
        child_state = recursion_state.enter_recipe(sub_recipe.name, step.recursion)

        # Check for saved child session from a previous pause
        child_session_key = f"_child_session_{step.id}"
        saved_child_session = context.get(child_session_key)

        # Execute sub-recipe recursively
        # If we have a saved child session, pass it as session_id to resume the child
        # Otherwise, pass None to create a new session (for staged) or run inline (for flat)
        try:
            result = await self.execute_recipe(
                recipe=sub_recipe,
                context_vars=sub_context,
                project_path=project_path,
                session_id=saved_child_session,
                recipe_path=sub_recipe_path,
                recursion_state=child_state,
                rate_limiter=rate_limiter,
                orchestrator_config=orchestrator_config,
                parent_session_id=parent_session_id,
            )
        except ApprovalGatePausedError as e:
            # Child hit an approval gate — save its session reference for later resume
            context[child_session_key] = e.session_id
            raise

        # Propagate total steps back to parent state
        recursion_state.total_steps = child_state.total_steps

        # Clean up saved child session on successful completion
        context.pop(child_session_key, None)

        return result
```

**Step 4: Run test to verify it passes**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-recipes/modules/tool-recipes
python -m pytest tests/test_staged_sub_recipe.py::TestExecuteRecipeStepChildSession -v
```
Expected: PASS (2 tests)

**Step 5: Run full test suite**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-recipes/modules/tool-recipes
python -m pytest tests/ -v
```
Expected: All tests pass.

**Step 6: Commit**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-recipes
git add modules/tool-recipes/amplifier_module_tool_recipes/executor.py modules/tool-recipes/tests/test_staged_sub_recipe.py
git commit -m "feat: manage child sessions in _execute_recipe_step for staged sub-recipes"
```

---

## Task 1.3: Update flat execution loop — catch child APE, mirror approval

**Files:**
- Modify: `modules/tool-recipes/amplifier_module_tool_recipes/executor.py` (flat loop ~lines 635-720)
- Test: `modules/tool-recipes/tests/test_staged_sub_recipe.py`

**Step 1: Write the failing test**

Append to `modules/tool-recipes/tests/test_staged_sub_recipe.py`:

```python
class TestFlatLoopApprovalMirroring:
    """Flat execution loop must catch child APE and mirror approval on parent."""

    @pytest.mark.asyncio
    async def test_flat_parent_mirrors_child_approval(
        self, mock_coordinator, mock_session_manager, tmp_path
    ):
        """When a recipe step's child raises APE, parent mirrors the approval gate."""
        # Create a staged sub-recipe
        sub_recipe_yaml = tmp_path / "staged-child.yaml"
        sub_recipe_yaml.write_text("""
name: staged-child
description: Child with approval gate
version: "1.0.0"
stages:
  - name: "work"
    steps:
      - id: do-work
        agent: test-agent
        prompt: "Work"
    approval:
      required: true
      prompt: "Approve child work?"
""")

        # Create a flat parent recipe that calls the staged child
        parent_recipe = Recipe(
            name="flat-parent",
            description="Flat parent calling staged child",
            version="1.0.0",
            steps=[
                Step(
                    id="call-child",
                    type="recipe",
                    recipe="staged-child.yaml",
                    step_context={},
                ),
            ],
            context={},
        )

        executor = RecipeExecutor(mock_coordinator, mock_session_manager)

        # The child will raise APE when it hits its approval gate
        child_ape = ApprovalGatePausedError(
            session_id="child-session-789",
            stage_name="work",
            approval_prompt="Approve child work?",
        )

        with patch.object(
            executor, "_execute_recipe_step", new_callable=AsyncMock
        ) as mock_step:
            mock_step.side_effect = child_ape

            with pytest.raises(ApprovalGatePausedError) as exc_info:
                await executor.execute_recipe(
                    parent_recipe, {}, tmp_path, recipe_path=tmp_path / "parent.yaml"
                )

            # The re-raised error should have the PARENT's session_id
            # (not the child's) so the user interacts with parent only
            raised = exc_info.value
            assert raised.session_id != "child-session-789", (
                "Re-raised APE should have parent's session_id, not child's"
            )

        # Parent session should have pending approval set
        mock_session_manager.set_pending_approval.assert_called_once()
        call_kwargs = mock_session_manager.set_pending_approval.call_args
        # Stage name should be compound: identifies it came from child
        assert "work" in str(call_kwargs), (
            "Mirrored approval should reference child's stage name"
        )
```

**Step 2: Run test to verify it fails**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-recipes/modules/tool-recipes
python -m pytest tests/test_staged_sub_recipe.py::TestFlatLoopApprovalMirroring -v
```
Expected: FAIL — the flat loop's step-type try block (lines 636-698) only catches `SkipRemainingError` and `CancellationRequestedError`, not `ApprovalGatePausedError`.

**Step 3: Write minimal implementation**

In `modules/tool-recipes/amplifier_module_tool_recipes/executor.py`, in the flat execution loop (the `try` block starting around line 636 that handles step types), add an `except ApprovalGatePausedError` clause after the existing `except SkipRemainingError` at line 693.

Find this block (around lines 693-698):

```python
                except SkipRemainingError:
                    # Skip remaining steps
                    break
                except CancellationRequestedError:
                    # Cancellation requested - save state and re-raise
                    raise
```

Replace with:

```python
                except SkipRemainingError:
                    # Skip remaining steps
                    break
                except ApprovalGatePausedError as e:
                    # Child staged sub-recipe hit an approval gate
                    # Save parent state at current step (don't advance)
                    state = {
                        "session_id": session_id,
                        "recipe_name": recipe.name,
                        "recipe_version": recipe.version,
                        "started": context["session"]["started"],
                        "current_step_index": i,  # Don't advance past this step
                        "context": context,
                        "completed_steps": completed_steps,
                        "project_path": str(project_path.resolve()),
                    }
                    self.session_manager.save_state(session_id, project_path, state)

                    # Mirror child's approval gate on parent session
                    compound_stage = e.stage_name
                    self.session_manager.set_pending_approval(
                        session_id=session_id,
                        project_path=project_path,
                        stage_name=compound_stage,
                        prompt=e.approval_prompt,
                        timeout=0,
                        default="deny",
                    )

                    # Save pending child approval metadata for forwarding
                    meta_state = self.session_manager.load_state(session_id, project_path)
                    meta_state["pending_child_approval"] = {
                        "child_session_id": e.session_id,
                        "child_stage_name": e.stage_name,
                        "parent_step_id": step.id,
                    }
                    self.session_manager.save_state(session_id, project_path, meta_state)

                    # Re-raise with parent's session_id
                    raise ApprovalGatePausedError(
                        session_id=session_id,
                        stage_name=compound_stage,
                        approval_prompt=e.approval_prompt,
                        resume_session_id=e.session_id,
                    ) from e
                except CancellationRequestedError:
                    # Cancellation requested - save state and re-raise
                    raise
```

**Step 4: Run test to verify it passes**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-recipes/modules/tool-recipes
python -m pytest tests/test_staged_sub_recipe.py::TestFlatLoopApprovalMirroring -v
```
Expected: PASS

**Step 5: Run full test suite**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-recipes/modules/tool-recipes
python -m pytest tests/ -v
```
Expected: All tests pass.

**Step 6: Commit**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-recipes
git add modules/tool-recipes/amplifier_module_tool_recipes/executor.py modules/tool-recipes/tests/test_staged_sub_recipe.py
git commit -m "feat: flat execution loop catches child APE and mirrors approval"
```

---

## Task 1.4: Update flat resume path — detect pending child approval

**Files:**
- Modify: `modules/tool-recipes/amplifier_module_tool_recipes/executor.py` (flat resume ~lines 510-524)
- Test: `modules/tool-recipes/tests/test_staged_sub_recipe.py`

**Step 1: Write the failing test**

Append to `modules/tool-recipes/tests/test_staged_sub_recipe.py`:

```python
class TestFlatResumeWithPendingChildApproval:
    """Flat resume path must detect pending_child_approval and handle it."""

    @pytest.mark.asyncio
    async def test_resume_with_approved_child_clears_pending(
        self, mock_coordinator, mock_session_manager, tmp_path
    ):
        """When resuming and child approval is APPROVED, clear pending and inject message."""
        from amplifier_module_tool_recipes.session import ApprovalStatus

        # Set up session state as if parent was paused with child pending
        mock_session_manager.load_state.return_value = {
            "session_id": "parent-session",
            "recipe_name": "flat-parent",
            "recipe_version": "1.0.0",
            "started": "2025-01-01T00:00:00",
            "current_step_index": 0,
            "context": {
                "_child_session_call-child": "child-session-123",
                "session": {"id": "parent-session", "started": "2025-01-01T00:00:00", "project": str(tmp_path)},
                "recipe": {"name": "flat-parent", "version": "1.0.0", "description": ""},
            },
            "completed_steps": [],
            "project_path": str(tmp_path),
            "pending_child_approval": {
                "child_session_id": "child-session-123",
                "child_stage_name": "work",
                "parent_step_id": "call-child",
            },
            "_approval_message": "looks good",
        }

        # Pending approval exists and is APPROVED
        mock_session_manager.get_pending_approval.return_value = {
            "stage_name": "work",
            "approval_prompt": "Approve?",
        }
        mock_session_manager.get_stage_approval_status.return_value = ApprovalStatus.APPROVED
        mock_session_manager.check_approval_timeout.return_value = None

        parent_recipe = Recipe(
            name="flat-parent",
            description="Flat parent",
            version="1.0.0",
            steps=[
                Step(
                    id="call-child",
                    type="recipe",
                    recipe="staged-child.yaml",
                    step_context={},
                ),
            ],
            context={},
        )

        # Write a dummy staged-child recipe
        (tmp_path / "staged-child.yaml").write_text("""
name: staged-child
version: "1.0.0"
stages:
  - name: "work"
    steps:
      - id: work
        agent: test-agent
        prompt: "Work"
""")

        executor = RecipeExecutor(mock_coordinator, mock_session_manager)

        # Mock _execute_recipe_step to succeed on resume (child completes)
        with patch.object(executor, "_execute_recipe_step", new_callable=AsyncMock) as mock_step:
            mock_step.return_value = {"result": "done"}

            result = await executor.execute_recipe(
                parent_recipe, {}, tmp_path,
                session_id="parent-session",
                recipe_path=tmp_path / "parent.yaml",
            )

        # Pending approval should have been cleared
        mock_session_manager.clear_pending_approval.assert_called()
```

**Step 2: Run test to verify it fails**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-recipes/modules/tool-recipes
python -m pytest tests/test_staged_sub_recipe.py::TestFlatResumeWithPendingChildApproval -v
```
Expected: FAIL — the flat resume path (lines 510-524) doesn't check for `pending_child_approval`.

**Step 3: Write minimal implementation**

In `modules/tool-recipes/amplifier_module_tool_recipes/executor.py`, in the flat recipe state loading section (around lines 510-524), add pending child approval handling after the state is loaded.

Find this block (around lines 510-524):

```python
        # Flat recipe state loading (uses current_step_index)
        if is_resuming:
            state = self.session_manager.load_state(session_id, project_path)
            current_step_index = state["current_step_index"]
            context = state["context"]
            completed_steps = state.get("completed_steps", [])
            session_started = state["started"]
```

Replace with:

```python
        # Flat recipe state loading (uses current_step_index)
        if is_resuming:
            state = self.session_manager.load_state(session_id, project_path)
            current_step_index = state["current_step_index"]
            context = state["context"]
            completed_steps = state.get("completed_steps", [])
            session_started = state["started"]

            # Check for pending child approval (from staged sub-recipe composition)
            pending_child = state.get("pending_child_approval")
            if pending_child:
                pending = self.session_manager.get_pending_approval(
                    session_id, project_path
                )
                if pending:
                    approval_status = self.session_manager.get_stage_approval_status(
                        session_id, project_path, pending["stage_name"]
                    )

                    timeout_result = self.session_manager.check_approval_timeout(
                        session_id, project_path
                    )
                    if timeout_result == ApprovalStatus.TIMEOUT:
                        raise ValueError(
                            f"Approval for child stage '{pending['stage_name']}' timed out"
                        )
                    if timeout_result == ApprovalStatus.APPROVED:
                        approval_status = ApprovalStatus.APPROVED

                    if approval_status == ApprovalStatus.PENDING:
                        raise ApprovalGatePausedError(
                            session_id=session_id,
                            stage_name=pending["stage_name"],
                            approval_prompt=pending["approval_prompt"],
                        )
                    elif approval_status == ApprovalStatus.DENIED:
                        raise ValueError(
                            f"Execution denied at child stage '{pending['stage_name']}'"
                        )
                    elif approval_status == ApprovalStatus.APPROVED:
                        # Clear pending approval and inject message
                        self.session_manager.clear_pending_approval(
                            session_id, project_path
                        )
                        # Reload state after clearing
                        state = self.session_manager.load_state(session_id, project_path)
                        context["_approval_message"] = state.get("_approval_message", "")
                        # Clear the pending_child_approval metadata
                        state.pop("pending_child_approval", None)
                        self.session_manager.save_state(session_id, project_path, state)
```

**Step 4: Run test to verify it passes**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-recipes/modules/tool-recipes
python -m pytest tests/test_staged_sub_recipe.py::TestFlatResumeWithPendingChildApproval -v
```
Expected: PASS

**Step 5: Run full test suite**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-recipes/modules/tool-recipes
python -m pytest tests/ -v
```
Expected: All tests pass.

**Step 6: Commit**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-recipes
git add modules/tool-recipes/amplifier_module_tool_recipes/executor.py modules/tool-recipes/tests/test_staged_sub_recipe.py
git commit -m "feat: flat resume path handles pending child approval"
```

---

## Task 1.5: Update staged execution loop — catch child APE

**Files:**
- Modify: `modules/tool-recipes/amplifier_module_tool_recipes/executor.py` (staged loop ~lines 912-970)
- Test: `modules/tool-recipes/tests/test_staged_sub_recipe.py`

**Step 1: Write the failing test**

Append to `modules/tool-recipes/tests/test_staged_sub_recipe.py`:

```python
class TestStagedLoopApprovalMirroring:
    """Staged execution loop must catch child APE with compound stage names."""

    @pytest.mark.asyncio
    async def test_staged_parent_mirrors_child_approval_with_compound_name(
        self, mock_coordinator, mock_session_manager, tmp_path
    ):
        """When staged parent's recipe step child raises APE, use compound stage name."""
        from amplifier_module_tool_recipes.models import Stage, ApprovalConfig

        sub_recipe_yaml = tmp_path / "staged-child.yaml"
        sub_recipe_yaml.write_text("""
name: staged-child
description: Child with gate
version: "1.0.0"
stages:
  - name: "child-gate"
    steps:
      - id: work
        agent: test-agent
        prompt: "Work"
    approval:
      required: true
      prompt: "Approve child?"
""")

        # Create a staged parent recipe
        parent_recipe = Recipe(
            name="staged-parent",
            description="Staged parent calling staged child",
            version="1.0.0",
            stages=[
                Stage(
                    name="parent-stage",
                    steps=[
                        Step(
                            id="call-child",
                            type="recipe",
                            recipe="staged-child.yaml",
                            step_context={},
                        ),
                    ],
                ),
            ],
            context={},
        )

        executor = RecipeExecutor(mock_coordinator, mock_session_manager)

        child_ape = ApprovalGatePausedError(
            session_id="child-session-staged",
            stage_name="child-gate",
            approval_prompt="Approve child?",
        )

        with patch.object(
            executor, "_execute_recipe_step", new_callable=AsyncMock
        ) as mock_step:
            mock_step.side_effect = child_ape

            with pytest.raises(ApprovalGatePausedError) as exc_info:
                await executor.execute_recipe(
                    parent_recipe, {}, tmp_path,
                    recipe_path=tmp_path / "parent.yaml",
                )

            raised = exc_info.value
            # Compound stage name should include parent context
            assert "child-gate" in raised.stage_name, (
                "Compound stage name should include child's stage name"
            )
            assert raised.session_id != "child-session-staged", (
                "Re-raised APE should use parent's session_id"
            )
```

**Step 2: Run test to verify it fails**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-recipes/modules/tool-recipes
python -m pytest tests/test_staged_sub_recipe.py::TestStagedLoopApprovalMirroring -v
```
Expected: FAIL — the staged loop (lines 912-967) only catches `SkipRemainingError` and `CancellationRequestedError`.

**Step 3: Write minimal implementation**

In `modules/tool-recipes/amplifier_module_tool_recipes/executor.py`, in the staged execution loop's step-type try block (around lines 912-970), add an `except ApprovalGatePausedError` clause.

Find this block (around lines 966-970):

```python
                    except SkipRemainingError:
                        break
                    except CancellationRequestedError:
                        # Cancellation requested - re-raise to outer handler
                        raise
```

Replace with:

```python
                    except SkipRemainingError:
                        break
                    except ApprovalGatePausedError as e:
                        # Child staged sub-recipe hit an approval gate
                        # Save state at current step within current stage
                        self._save_staged_state(
                            session_id,
                            project_path,
                            recipe,
                            context,
                            stage_idx,
                            step_idx,  # Don't advance past this step
                            completed_stages,
                            completed_steps,
                        )

                        # Mirror with compound stage name
                        compound_stage = f"{stage.name}/{e.stage_name}"
                        self.session_manager.set_pending_approval(
                            session_id=session_id,
                            project_path=project_path,
                            stage_name=compound_stage,
                            prompt=e.approval_prompt,
                            timeout=0,
                            default="deny",
                        )

                        # Save pending child approval metadata
                        meta_state = self.session_manager.load_state(
                            session_id, project_path
                        )
                        meta_state["pending_child_approval"] = {
                            "child_session_id": e.session_id,
                            "child_stage_name": e.stage_name,
                            "parent_step_id": step.id,
                        }
                        self.session_manager.save_state(
                            session_id, project_path, meta_state
                        )

                        # Re-raise with parent's session_id and compound name
                        raise ApprovalGatePausedError(
                            session_id=session_id,
                            stage_name=compound_stage,
                            approval_prompt=e.approval_prompt,
                            resume_session_id=e.session_id,
                        ) from e
                    except CancellationRequestedError:
                        # Cancellation requested - re-raise to outer handler
                        raise
```

**Step 4: Run test to verify it passes**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-recipes/modules/tool-recipes
python -m pytest tests/test_staged_sub_recipe.py::TestStagedLoopApprovalMirroring -v
```
Expected: PASS

**Step 5: Update staged resume path**

Also update the staged resume path in `_execute_staged_recipe()` (around lines 769-815) to handle `pending_child_approval`, the same way the flat resume path was updated in Task 1.4. Find the block that checks for pending approvals:

```python
            # Check if we're resuming from a pending approval
            pending = self.session_manager.get_pending_approval(
                session_id, project_path
            )
            if pending:
```

Add pending child detection BEFORE the existing pending approval check. Insert right after `completed_steps = state.get("completed_steps", [])` (line 774):

```python
            completed_steps = state.get("completed_steps", [])

            # Check for pending child approval (from staged sub-recipe composition)
            pending_child = state.get("pending_child_approval")
```

Then in the approval status handling block (around lines 808-815), after the `APPROVED` case clears pending and injects `_approval_message`, also clear `pending_child_approval`:

```python
                elif approval_status == ApprovalStatus.APPROVED:
                    # Approved, clear pending and continue
                    self.session_manager.clear_pending_approval(
                        session_id, project_path
                    )
                    # Inject approval message into context for subsequent steps
                    state = self.session_manager.load_state(session_id, project_path)
                    context["_approval_message"] = state.get("_approval_message", "")
                    # Clear pending child metadata if present
                    if pending_child:
                        state.pop("pending_child_approval", None)
                        self.session_manager.save_state(session_id, project_path, state)
```

**Step 6: Run full test suite**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-recipes/modules/tool-recipes
python -m pytest tests/ -v
```
Expected: All tests pass.

**Step 7: Commit**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-recipes
git add modules/tool-recipes/amplifier_module_tool_recipes/executor.py modules/tool-recipes/tests/test_staged_sub_recipe.py
git commit -m "feat: staged execution loop catches child APE with compound stage names"
```

---

## Task 1.6: Add approval forwarding helpers to `__init__.py`

**Files:**
- Modify: `modules/tool-recipes/amplifier_module_tool_recipes/__init__.py`
- Test: `modules/tool-recipes/tests/test_staged_sub_recipe.py`

**Step 1: Write the failing test**

Append to `modules/tool-recipes/tests/test_staged_sub_recipe.py`:

```python
class TestApprovalForwarding:
    """Approval forwarding must recursively propagate to child sessions."""

    def test_forward_approval_sets_child_status(
        self, mock_session_manager, tmp_path
    ):
        """_forward_approval sets APPROVED on child and clears parent metadata."""
        from amplifier_module_tool_recipes import RecipesTool
        from amplifier_module_tool_recipes.session import ApprovalStatus

        coordinator = MagicMock()
        coordinator.session_state = {}
        coordinator.get_capability.return_value = None

        tool = RecipesTool.__new__(RecipesTool)
        tool.coordinator = coordinator
        tool.session_manager = mock_session_manager
        tool.executor = MagicMock()

        # Parent state has pending_child_approval
        parent_state = {
            "pending_child_approval": {
                "child_session_id": "child-sess",
                "child_stage_name": "child-stage",
                "parent_step_id": "step-1",
            },
            "_approval_message": "ship it",
        }
        # Child state has no further children
        child_state = {}

        def load_state_side_effect(sid, pp):
            if sid == "parent-sess":
                return parent_state.copy()
            return child_state.copy()

        mock_session_manager.load_state.side_effect = load_state_side_effect
        mock_session_manager.session_exists.return_value = True

        tool._forward_approval(
            session_id="parent-sess",
            project_path=tmp_path,
            message="ship it",
        )

        # Child should have been approved
        mock_session_manager.set_stage_approval_status.assert_called()
        call_args = mock_session_manager.set_stage_approval_status.call_args
        assert call_args.kwargs["session_id"] == "child-sess"
        assert call_args.kwargs["status"] == ApprovalStatus.APPROVED

    def test_forward_denial_sets_child_denied(
        self, mock_session_manager, tmp_path
    ):
        """_forward_denial sets DENIED on child."""
        from amplifier_module_tool_recipes import RecipesTool
        from amplifier_module_tool_recipes.session import ApprovalStatus

        coordinator = MagicMock()
        coordinator.session_state = {}
        coordinator.get_capability.return_value = None

        tool = RecipesTool.__new__(RecipesTool)
        tool.coordinator = coordinator
        tool.session_manager = mock_session_manager
        tool.executor = MagicMock()

        parent_state = {
            "pending_child_approval": {
                "child_session_id": "child-sess",
                "child_stage_name": "child-stage",
                "parent_step_id": "step-1",
            },
        }
        child_state = {}

        def load_state_side_effect(sid, pp):
            if sid == "parent-sess":
                return parent_state.copy()
            return child_state.copy()

        mock_session_manager.load_state.side_effect = load_state_side_effect
        mock_session_manager.session_exists.return_value = True

        tool._forward_denial(
            session_id="parent-sess",
            project_path=tmp_path,
            reason="not ready",
        )

        mock_session_manager.set_stage_approval_status.assert_called()
        call_args = mock_session_manager.set_stage_approval_status.call_args
        assert call_args.kwargs["session_id"] == "child-sess"
        assert call_args.kwargs["status"] == ApprovalStatus.DENIED
```

**Step 2: Run test to verify it fails**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-recipes/modules/tool-recipes
python -m pytest tests/test_staged_sub_recipe.py::TestApprovalForwarding -v
```
Expected: FAIL — `RecipesTool` has no `_forward_approval` or `_forward_denial` methods.

**Step 3: Write minimal implementation**

In `modules/tool-recipes/amplifier_module_tool_recipes/__init__.py`, add these two methods to the `RecipesTool` class (add them after the `_deny_stage` method, around line 797):

```python
    def _forward_approval(
        self,
        session_id: str,
        project_path: Path,
        message: str = "",
    ) -> None:
        """Forward approval recursively to child sessions.

        When a parent session has a mirrored child approval gate,
        this forwards the approval down to the child (and any grandchild).

        Args:
            session_id: Parent session ID
            project_path: Project directory
            message: Approval message to propagate
        """
        state = self.session_manager.load_state(session_id, project_path)
        pending_child = state.get("pending_child_approval")
        if not pending_child:
            return

        child_session_id = pending_child["child_session_id"]
        child_stage_name = pending_child["child_stage_name"]

        # Set child's approval status to APPROVED
        self.session_manager.set_stage_approval_status(
            session_id=child_session_id,
            project_path=project_path,
            stage_name=child_stage_name,
            status=ApprovalStatus.APPROVED,
            reason="Forwarded from parent approval",
        )

        # Propagate approval message to child
        if self.session_manager.session_exists(child_session_id, project_path):
            child_state = self.session_manager.load_state(child_session_id, project_path)
            child_state["_approval_message"] = message
            self.session_manager.save_state(child_session_id, project_path, child_state)

            # Recurse: if child also has a pending child, forward there too
            if child_state.get("pending_child_approval"):
                self._forward_approval(child_session_id, project_path, message)

        # Clear parent's pending_child_approval metadata
        state.pop("pending_child_approval", None)
        self.session_manager.save_state(session_id, project_path, state)

    def _forward_denial(
        self,
        session_id: str,
        project_path: Path,
        reason: str = "Denied by user",
    ) -> None:
        """Forward denial recursively to child sessions.

        Args:
            session_id: Parent session ID
            project_path: Project directory
            reason: Denial reason to propagate
        """
        state = self.session_manager.load_state(session_id, project_path)
        pending_child = state.get("pending_child_approval")
        if not pending_child:
            return

        child_session_id = pending_child["child_session_id"]
        child_stage_name = pending_child["child_stage_name"]

        # Set child's approval status to DENIED
        self.session_manager.set_stage_approval_status(
            session_id=child_session_id,
            project_path=project_path,
            stage_name=child_stage_name,
            status=ApprovalStatus.DENIED,
            reason=reason,
        )

        # Clear child's pending approval
        if self.session_manager.session_exists(child_session_id, project_path):
            self.session_manager.clear_pending_approval(child_session_id, project_path)

            # Recurse: if child also has a pending child, deny there too
            child_state = self.session_manager.load_state(child_session_id, project_path)
            if child_state.get("pending_child_approval"):
                self._forward_denial(child_session_id, project_path, reason)

        # Clear parent's pending_child_approval metadata
        state.pop("pending_child_approval", None)
        self.session_manager.save_state(session_id, project_path, state)
```

**Step 4: Run test to verify it passes**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-recipes/modules/tool-recipes
python -m pytest tests/test_staged_sub_recipe.py::TestApprovalForwarding -v
```
Expected: PASS (2 tests)

**Step 5: Commit**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-recipes
git add modules/tool-recipes/amplifier_module_tool_recipes/__init__.py modules/tool-recipes/tests/test_staged_sub_recipe.py
git commit -m "feat: add _forward_approval and _forward_denial helpers"
```

---

## Task 1.7: Wire forwarding into `_approve_stage` and `_deny_stage`

**Files:**
- Modify: `modules/tool-recipes/amplifier_module_tool_recipes/__init__.py:654-797`
- Test: `modules/tool-recipes/tests/test_staged_sub_recipe.py`

**Step 1: Write the failing test**

Append to `modules/tool-recipes/tests/test_staged_sub_recipe.py`:

```python
class TestApproveStageForwardsToChild:
    """_approve_stage must call _forward_approval when pending_child_approval exists."""

    @pytest.mark.asyncio
    async def test_approve_calls_forward(self, mock_session_manager, tmp_path):
        """Approving a parent stage with child metadata calls _forward_approval."""
        from amplifier_module_tool_recipes import RecipesTool

        coordinator = MagicMock()
        coordinator.session_state = {}
        coordinator.get_capability.return_value = None

        tool = RecipesTool.__new__(RecipesTool)
        tool.coordinator = coordinator
        tool.session_manager = mock_session_manager
        tool.executor = MagicMock()
        tool._get_working_dir = MagicMock(return_value=tmp_path)

        mock_session_manager.session_exists.return_value = True
        mock_session_manager.get_pending_approval.return_value = {
            "stage_name": "parent-stage/child-gate",
            "approval_prompt": "Approve?",
        }

        # State has pending_child_approval
        mock_session_manager.load_state.return_value = {
            "pending_child_approval": {
                "child_session_id": "child-123",
                "child_stage_name": "child-gate",
                "parent_step_id": "call-child",
            },
            "_approval_message": "",
        }

        with patch.object(tool, "_forward_approval") as mock_forward:
            result = await tool._approve_stage({
                "session_id": "parent-sess",
                "stage_name": "parent-stage/child-gate",
                "message": "go ahead",
            })

        assert result.success is True
        mock_forward.assert_called_once_with(
            session_id="parent-sess",
            project_path=tmp_path,
            message="go ahead",
        )
```

**Step 2: Run test to verify it fails**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-recipes/modules/tool-recipes
python -m pytest tests/test_staged_sub_recipe.py::TestApproveStageForwardsToChild -v
```
Expected: FAIL — `_approve_stage` does not call `_forward_approval`.

**Step 3: Write minimal implementation**

In `modules/tool-recipes/amplifier_module_tool_recipes/__init__.py`, in the `_approve_stage` method, add a call to `_forward_approval` after the existing approval logic. Find the success return block (around lines 712-726):

```python
            # Store the approval message in session state so the executor
            # can inject it into the recipe context on resume
            state = self.session_manager.load_state(session_id, project_path)
            state["_approval_message"] = message
            self.session_manager.save_state(session_id, project_path, state)

            return ToolResult(
```

Insert BEFORE the `return ToolResult(` line:

```python
            # Forward approval to child session if this is a mirrored child gate
            if state.get("pending_child_approval"):
                self._forward_approval(
                    session_id=session_id,
                    project_path=project_path,
                    message=message,
                )
```

Similarly, in `_deny_stage`, find where it clears the pending approval (around line 781):

```python
            # Clear the pending approval
            self.session_manager.clear_pending_approval(session_id, project_path)
```

Insert BEFORE the clear:

```python
            # Forward denial to child session if this is a mirrored child gate
            state = self.session_manager.load_state(session_id, project_path)
            if state.get("pending_child_approval"):
                self._forward_denial(
                    session_id=session_id,
                    project_path=project_path,
                    reason=reason,
                )
```

**Step 4: Run test to verify it passes**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-recipes/modules/tool-recipes
python -m pytest tests/test_staged_sub_recipe.py::TestApproveStageForwardsToChild -v
```
Expected: PASS

**Step 5: Run full test suite**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-recipes/modules/tool-recipes
python -m pytest tests/ -v
```
Expected: All tests pass.

**Step 6: Commit**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-recipes
git add modules/tool-recipes/amplifier_module_tool_recipes/__init__.py modules/tool-recipes/tests/test_staged_sub_recipe.py
git commit -m "feat: wire approval/denial forwarding into _approve_stage and _deny_stage"
```

---

## Task 1.8: Update tool-level APE handlers for `resume_session_id`

**Files:**
- Modify: `modules/tool-recipes/amplifier_module_tool_recipes/__init__.py:451-463,539-551`
- Test: `modules/tool-recipes/tests/test_staged_sub_recipe.py`

**Step 1: Write the failing test**

Append to `modules/tool-recipes/tests/test_staged_sub_recipe.py`:

```python
class TestToolLevelAPEReporting:
    """Tool-level APE handlers should report resume_session_id when present."""

    @pytest.mark.asyncio
    async def test_execute_reports_resume_session_id(self, tmp_path):
        """When APE has resume_session_id, report it in tool result."""
        from amplifier_module_tool_recipes import RecipesTool
        from amplifier_core import ToolResult

        coordinator = MagicMock()
        coordinator.session_state = {}
        coordinator.get_capability.return_value = None

        tool = RecipesTool.__new__(RecipesTool)
        tool.coordinator = coordinator
        tool.session_manager = MagicMock()
        tool.executor = MagicMock()
        tool._get_working_dir = MagicMock(return_value=tmp_path)
        tool._resolve_path = MagicMock(return_value=tmp_path / "recipe.yaml")

        # Create a minimal recipe file
        recipe_yaml = tmp_path / "recipe.yaml"
        recipe_yaml.write_text("""
name: test
description: test
version: "1.0.0"
steps:
  - id: s1
    agent: a
    prompt: p
""")

        from amplifier_module_tool_recipes.validator import ValidationResult
        with patch("amplifier_module_tool_recipes.validate_recipe") as mock_validate:
            mock_validate.return_value = ValidationResult(is_valid=True, errors=[], warnings=[])

            ape = ApprovalGatePausedError(
                session_id="parent-sess",
                stage_name="gate",
                approval_prompt="Approve?",
                resume_session_id="child-sess",
            )
            tool.executor.execute_recipe = AsyncMock(side_effect=ape)

            result = await tool._execute_recipe({"recipe_path": "@test:recipe.yaml"})

        assert result.success is True
        assert result.output["session_id"] == "parent-sess", (
            "Should report parent session_id as the primary session"
        )
```

**Step 2: Run test to verify it fails**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-recipes/modules/tool-recipes
python -m pytest tests/test_staged_sub_recipe.py::TestToolLevelAPEReporting -v
```
Expected: FAIL or PASS depending on whether `e.session_id` already resolves to parent. Verify behavior and adjust as needed.

**Step 3: Implementation note**

The existing APE handlers at lines 451-463 and 539-551 already use `e.session_id`, which will be the parent's session_id after our changes (since we re-raise with parent's id in the execution loops). No code changes may be needed here — the test confirms the behavior. If the test passes without changes, skip to Step 5.

If the test fails because `e.session_id` is not the parent's, update both APE handlers to check for `e.resume_session_id`:

In both `_execute_recipe` (line 458) and `_resume_recipe` (line 546), the `session_id` in the output should use `e.session_id` (which is already the parent's). The `resume_session_id` can optionally be included in the output for observability.

**Step 4: Run test to verify it passes**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-recipes/modules/tool-recipes
python -m pytest tests/test_staged_sub_recipe.py::TestToolLevelAPEReporting -v
```
Expected: PASS

**Step 5: Commit**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-recipes
git add modules/tool-recipes/amplifier_module_tool_recipes/__init__.py modules/tool-recipes/tests/test_staged_sub_recipe.py
git commit -m "test: verify tool-level APE handlers report correct session_id"
```

---

## Task 1.9: Add validator warning for parallel foreach + recipe steps

**Files:**
- Modify: `modules/tool-recipes/amplifier_module_tool_recipes/validator.py`
- Test: `modules/tool-recipes/tests/test_staged_sub_recipe.py`

**Step 1: Write the failing test**

Append to `modules/tool-recipes/tests/test_staged_sub_recipe.py`:

```python
from amplifier_module_tool_recipes.validator import validate_recipe


class TestValidatorParallelRecipeWarning:
    """Validator should warn on parallel: true foreach over recipe steps."""

    def test_parallel_foreach_with_recipe_step_warns(self):
        """parallel foreach containing a recipe step should produce a warning."""
        recipe = Recipe(
            name="parallel-recipe-test",
            description="Test",
            version="1.0.0",
            steps=[
                Step(
                    id="parallel-recipes",
                    agent="test-agent",
                    prompt="ignored",
                    foreach="{{items}}",
                    parallel=True,
                    type="recipe",
                    recipe="child.yaml",
                ),
            ],
            context={"items": []},
        )

        result = validate_recipe(recipe)
        assert any("parallel" in w.lower() and "recipe" in w.lower() for w in result.warnings), (
            f"Expected a warning about parallel foreach with recipe steps, got: {result.warnings}"
        )

    def test_parallel_foreach_without_recipe_no_warning(self):
        """parallel foreach with agent steps should NOT produce this warning."""
        recipe = Recipe(
            name="parallel-agent-test",
            description="Test",
            version="1.0.0",
            steps=[
                Step(
                    id="parallel-agents",
                    agent="test-agent",
                    prompt="Do work with {{item}}",
                    foreach="{{items}}",
                    parallel=True,
                ),
            ],
            context={"items": []},
        )

        result = validate_recipe(recipe)
        parallel_recipe_warnings = [
            w for w in result.warnings
            if "parallel" in w.lower() and "recipe" in w.lower()
        ]
        assert len(parallel_recipe_warnings) == 0, (
            f"Should not warn for parallel agent steps: {parallel_recipe_warnings}"
        )
```

**Step 2: Run test to verify it fails**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-recipes/modules/tool-recipes
python -m pytest tests/test_staged_sub_recipe.py::TestValidatorParallelRecipeWarning -v
```
Expected: FAIL — no such warning exists.

**Step 3: Write minimal implementation**

In `modules/tool-recipes/amplifier_module_tool_recipes/validator.py`, in the `validate_recipe` function (around lines 19-56), add a check for parallel foreach + recipe steps. Add this block after the dependency validation (around line 48):

```python
    # Check for parallel foreach with recipe steps (approval gates undefined in parallel)
    all_steps = list(recipe.steps)
    if recipe.stages:
        for stage in recipe.stages:
            all_steps.extend(stage.steps)

    for step in all_steps:
        if step.foreach and step.parallel and step.type == "recipe":
            warnings.append(
                f"Step '{step.id}': parallel foreach with type='recipe' may cause issues "
                f"if the sub-recipe has approval gates (parallel approval gates are undefined behavior)"
            )
```

**Step 4: Run test to verify it passes**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-recipes/modules/tool-recipes
python -m pytest tests/test_staged_sub_recipe.py::TestValidatorParallelRecipeWarning -v
```
Expected: PASS (2 tests)

**Step 5: Run full test suite**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-recipes/modules/tool-recipes
python -m pytest tests/ -v
```
Expected: All tests pass.

**Step 6: Commit**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-recipes
git add modules/tool-recipes/amplifier_module_tool_recipes/validator.py modules/tool-recipes/tests/test_staged_sub_recipe.py
git commit -m "feat: validator warns on parallel foreach with recipe steps"
```

---

# Work Stream 2: Mode @-mention Fix

**Repo:** `/home/bkrabach/dev/superpowers-3/amplifier-bundle-modes`
**Branch:** `feature/mode-mention-resolution`
**Source:** `modules/hooks-mode/amplifier_module_hooks_mode/`
**Tests:** `modules/hooks-mode/tests/`
**Run tests from:** `modules/hooks-mode/`

Before starting, create the branch:
```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-modes
git checkout -b feature/mode-mention-resolution
```

---

## Task 2.1: Add @-mention resolution to `handle_provider_request()`

**Files:**
- Modify: `modules/hooks-mode/amplifier_module_hooks_mode/__init__.py:405-429`
- Test: `modules/hooks-mode/tests/test_mention_resolution.py` (create)

**Step 1: Write the failing test**

Create `modules/hooks-mode/tests/test_mention_resolution.py`:

```python
"""Tests for @-mention resolution in mode body content.

Tests cover:
- Mode body with @namespace:path resolves to actual file content
- Mode body without @-mentions works unchanged
- Invalid @-mention path produces graceful error
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from amplifier_module_hooks_mode import ModeDiscovery, ModeHooks


def _create_mode_file(path: Path, name: str, body: str = "") -> Path:
    """Helper: create a mode .md file with given body."""
    mode_file = path / f"{name}.md"
    mode_file.write_text(
        textwrap.dedent(f"""\
            ---
            mode:
              name: {name}
              description: "{name} mode"
              tools:
                safe: [read_file, grep]
              default_action: block
            ---
            {body}
        """),
        encoding="utf-8",
    )
    return mode_file


def _make_coordinator(active_mode: str | None = None) -> MagicMock:
    """Create a mock coordinator with session_state."""
    coordinator = MagicMock()
    coordinator.session_state = {
        "active_mode": active_mode,
        "require_approval_tools": set(),
    }
    coordinator.hooks = MagicMock()
    coordinator.get_capability = MagicMock(return_value=None)
    return coordinator


class TestMentionResolutionInModeBody:
    """@-mentions in mode bodies must be resolved to file content."""

    @pytest.mark.asyncio
    async def test_at_mention_resolved_to_file_content(self, tmp_path: Path) -> None:
        """Mode body with @namespace:path/file.md resolves to actual file content."""
        modes_dir = tmp_path / "modes"
        modes_dir.mkdir()

        # Create the context file that will be @-mentioned
        context_dir = tmp_path / "context"
        context_dir.mkdir()
        context_file = context_dir / "shared.md"
        context_file.write_text("This is shared anti-rationalization content.")

        # Create mode with @-mention in the body
        _create_mode_file(
            modes_dir, "test-mode",
            body="Mode guidance here.\n\n@testbundle:context/shared.md\n\nMore guidance."
        )

        coordinator = _make_coordinator(active_mode="test-mode")

        # Set up mention_resolver to resolve @testbundle:context/shared.md
        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = context_file

        def get_cap(name):
            if name == "mention_resolver":
                return mock_resolver
            return None
        coordinator.get_capability.side_effect = get_cap

        discovery = ModeDiscovery(search_paths=[modes_dir])
        hooks = ModeHooks(coordinator, discovery)

        result = await hooks.handle_provider_request("provider:request", {})

        assert result.action == "inject_context"
        # The resolved content should contain the actual file content
        assert "This is shared anti-rationalization content." in result.context_injection, (
            "Mode body @-mention should be resolved to actual file content"
        )
        # The literal @-mention string should NOT be in the output
        assert "@testbundle:context/shared.md" not in result.context_injection, (
            "Literal @-mention should be replaced, not passed through"
        )

    @pytest.mark.asyncio
    async def test_mode_without_mentions_unchanged(self, tmp_path: Path) -> None:
        """Mode body without @-mentions should work exactly as before."""
        modes_dir = tmp_path / "modes"
        modes_dir.mkdir()

        _create_mode_file(
            modes_dir, "plain-mode",
            body="Just plain guidance with no mentions."
        )

        coordinator = _make_coordinator(active_mode="plain-mode")
        discovery = ModeDiscovery(search_paths=[modes_dir])
        hooks = ModeHooks(coordinator, discovery)

        result = await hooks.handle_provider_request("provider:request", {})

        assert result.action == "inject_context"
        assert "Just plain guidance with no mentions." in result.context_injection

    @pytest.mark.asyncio
    async def test_invalid_mention_graceful_error(self, tmp_path: Path) -> None:
        """Invalid @-mention should not break mode injection."""
        modes_dir = tmp_path / "modes"
        modes_dir.mkdir()

        _create_mode_file(
            modes_dir, "bad-mention-mode",
            body="Before mention.\n\n@nonexistent:missing/file.md\n\nAfter mention."
        )

        coordinator = _make_coordinator(active_mode="bad-mention-mode")

        # Resolver returns None for the bad path
        mock_resolver = MagicMock()
        mock_resolver.resolve.return_value = None

        def get_cap(name):
            if name == "mention_resolver":
                return mock_resolver
            return None
        coordinator.get_capability.side_effect = get_cap

        discovery = ModeDiscovery(search_paths=[modes_dir])
        hooks = ModeHooks(coordinator, discovery)

        # Should NOT raise — mode still works even with bad @-mention
        result = await hooks.handle_provider_request("provider:request", {})

        assert result.action == "inject_context"
        # The remaining content should still be injected
        assert "Before mention." in result.context_injection
        assert "After mention." in result.context_injection
```

**Step 2: Run test to verify it fails**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-modes/modules/hooks-mode
python -m pytest tests/test_mention_resolution.py -v
```
Expected: FAIL — `test_at_mention_resolved_to_file_content` fails because the literal `@testbundle:context/shared.md` is still in the output.

**Step 3: Write minimal implementation**

In `modules/hooks-mode/amplifier_module_hooks_mode/__init__.py`, update the `handle_provider_request` method (lines 405-429). Add @-mention resolution before building the context block.

Replace the current method:

```python
    async def handle_provider_request(self, _event: str, _data: dict) -> "HookResult":
        """Inject mode context on every provider request."""
        from amplifier_core.models import HookResult

        mode = self._get_active_mode()
        if not mode or not mode.context:
            return HookResult(action="continue")

        # Resolve @-mentions in mode body content
        resolved_context = self._resolve_mentions(mode.context)

        # Wrap context in system-reminder tags with explicit MODE ACTIVE banner
        context_block = (
            f'<system-reminder source="mode-{mode.name}">\n'
            f"MODE ACTIVE: {mode.name}\n"
            f"You are CURRENTLY in {mode.name} mode. It is already active — "
            f'do NOT call mode(set, "{mode.name}") to re-activate it. '
            f"Follow the guidance below.\n\n"
            f"{resolved_context}\n"
            f"</system-reminder>"
        )

        return HookResult(
            action="inject_context",
            context_injection=context_block,
            context_injection_role="system",
            ephemeral=True,
        )
```

Then add the helper method `_resolve_mentions` to the `ModeHooks` class:

```python
    def _resolve_mentions(self, content: str) -> str:
        """Resolve @namespace:path mentions in mode body content.

        Scans for lines that are solely an @-mention (e.g., @superpowers:context/file.md)
        and replaces them with the file's content. If resolution fails, removes the
        @-mention line and logs a warning.

        Args:
            content: Raw mode body text

        Returns:
            Content with @-mentions replaced by resolved file content
        """
        if "@" not in content:
            return content

        resolver = None
        if self.coordinator:
            resolver = self.coordinator.get_capability("mention_resolver")

        if not resolver:
            return content

        import re
        # Match lines that are just an @-mention (with optional whitespace)
        mention_pattern = re.compile(r"^\s*(@\S+:\S+)\s*$", re.MULTILINE)

        def replace_mention(match: re.Match) -> str:
            mention = match.group(1)
            try:
                resolved_path = resolver.resolve(mention)
                if resolved_path is None:
                    logger.warning(
                        "Mode @-mention could not be resolved: %s", mention
                    )
                    return ""

                resolved_path = Path(resolved_path)
                if resolved_path.exists() and resolved_path.is_file():
                    file_content = resolved_path.read_text(encoding="utf-8")
                    return file_content
                else:
                    logger.warning(
                        "Mode @-mention resolved to non-existent file: %s -> %s",
                        mention,
                        resolved_path,
                    )
                    return ""
            except Exception as exc:
                logger.warning(
                    "Error resolving mode @-mention %s: %s", mention, exc
                )
                return ""

        return mention_pattern.sub(replace_mention, content)
```

**Step 4: Run test to verify it passes**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-modes/modules/hooks-mode
python -m pytest tests/test_mention_resolution.py -v
```
Expected: PASS (3 tests)

**Step 5: Run full test suite**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-modes/modules/hooks-mode
python -m pytest tests/ -v
```
Expected: All tests pass.

**Step 6: Commit**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-modes
git add modules/hooks-mode/amplifier_module_hooks_mode/__init__.py modules/hooks-mode/tests/test_mention_resolution.py
git commit -m "feat: resolve @-mentions in mode body content before injection"
```

---

# Work Stream 3: Superpowers Bundle Updates

**Repo:** `/home/bkrabach/dev/superpowers-3/amplifier-bundle-superpowers`
**Branch:** `feature/superpowers-update`
**Tests:** `tests/`
**Run tests from:** repo root

Before starting, create the branch:
```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-superpowers
git checkout -b feature/superpowers-update
```

---

## Task 3.1: Flip skill source order in behavior YAML

**Files:**
- Modify: `behaviors/superpowers-methodology.yaml:57-59`
- Test: `tests/test_b4_context_files.py` (or new test)

**Step 1: Write the failing test**

Create `tests/test_skill_strategy.py`:

```python
"""Tests for skill strategy — source ordering and skill count.

Validates:
- Skill source order is ours-first, obra-second
- Only 2 Amplifier-specific skills remain
- No Claude Code contamination
"""

import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
BEHAVIOR_FILE = REPO_ROOT / "behaviors" / "superpowers-methodology.yaml"
SKILLS_DIR = REPO_ROOT / "skills"


class TestSkillSourceOrder:
    """Skill source order must be ours first, obra second."""

    def test_our_skills_listed_first(self):
        """In the skills config, our bundle's skills must come before obra's."""
        content = BEHAVIOR_FILE.read_text()
        data = yaml.safe_load(content)

        # Find skills config in tools
        skills_config = None
        for tool in data.get("tools", []):
            if tool.get("module") == "tool-skills":
                skills_config = tool.get("config", {}).get("skills", [])
                break

        assert skills_config is not None, "tool-skills config not found in behavior YAML"
        assert len(skills_config) >= 2, "Expected at least 2 skill sources"

        # Our bundle should be first (wins on collision)
        assert "microsoft/amplifier-bundle-superpowers" in skills_config[0], (
            f"First skill source should be ours, got: {skills_config[0]}"
        )
        assert "obra/superpowers" in skills_config[1], (
            f"Second skill source should be obra's, got: {skills_config[1]}"
        )
```

**Step 2: Run test to verify it fails**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-superpowers
python -m pytest tests/test_skill_strategy.py::TestSkillSourceOrder -v
```
Expected: FAIL — currently obra's is first (line 58), ours is second (line 59).

**Step 3: Write minimal implementation**

In `behaviors/superpowers-methodology.yaml`, swap lines 58 and 59. Change:

```yaml
      skills:
        - "git+https://github.com/obra/superpowers@main#subdirectory=skills"
        - "git+https://github.com/microsoft/amplifier-bundle-superpowers@main#subdirectory=skills"
```

To:

```yaml
      skills:
        - "git+https://github.com/microsoft/amplifier-bundle-superpowers@main#subdirectory=skills"
        - "git+https://github.com/obra/superpowers@main#subdirectory=skills"
```

**Step 4: Run test to verify it passes**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-superpowers
python -m pytest tests/test_skill_strategy.py::TestSkillSourceOrder -v
```
Expected: PASS

**Step 5: Commit**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-superpowers
git add behaviors/superpowers-methodology.yaml tests/test_skill_strategy.py
git commit -m "feat: flip skill source order — ours first, obra second"
```

---

## Task 3.2: Remove 5 skill directories

**Files:**
- Delete: `skills/systematic-debugging/`
- Delete: `skills/verification-before-completion/`
- Delete: `skills/finishing-a-development-branch/`
- Delete: `skills/code-review-reception/`
- Delete: `skills/parallel-agent-dispatch/`
- Test: `tests/test_skill_strategy.py`

**Step 1: Write the failing test**

Append to `tests/test_skill_strategy.py`:

```python
class TestSkillCount:
    """Only 2 Amplifier-specific skills should remain."""

    EXPECTED_SKILLS = {"integration-testing-discipline", "superpowers-reference"}
    REMOVED_SKILLS = {
        "systematic-debugging",
        "verification-before-completion",
        "finishing-a-development-branch",
        "code-review-reception",
        "parallel-agent-dispatch",
    }

    def test_only_two_skills_remain(self):
        """skills/ directory should contain exactly 2 skill directories."""
        if not SKILLS_DIR.exists():
            pytest.fail("skills/ directory does not exist")

        skill_dirs = {d.name for d in SKILLS_DIR.iterdir() if d.is_dir()}
        assert skill_dirs == self.EXPECTED_SKILLS, (
            f"Expected exactly {self.EXPECTED_SKILLS}, got {skill_dirs}"
        )

    def test_removed_skills_not_present(self):
        """Removed skills must not exist."""
        for skill_name in self.REMOVED_SKILLS:
            skill_path = SKILLS_DIR / skill_name
            assert not skill_path.exists(), (
                f"Skill should be removed but still exists: {skill_path}"
            )
```

**Step 2: Run test to verify it fails**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-superpowers
python -m pytest tests/test_skill_strategy.py::TestSkillCount -v
```
Expected: FAIL — 7 skill directories currently exist.

**Step 3: Remove the 5 skill directories**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-superpowers
rm -rf skills/systematic-debugging
rm -rf skills/verification-before-completion
rm -rf skills/finishing-a-development-branch
rm -rf skills/code-review-reception
rm -rf skills/parallel-agent-dispatch
```

**Step 4: Run test to verify it passes**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-superpowers
python -m pytest tests/test_skill_strategy.py::TestSkillCount -v
```
Expected: PASS (2 tests)

**Step 5: Commit**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-superpowers
git add -A skills/
git add tests/test_skill_strategy.py
git commit -m "feat: remove 5 skills where obra's versions are equal or better"
```

---

## Task 3.3: Create shared anti-rationalization context file

**Files:**
- Create: `context/shared-anti-rationalization.md`
- Test: `tests/test_skill_strategy.py`

**Step 1: Write the failing test**

Append to `tests/test_skill_strategy.py`:

```python
class TestSharedAntiRationalization:
    """Shared anti-rationalization context file must exist with required content."""

    SHARED_FILE = REPO_ROOT / "context" / "shared-anti-rationalization.md"

    def test_file_exists(self):
        """shared-anti-rationalization.md must exist in context/."""
        assert self.SHARED_FILE.exists(), (
            "context/shared-anti-rationalization.md must exist"
        )

    def test_has_spirit_vs_letter(self):
        """Must contain 'spirit vs letter' inoculation."""
        content = self.SHARED_FILE.read_text()
        assert "spirit" in content.lower() and "letter" in content.lower(), (
            "Must contain spirit vs letter anti-rationalization content"
        )

    def test_has_yagni(self):
        """Must contain YAGNI reminder."""
        content = self.SHARED_FILE.read_text()
        assert "YAGNI" in content, "Must contain YAGNI reminder"

    def test_has_false_completion(self):
        """Must contain false completion prevention."""
        content = self.SHARED_FILE.read_text()
        assert "complete" in content.lower(), (
            "Must contain false-completion prevention content"
        )
```

**Step 2: Run test to verify it fails**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-superpowers
python -m pytest tests/test_skill_strategy.py::TestSharedAntiRationalization -v
```
Expected: FAIL — file does not exist.

**Step 3: Create the file**

Create `context/shared-anti-rationalization.md`:

```markdown
# Anti-Rationalization — Cross-Phase Reminders

These reminders apply in EVERY workflow phase. Your brain will try to skip them. It's wrong.

## Spirit vs Letter

**Violating the letter of a process rule IS violating the spirit.**

When you think "this technically satisfies the requirement but..." — you're rationalizing. The process exists because the shortcut you're considering has been tried before and failed. Follow the process as written.

Common rationalizations:
- "The spirit is what matters, not the exact steps" — The steps ARE the spirit. They encode hard-won lessons.
- "This is different because..." — It's not different. The rule applies.
- "I'll do it properly next time" — There is no next time. Do it now.

## YAGNI — Ruthless Scope Control

You Aren't Gonna Need It. Every feature, abstraction, and "improvement" must justify its existence RIGHT NOW, not in some imagined future.

- Don't add "while I'm here" improvements
- Don't build for hypothetical future requirements
- Don't add abstractions "in case we need to change it later"
- Don't optimize before measuring

If the spec doesn't require it, don't build it. If the plan doesn't mention it, don't add it.

## False Completion Prevention

"Done" means verified, not "I think it works." Before claiming completion:

1. Did you run the FULL test suite? (Not a subset. Not "the relevant tests.")
2. Did you verify the specific behavior works? (Not "the tests pass." The actual behavior.)
3. Did you check for regressions? (Not "I don't think anything else is affected.")

If you haven't done all three, you're not done. You're hoping.

## The Three-Fix Escalation

If you've attempted 3+ fixes for the same issue:
- STOP fixing symptoms
- Question the architecture
- Discuss with the user before attempting more fixes

Three failures means you're working at the wrong level of abstraction.
```

**Step 4: Run test to verify it passes**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-superpowers
python -m pytest tests/test_skill_strategy.py::TestSharedAntiRationalization -v
```
Expected: PASS (4 tests)

**Step 5: Commit**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-superpowers
git add context/shared-anti-rationalization.md tests/test_skill_strategy.py
git commit -m "feat: create shared anti-rationalization context file"
```

---

## Task 3.4: Enrich `modes/brainstorm.md`

**Files:**
- Modify: `modes/brainstorm.md`
- Test: `tests/test_modes_adherence.py` (update)

**Step 1: Write the failing test**

Append to `tests/test_modes_adherence.py`:

```python
class TestModeContentEnrichment:
    """Modes must contain obra's latest methodology content."""

    def test_brainstorm_has_architecture_guidance(self) -> None:
        """brainstorm.md must contain architecture guidance."""
        content = _read_mode("brainstorm.md")
        assert "isolation" in content.lower() or "testability" in content.lower(), (
            "brainstorm.md must contain architecture guidance (isolation, testability)"
        )

    def test_brainstorm_has_scope_assessment(self) -> None:
        """brainstorm.md must contain scope assessment guidance."""
        content = _read_mode("brainstorm.md")
        assert "scope" in content.lower(), (
            "brainstorm.md must contain scope assessment guidance"
        )

    def test_brainstorm_has_shared_anti_rationalization_mention(self) -> None:
        """brainstorm.md must @-mention the shared anti-rationalization file."""
        content = _read_mode("brainstorm.md")
        assert "@superpowers:context/shared-anti-rationalization.md" in content, (
            "brainstorm.md must @-mention shared-anti-rationalization.md"
        )
```

**Step 2: Run test to verify it fails**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-superpowers
python -m pytest tests/test_modes_adherence.py::TestModeContentEnrichment::test_brainstorm_has_architecture_guidance -v
python -m pytest tests/test_modes_adherence.py::TestModeContentEnrichment::test_brainstorm_has_shared_anti_rationalization_mention -v
```
Expected: FAIL — brainstorm.md doesn't have architecture guidance or the @-mention yet.

**Step 3: Write minimal implementation**

In `modes/brainstorm.md`, add the following content. Insert BEFORE the `## Anti-Rationalization Table` section (before line 127):

```markdown
## Architecture Guidance

When exploring approaches in Phase 3, evaluate each against these principles:
- **Design for isolation** — Components should be independently testable and replaceable
- **Minimize interfaces** — Fewer connection points between components means fewer bugs and easier changes
- **Prefer composition over inheritance** — Small, composable pieces beat deep hierarchies
- **Design for testability** — If it's hard to test, it's hard to use. Listen to the test friction.

## Scope Assessment

Before diving into detailed design, assess the project scope:
- **Single-subsystem change?** One component, contained blast radius → streamlined design conversation
- **Multi-subsystem change?** Multiple components, cross-cutting concerns → thorough dependency mapping
- **New system?** Greenfield → extra emphasis on interface design and boundary definition

Match the depth of the design conversation to the scope. A 20-line utility doesn't need the same design process as a multi-repo refactor — but it DOES still go through the phases.

## Cross-Phase Reminders

@superpowers:context/shared-anti-rationalization.md
```

**Step 4: Run test to verify it passes**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-superpowers
python -m pytest tests/test_modes_adherence.py::TestModeContentEnrichment -v
```
Expected: PASS (3 tests)

**Step 5: Run full test suite to check for regressions**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-superpowers
python -m pytest tests/ -v
```
Expected: All tests pass.

**Step 6: Commit**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-superpowers
git add modes/brainstorm.md tests/test_modes_adherence.py
git commit -m "feat: enrich brainstorm.md with architecture guidance and scope assessment"
```

---

## Task 3.5: Enrich `modes/debug.md`

**Files:**
- Modify: `modes/debug.md:186-210`
- Test: `tests/test_modes_adherence.py`

**Step 1: Write the failing test**

Append to `tests/test_modes_adherence.py` (inside `TestModeContentEnrichment`):

```python
    def test_debug_has_architecture_escalation(self) -> None:
        """debug.md must contain 3+ fixes escalation."""
        content = _read_mode("debug.md")
        assert "3" in content and "architecture" in content.lower(), (
            "debug.md must contain '3+ fixes → question architecture' escalation"
        )

    def test_debug_has_human_partner_signals(self) -> None:
        """debug.md must contain human partner signals section."""
        content = _read_mode("debug.md")
        assert "Human Partner Signals" in content, (
            "debug.md must contain 'Human Partner Signals' section"
        )

    def test_debug_fixed_at_mention(self) -> None:
        """debug.md @-mention should reference the debugging-techniques file correctly."""
        content = _read_mode("debug.md")
        assert "@superpowers:context/debugging-techniques.md" in content, (
            "debug.md must @-mention debugging-techniques.md"
        )

    def test_debug_has_shared_anti_rationalization_mention(self) -> None:
        """debug.md must @-mention the shared anti-rationalization file."""
        content = _read_mode("debug.md")
        assert "@superpowers:context/shared-anti-rationalization.md" in content, (
            "debug.md must @-mention shared-anti-rationalization.md"
        )
```

**Step 2: Run test to verify it fails**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-superpowers
python -m pytest tests/test_modes_adherence.py::TestModeContentEnrichment::test_debug_has_shared_anti_rationalization_mention -v
```
Expected: FAIL — debug.md doesn't have the shared anti-rationalization @-mention yet. (The other tests may already pass since debug.md already has some of this content.)

**Step 3: Write minimal implementation**

In `modes/debug.md`, add a cross-phase reminders section. The "Human Partner Signals" and "3+ fixes" content already exists (lines 186-189 and 247-258). Add the shared @-mention. Insert BEFORE the `## Quick Reference` section (before line 259):

```markdown
## Cross-Phase Reminders

@superpowers:context/shared-anti-rationalization.md
```

The existing `@superpowers:context/debugging-techniques.md` at line 210 is already correct — it will now actually resolve with the Work Stream 2 fix.

**Step 4: Run test to verify it passes**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-superpowers
python -m pytest tests/test_modes_adherence.py::TestModeContentEnrichment -v
```
Expected: All enrichment tests pass.

**Step 5: Commit**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-superpowers
git add modes/debug.md tests/test_modes_adherence.py
git commit -m "feat: enrich debug.md with shared anti-rationalization @-mention"
```

---

## Task 3.6: Enrich `modes/execute-plan.md`

**Files:**
- Modify: `modes/execute-plan.md`
- Test: `tests/test_modes_adherence.py`

**Step 1: Write the failing test**

Append to `tests/test_modes_adherence.py` (inside `TestModeContentEnrichment`):

```python
    def test_execute_plan_has_status_protocol(self) -> None:
        """execute-plan.md must contain implementer status protocol."""
        content = _read_mode("execute-plan.md")
        assert "DONE" in content and "BLOCKED" in content, (
            "execute-plan.md must contain status protocol (DONE, BLOCKED)"
        )

    def test_execute_plan_has_model_selection(self) -> None:
        """execute-plan.md must contain model selection guidance."""
        content = _read_mode("execute-plan.md")
        assert "model" in content.lower(), (
            "execute-plan.md must contain model selection guidance"
        )
```

**Step 2: Run test to verify it fails**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-superpowers
python -m pytest tests/test_modes_adherence.py::TestModeContentEnrichment::test_execute_plan_has_status_protocol -v
```
Expected: FAIL — execute-plan.md doesn't have the status protocol yet.

**Step 3: Write minimal implementation**

In `modes/execute-plan.md`, add the following content. Insert BEFORE the `## For Multi-Task Plans: USE THE RECIPE` section (before line 117):

```markdown
## Implementer Status Protocol

When the implementer reports back, expect one of these statuses:

| Status | Meaning | Your Action |
|--------|---------|-------------|
| `DONE` | Task complete, tests pass, committed | Proceed to spec-review |
| `DONE_WITH_CONCERNS` | Complete but flagging potential issues | Read concerns, decide if they need addressing before review |
| `NEEDS_CONTEXT` | Missing information to proceed | Answer the question clearly and completely, then re-dispatch |
| `BLOCKED` | Cannot proceed due to external dependency | Assess the blocker — may need to reorder tasks or resolve dependency first |

Never rush past `NEEDS_CONTEXT` or `BLOCKED`. Unclear answers create bad implementations.

## Model Selection Guidance

Match model capability to task complexity:

| Task Type | Model Role | Why |
|-----------|-----------|-----|
| Mechanical (rename, move, format) | `fast` | No reasoning needed, save cost |
| Standard implementation (single file, clear spec) | `coding` | Good balance of speed and quality |
| Multi-file changes, complex logic | `coding` | Needs to hold multiple files in context |
| Architecture decisions, review | `reasoning` | Needs deep analysis |

Use the `model_role` parameter when delegating to match the agent to the task.

## Cross-Phase Reminders

@superpowers:context/shared-anti-rationalization.md
```

**Step 4: Run test to verify it passes**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-superpowers
python -m pytest tests/test_modes_adherence.py::TestModeContentEnrichment -v
```
Expected: All enrichment tests pass.

**Step 5: Commit**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-superpowers
git add modes/execute-plan.md tests/test_modes_adherence.py
git commit -m "feat: enrich execute-plan.md with status protocol and model selection"
```

---

## Task 3.7: Enrich `modes/verify.md`

**Files:**
- Modify: `modes/verify.md`
- Test: `tests/test_modes_adherence.py`

**Step 1: Write the failing test**

Append to `tests/test_modes_adherence.py` (inside `TestModeContentEnrichment`):

```python
    def test_verify_has_regression_pattern(self) -> None:
        """verify.md must contain regression test verification pattern."""
        content = _read_mode("verify.md")
        assert "regression" in content.lower() and "revert" in content.lower(), (
            "verify.md must contain regression test pattern (write test, revert fix, verify fail)"
        )
```

**Step 2: Run test to verify it fails**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-superpowers
python -m pytest tests/test_modes_adherence.py::TestModeContentEnrichment::test_verify_has_regression_pattern -v
```
Expected: FAIL — verify.md doesn't have the regression test verification pattern yet.

**Step 3: Write minimal implementation**

In `modes/verify.md`, add the following content. Insert BEFORE the `## Delegation During Verification` section (before line 102):

```markdown
### Regression Test Verification (Red-Green Regression Cycle)

When verifying a bug fix, the regression test itself must be verified:

1. **Write the regression test** — should reproduce the original bug
2. **Run it with the fix** — PASS (confirms the fix works)
3. **Revert the fix temporarily** — `git stash` or comment out the fix
4. **Run the test again** — FAIL (confirms the test actually catches the bug)
5. **Restore the fix** — `git stash pop` or uncomment
6. **Run the test again** — PASS (confirms everything is clean)

If step 4 doesn't fail, your test doesn't actually test for the bug. It's a false positive.

```

**Step 4: Run test to verify it passes**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-superpowers
python -m pytest tests/test_modes_adherence.py::TestModeContentEnrichment::test_verify_has_regression_pattern -v
```
Expected: PASS

**Step 5: Commit**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-superpowers
git add modes/verify.md tests/test_modes_adherence.py
git commit -m "feat: enrich verify.md with regression test verification pattern"
```

---

## Task 3.8: Enrich `modes/write-plan.md`

**Files:**
- Modify: `modes/write-plan.md`
- Test: `tests/test_modes_adherence.py`

**Step 1: Write the failing test**

Append to `tests/test_modes_adherence.py` (inside `TestModeContentEnrichment`):

```python
    def test_write_plan_has_file_structure_planning(self) -> None:
        """write-plan.md must contain file structure planning guidance."""
        content = _read_mode("write-plan.md")
        assert "file" in content.lower() and "structure" in content.lower(), (
            "write-plan.md must contain file structure planning step"
        )
```

**Step 2: Run test to verify it fails**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-superpowers
python -m pytest tests/test_modes_adherence.py::TestModeContentEnrichment::test_write_plan_has_file_structure_planning -v
```
Expected: Likely PASS (the word "file" already appears in write-plan.md in the context of "file paths"). If it passes, this test is already satisfied by existing content. If it fails, add the content below.

**Step 3: Write minimal implementation (if needed)**

In `modes/write-plan.md`, add the following content. Insert BEFORE `### What the Plan Must Contain` (before line 96):

```markdown
### Step 2.5: Plan File Structure

Before defining tasks, explicitly decide file decomposition:
- Which files will be created?
- Which existing files will be modified?
- What's the directory structure?
- Where do tests go?

This prevents the implementer from making file organization decisions they'll get wrong. Write it into the plan — every file path, every directory.
```

**Step 4: Run test to verify it passes**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-superpowers
python -m pytest tests/test_modes_adherence.py::TestModeContentEnrichment -v
```
Expected: All enrichment tests pass.

**Step 5: Commit**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-superpowers
git add modes/write-plan.md tests/test_modes_adherence.py
git commit -m "feat: enrich write-plan.md with file structure planning step"
```

---

## Task 3.9: Update agent files

**Files:**
- Modify: `agents/implementer.md`
- Modify: `agents/code-quality-reviewer.md`
- Modify: `agents/spec-reviewer.md`
- Test: `tests/test_modes_adherence.py`

**Step 1: Write the failing test**

Append to `tests/test_modes_adherence.py`:

```python
class TestAgentContentEnrichment:
    """Agents must contain obra's latest methodology content."""

    def test_implementer_has_status_protocol(self) -> None:
        """implementer.md must contain status protocol."""
        content = _read_agent("implementer.md")
        assert "DONE" in content and "BLOCKED" in content, (
            "implementer.md must contain status protocol (DONE, BLOCKED)"
        )

    def test_implementer_has_architecture_guidance(self) -> None:
        """implementer.md must contain architecture guidance."""
        content = _read_agent("implementer.md")
        assert "isolation" in content.lower() or "small files" in content.lower() or "minimal interfaces" in content.lower(), (
            "implementer.md must contain architecture guidance"
        )

    def test_code_quality_reviewer_has_architecture_checks(self) -> None:
        """code-quality-reviewer.md must contain architecture-level checks."""
        content = _read_agent("code-quality-reviewer.md")
        assert "YAGNI" in content, (
            "code-quality-reviewer.md must check for YAGNI violations"
        )

    def test_spec_reviewer_distrust_framing(self) -> None:
        """spec-reviewer.md must contain institutional distrust framing."""
        content = _read_agent("spec-reviewer.md")
        assert "suspiciously" in content.lower() or "incomplete" in content.lower(), (
            "spec-reviewer.md must contain distrust framing about implementer reports"
        )
```

**Step 2: Run test to verify it fails**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-superpowers
python -m pytest tests/test_modes_adherence.py::TestAgentContentEnrichment -v
```
Expected: FAIL — at least `test_implementer_has_status_protocol` will fail (no BLOCKED in current implementer.md).

**Step 3: Write minimal implementation**

**`agents/implementer.md`** — add status protocol and architecture guidance. Insert BEFORE `## Output Format` (before line 118):

```markdown
## Status Protocol

When complete, report your status using one of these codes:

| Status | When to Use | What to Include |
|--------|-------------|-----------------|
| `DONE` | Task complete, tests pass, committed | Standard completion report |
| `DONE_WITH_CONCERNS` | Complete but flagging issues | Completion report + specific concerns |
| `NEEDS_CONTEXT` | Missing info to proceed | Exactly what information you need |
| `BLOCKED` | Cannot proceed | What's blocking and suggested resolution |

Never guess when `NEEDS_CONTEXT` applies. Ask.

## Architecture Principles

When implementing, follow these design principles:
- **Design for isolation** — Each component should be independently testable
- **Prefer small files** — One clear responsibility per file
- **Minimize interfaces** — Fewer public methods, fewer parameters
- **Composition over inheritance** — Small composable pieces
```

**`agents/code-quality-reviewer.md`** — add architecture-level checks. Insert BEFORE `## What You DON'T Check` (before line 135):

```markdown
### 7. Architecture Compliance
- YAGNI — Did the implementer add features not in the spec?
- File decomposition — Are files appropriately sized and focused?
- Size growth — Did an existing file grow beyond reasonable bounds?
- Coupling — Are components appropriately decoupled?
- Over-engineering — Is there unnecessary abstraction?
```

**`agents/spec-reviewer.md`** — strengthen distrust framing. Replace the existing block at lines 45-60 with:

```markdown
## CRITICAL: Do Not Trust the Report

The implementer finished suspiciously quickly. Their report may be incomplete, inaccurate, or optimistic. You MUST verify everything independently.

**DO NOT:**
- Take their word for what they implemented
- Trust their claims about completeness
- Accept their interpretation of requirements
- Assume "tests pass" means requirements are met

**DO:**
- Read the actual code they wrote
- Compare actual implementation to requirements line by line
- Check for missing pieces they claimed to implement
- Look for extra features they didn't mention
- Verify test assertions actually test the requirement, not just exercise code paths

**Verify by reading code, not by trusting report.**
```

**Step 4: Run test to verify it passes**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-superpowers
python -m pytest tests/test_modes_adherence.py::TestAgentContentEnrichment -v
```
Expected: PASS (4 tests)

**Step 5: Run full test suite**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-superpowers
python -m pytest tests/ -v
```
Expected: All tests pass.

**Step 6: Commit**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-superpowers
git add agents/implementer.md agents/code-quality-reviewer.md agents/spec-reviewer.md tests/test_modes_adherence.py
git commit -m "feat: enrich agent files with status protocol, architecture guidance, YAGNI checks"
```

---

## Task 3.10: Update context files

**Files:**
- Modify: `context/philosophy.md`
- Modify: `context/instructions.md`

**Step 1: Write the failing test**

Append to `tests/test_skill_strategy.py`:

```python
class TestContextFileUpdates:
    """Context files must reflect the updated skill strategy."""

    def test_philosophy_has_spirit_vs_letter(self):
        """philosophy.md must contain spirit vs letter content."""
        content = (REPO_ROOT / "context" / "philosophy.md").read_text()
        assert "spirit" in content.lower() and "letter" in content.lower(), (
            "philosophy.md must contain spirit vs letter inoculation"
        )

    def test_instructions_no_removed_skill_references(self):
        """instructions.md must not reference removed skills."""
        content = (REPO_ROOT / "context" / "instructions.md").read_text()
        removed_skills = [
            "code-review-reception",
            "parallel-agent-dispatch",
        ]
        for skill in removed_skills:
            assert f'skill_name="{skill}"' not in content, (
                f"instructions.md still references removed skill: {skill}"
            )
```

**Step 2: Run test to verify it fails**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-superpowers
python -m pytest tests/test_skill_strategy.py::TestContextFileUpdates -v
```
Expected: `test_instructions_no_removed_skill_references` will FAIL because `instructions.md` still references `code-review-reception` and `parallel-agent-dispatch` at lines 119-127.

**Step 3: Write minimal implementation**

**`context/philosophy.md`** — already contains "spirit" references (line 107: "the ritual IS the spirit"). Check test — it should already pass.

**`context/instructions.md`** — remove references to deleted skills. Replace lines 109-127 (the `## Reference` section at the end):

```markdown
---

## Reference

For complete reference tables (modes, agents, recipes, anti-patterns, key rules), use:

```
load_skill(skill_name="superpowers-reference")
```

All other methodology skills (debugging, verification, code review, etc.) are provided by obra/superpowers and discovered automatically via the skill tool.
```

**Step 4: Run test to verify it passes**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-superpowers
python -m pytest tests/test_skill_strategy.py::TestContextFileUpdates -v
```
Expected: PASS (2 tests)

**Step 5: Commit**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-superpowers
git add context/instructions.md tests/test_skill_strategy.py
git commit -m "feat: update context/instructions.md to reflect simplified skill strategy"
```

---

## Task 3.11: Restructure full-development-cycle recipe

**Files:**
- Modify: `recipes/superpowers-full-development-cycle.yaml:268-296`
- Test: `tests/test_recipe_pipeline.py`

**Step 1: Write the failing test**

Update the existing test in `tests/test_recipe_pipeline.py`. Find `TestFullCycleRecipePerTaskReview` class and update `test_execute_plan_describes_per_task_pipeline` (around line 261):

Replace the existing test method:

```python
    def test_execute_plan_uses_sdd_recipe(self):
        """The implementation stage must use a type: recipe step calling SDD."""
        recipe = load_recipe(FULL_CYCLE_RECIPE)
        for stage in recipe["stages"]:
            if stage["name"] == "implementation":
                for step in stage["steps"]:
                    if step.get("type") == "recipe":
                        step_text = str(step)
                        assert "subagent-driven-development" in step_text, (
                            "recipe step must reference subagent-driven-development"
                        )
                        return
                # Check if any step references the SDD recipe
                stage_text = str(stage)
                assert "subagent-driven-development" in stage_text, (
                    "implementation stage must reference subagent-driven-development recipe"
                )
                return
        raise AssertionError("implementation stage not found")
```

**Step 2: Run test to verify it fails**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-superpowers
python -m pytest tests/test_recipe_pipeline.py::TestFullCycleRecipePerTaskReview -v
```
Expected: FAIL — the implementation stage currently uses a single implementer agent step, not a `type: recipe` step.

**Step 3: Write minimal implementation**

In `recipes/superpowers-full-development-cycle.yaml`, replace the `execute-plan` step (lines 268-296) with a `type: recipe` step calling the SDD recipe:

Find lines 268-296 (the `execute-plan` step and its surrounding context):

```yaml
      # Execute the plan using the three-agent pipeline per task
      - id: "execute-plan"
        agent: "superpowers:implementer"
        prompt: |
          Execute the implementation plan using strict TDD...
          ...
        output: "implementation_result"
        on_error: "continue"
```

Replace with:

```yaml
      # Execute the plan using subagent-driven-development recipe
      # This composes the SDD recipe directly — its internal approval gate
      # at final-review surfaces through the parent automatically
      - id: "execute-plan"
        type: "recipe"
        recipe: "subagent-driven-development.yaml"
        context:
          plan_path: "{{paths.plan_path}}"
        output: "implementation_result"
        on_error: "continue"
```

**Step 4: Run test to verify it passes**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-superpowers
python -m pytest tests/test_recipe_pipeline.py::TestFullCycleRecipePerTaskReview -v
```
Expected: PASS

**Step 5: Run full test suite**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-superpowers
python -m pytest tests/ -v
```
Expected: All tests pass.

**Step 6: Commit**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-superpowers
git add recipes/superpowers-full-development-cycle.yaml tests/test_recipe_pipeline.py
git commit -m "feat: restructure full-cycle recipe to compose SDD via type: recipe step"
```

---

## Task 3.12: Update superpowers-reference skill

**Files:**
- Modify: `skills/superpowers-reference/SKILL.md`
- Test: `tests/test_skill_strategy.py`

**Step 1: Write the failing test**

Append to `tests/test_skill_strategy.py`:

```python
class TestSuperpowersReferenceSkill:
    """superpowers-reference skill must reflect current state."""

    SKILL_FILE = REPO_ROOT / "skills" / "superpowers-reference" / "SKILL.md"

    def test_skill_exists(self):
        """superpowers-reference SKILL.md must exist."""
        assert self.SKILL_FILE.exists()

    def test_no_removed_skill_references(self):
        """Skill file must not reference removed skills as Amplifier-provided."""
        content = self.SKILL_FILE.read_text()
        # These should not be referenced as our skills anymore
        removed = ["systematic-debugging", "verification-before-completion",
                    "finishing-a-development-branch", "code-review-reception",
                    "dispatching-parallel-agents"]
        for skill in removed:
            # Allow mention in context of "obra provides" but not as our own
            lines_with_skill = [l for l in content.split("\n") if skill in l]
            for line in lines_with_skill:
                assert "obra" in line.lower() or "removed" in line.lower() or skill not in line, (
                    f"superpowers-reference mentions removed skill '{skill}' without context"
                )
```

**Step 2: Run test to verify it fails**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-superpowers
python -m pytest tests/test_skill_strategy.py::TestSuperpowersReferenceSkill -v
```
Expected: Might fail or pass depending on exact wording. Check and adjust.

**Step 3: Write minimal implementation**

Review `skills/superpowers-reference/SKILL.md` and update the content to reflect that we now have 2 Amplifier-specific skills (integration-testing-discipline and superpowers-reference), with all other methodology skills provided by obra/superpowers. The existing reference tables for modes, agents, and recipes stay the same — only skill references need updating.

At the end of the file, if there are references to the removed skills as load_skill examples, remove them. The file's core reference tables (modes, agents, recipes) are still accurate and should be preserved.

**Step 4: Run test to verify it passes**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-superpowers
python -m pytest tests/test_skill_strategy.py -v
```
Expected: All tests pass.

**Step 5: Commit**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-superpowers
git add skills/superpowers-reference/SKILL.md tests/test_skill_strategy.py
git commit -m "feat: update superpowers-reference skill to reflect 2-skill strategy"
```

---

## Task 3.13: Update existing tests for reduced skill count and new content

**Files:**
- Modify: `tests/test_b4_context_files.py`
- Test: self-validating

**Step 1: Check which existing tests need updates**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-superpowers
python -m pytest tests/ -v 2>&1 | grep -E "FAIL|ERROR"
```

Review failures and update tests that reference removed skills or changed content.

**Step 2: Update `test_b4_context_files.py`**

The existing `test_b4_context_files.py` tests may reference removed skills (like `code-review-reception` and `parallel-agent-dispatch`). Remove or update tests that validate removed skill content. The tests for `using-superpowers-amplifier.md` and `superpowers-methodology.yaml` should still pass since those files still exist.

Specifically, find and remove/update:
- Any tests in classes like `TestCodeReviewReceptionSkill` or `TestParallelAgentDispatchSkill` that reference removed skills
- Update the behavior YAML test if it checks skill count

**Step 3: Run full test suite**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-superpowers
python -m pytest tests/ -v
```
Expected: ALL tests pass across all test files.

**Step 4: Commit**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-superpowers
git add tests/
git commit -m "test: update existing tests for reduced skill count and new content"
```

---

## Task 3.14: Final verification across all repos

**No files changed — verification only.**

**Step 1: Run all tests in amplifier-bundle-recipes**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-recipes/modules/tool-recipes
python -m pytest tests/ -v
```
Expected: ALL pass.

**Step 2: Run all tests in amplifier-bundle-modes**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-modes/modules/hooks-mode
python -m pytest tests/ -v
```
Expected: ALL pass.

**Step 3: Run all tests in amplifier-bundle-superpowers**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-superpowers
python -m pytest tests/ -v
```
Expected: ALL pass.

**Step 4: Verify no Claude Code contamination**

```bash
cd /home/bkrabach/dev/superpowers-3/amplifier-bundle-superpowers
grep -r "TodoWrite\|CLAUDE\.md\|Skill tool" modes/ agents/ context/ skills/ recipes/ || echo "Clean - no contamination"
```
Expected: "Clean - no contamination"
