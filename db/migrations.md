# Migration notes

- PostgreSQL URL env: `DATABASE_URL` or `POSTGRES_URL` or `POSTGRESQL_URL`
- Tables (SQLAlchemy models):
  - simulations: id (pk), ticker, status, summary (json string), created_at
  - agent_logs: id (pk), simulation_id fk, role, content, created_at
- Pending expansion (if needed):
  - store snapshot/news meta in simulations.summary (already serialized)
  - if normalization needed, add tables: snapshots (fk simulation_id), news_items (fk simulation_id)

Initialize:
```sql
-- run via db/session.py init_db or alembic in future
```
