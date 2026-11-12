import pytest
from sqlalchemy import inspect

pytestmark = pytest.mark.integration


async def test_persona_tables_exist(session_factory):
    async with session_factory() as session:
        conn = await session.connection()
        names = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_table_names(schema="agent")
        )
    for table in ("user_persona", "user_trait", "user_signal", "user_leaning"):
        assert table in names
