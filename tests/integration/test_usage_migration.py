"""Usage migration preserves history without inventing attribution."""

from uuid import uuid4

from sqlalchemy import Engine, inspect, text

from scripts.testing_database import migrate


def test_usage_migration_preserves_unknown_history_and_downgrades(
    migration_engine: Engine,
) -> None:
    engine = migration_engine
    run_id, agent_id = str(uuid4()), str(uuid4())
    try:
        migrate(engine, "0017_unique_active_lease")
        assert "runs" in inspect(engine).get_table_names()
        with engine.begin() as connection:
            connection.execute(
                text("""
                INSERT INTO agents (id, name, description, status, memory_policy,
                                    tool_policy, metadata, created_at)
                VALUES (:id, 'legacy', '', 'active', '{}', '{}', '{}', CURRENT_TIMESTAMP)
            """),
                {"id": agent_id},
            )
            connection.execute(
                text("""
                INSERT INTO runs (id, agent_id, status, input, input_tokens_total,
                    output_tokens_total, estimated_cost_total, created_at)
                VALUES (:id, :agent, 'succeeded', '{"principal_id":"not-trusted"}',
                        12, 3, 0.5, CURRENT_TIMESTAMP)
            """),
                {"id": run_id, "agent": agent_id},
            )
        migrate(engine)
        with engine.connect() as connection:
            row = connection.execute(text("SELECT principal_id, estimated_cost_total FROM runs"))
            assert row.one() == (None, 0.5)
            usage = connection.execute(
                text("""
                SELECT run_id, provider, model, input_tokens, output_tokens, estimated_cost
                FROM model_usage
            """)
            ).one()
            assert usage == (run_id, "unknown", "unknown", 12, 3, 0.5)
        migrate(engine, "0017_unique_active_lease", downgrade=True)
        assert "principal_id" not in {col["name"] for col in inspect(engine).get_columns("runs")}
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT estimated_cost_total FROM runs")) == 0.5
        migrate(engine)
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT count(*) FROM model_usage")) == 1
    finally:
        engine.dispose()
