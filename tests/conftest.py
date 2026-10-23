"""pytest 全局夹具：用户级设置目录按测试隔离。

settings.user_settings_path() 默认指向 ~/.deeptalk/workbench.local.json
（Owner Key 跨工作树持久化）。所有测试必须通过注入临时目录隔离，
绝不读写真实用户主目录，也避免不同 root 的测试互相污染用户级状态。
autouse fixture 对 unittest.TestCase 同样生效（pytest 文档行为）。
"""

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolated_user_settings(tmp_path, monkeypatch):
    from deeptalk_studio.workbench import settings as settings_module

    monkeypatch.setattr(settings_module, "USER_SETTINGS_DIR", Path(tmp_path))
    yield
