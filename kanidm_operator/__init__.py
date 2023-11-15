# noqa: F401,W0611
# pylint: disable=unused-import

from .deploy.kanidm import on_create_kanidms, on_update_kanidms  # noqa
from .deploy.account import (
    on_create_account,
    on_update_account,
    on_delete_account,
)  # noqa
from .deploy.group import on_create_group, on_update_group, on_delete_group  # noqa
