from typing import Literal


AppMode = Literal["prod", "test"]
PROD_WORKSPACE_SUFFIX = "::prod"
TEST_WORKSPACE_SUFFIX = "::test"


def normalize_mode(value: str | None) -> AppMode:
    return "test" if value == "test" else "prod"


def data_workspace_id(workspace_id: str, mode: AppMode) -> str:
    suffix = TEST_WORKSPACE_SUFFIX if mode == "test" else PROD_WORKSPACE_SUFFIX
    return f"{account_workspace_id(workspace_id)}{suffix}"


def account_workspace_id(workspace_id: str) -> str:
    return workspace_id.removesuffix(TEST_WORKSPACE_SUFFIX).removesuffix(PROD_WORKSPACE_SUFFIX)
