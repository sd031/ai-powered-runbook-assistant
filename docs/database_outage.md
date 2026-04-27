# Database Outage Runbook

## Overview
This runbook covers steps to diagnose and recover from a PostgreSQL database outage.

## Symptoms
- Application errors: `FATAL: connection refused` or `too many connections`
- Dashboards showing DB query latency > 5000ms
- Alerts firing: `PostgresDown` or `PostgresHighConnections`

## Immediate Triage

### Step 1: Check database health
```bash
pg_isready -h <DB_HOST> -p 5432
systemctl status postgresql
```

### Step 2: Check active connections
```sql
SELECT count(*), state FROM pg_stat_activity GROUP BY state;
```
If connections > 95% of `max_connections`, proceed to connection pool restart.

### Step 3: Restart connection pool (PgBouncer)
```bash
sudo systemctl restart pgbouncer
```

## Recovery Procedures

### Failover to Read Replica
1. Identify the current primary: `SELECT pg_is_in_recovery();` — returns `false` on the primary
2. Promote the replica: `sudo -u postgres pg_ctl promote -D /var/lib/postgresql/data`
3. Update the application connection string in Kubernetes secret `db-credentials`
4. Notify team in the #incidents Slack channel

### Disk Full Recovery
```bash
df -h /var/lib/postgresql
```
Identify large tables:
```sql
SELECT relname, pg_size_pretty(pg_total_relation_size(relid))
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(relid) DESC
LIMIT 10;
```
Options: archive old partitions, delete stale data, or expand EBS volume.

### Max Connections Exhausted
1. Increase `max_connections` temporarily in `postgresql.conf`
2. Restart PostgreSQL: `sudo systemctl restart postgresql`
3. Audit connection pool settings and add a PgBouncer layer if missing

## Escalation
- **L1 (0–15 min):** On-call engineer
- **L2 (15–30 min):** Database team lead — @db-oncall in Slack
- **L3 (30+ min):** Database vendor support + VP Engineering

## Post-Incident
- File incident report within 24 hours
- Add alerting for the root cause
- Update this runbook if new resolution steps were found
