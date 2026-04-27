# High CPU Runbook

## Overview
Steps to diagnose and resolve high CPU utilization on application servers or Kubernetes pods.

## Symptoms
- Alert: `HighCPUUsage` (CPU > 85% for 5 minutes)
- Application response times are degraded
- Pods in `CrashLoopBackOff` or `OOMKilled` state in Kubernetes

## Triage Steps

### Step 1: Identify the culprit process
```bash
top -b -n1 | head -20
ps aux --sort=-%cpu | head -10
```

### Step 2: Check Kubernetes pod resource usage
```bash
kubectl top pods -n production --sort-by=cpu
kubectl describe pod <pod-name> -n production
```

### Step 3: Check for runaway database queries
```sql
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE state = 'active'
  AND now() - pg_stat_activity.query_start > interval '30 seconds'
ORDER BY duration DESC;
```

## Mitigation

### Scale horizontally
```bash
kubectl scale deployment <app-name> --replicas=<current+2> -n production
kubectl rollout status deployment/<app-name> -n production
```

### Kill a runaway process
```bash
kill -9 <PID>
```
Or terminate a runaway PostgreSQL query:
```sql
SELECT pg_terminate_backend(<pid>);
```

### Apply CPU limits temporarily
```bash
kubectl set resources deployment <app-name> -n production --limits=cpu=2000m
```

## Common Root Cause Patterns
- **Infinite loop in code:** Check recent deployments and consider rollback
- **N+1 query problem:** Review slow query logs; add query result caching
- **Crypto or compression spike:** Reschedule batch jobs to off-peak hours
- **Memory leak causing GC pressure:** Profile heap usage; restart pods temporarily

## Escalation
- **15 min without resolution:** Page the application team lead
- **30 min without resolution:** Initiate incident war room and invite team leads
