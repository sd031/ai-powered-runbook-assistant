# Deployment Rollback Runbook

## Overview
Steps to safely roll back a failed deployment in Kubernetes.

## When to Roll Back
- Error rate increases more than 5% after deployment
- P99 latency doubles compared to pre-deployment baseline
- Critical functionality is broken as confirmed by QA or monitoring
- Kubernetes deployment health check fails and pods do not become Ready

## Rollback Steps

### Step 1: Identify the bad deployment
```bash
kubectl rollout history deployment/<app-name> -n production
```

### Step 2: Immediate rollback to previous version
```bash
kubectl rollout undo deployment/<app-name> -n production
kubectl rollout status deployment/<app-name> -n production
```

### Step 3: Roll back to a specific revision
```bash
kubectl rollout undo deployment/<app-name> --to-revision=<N> -n production
```

### Step 4: Verify application health after rollback
```bash
kubectl get pods -n production -l app=<app-name>
curl -f https://<app-endpoint>/healthz
```

## Database Migration Rollback
If the deployment included a DB schema migration:
1. **Do NOT auto-rollback migrations** — manual review required
2. Contact the database team immediately: @db-oncall in Slack
3. Run down-migration: `python manage.py migrate <app> <previous_migration_name>`
4. Verify data integrity before bringing the application back online

## Feature Flag Rollback (LaunchDarkly)
1. Log in to the LaunchDarkly dashboard
2. Locate the feature flag for the broken feature
3. Turn the flag off for all users or target environments
4. Confirm error rate drops within 2 minutes

## Helm Chart Rollback
```bash
helm history <release-name> -n production
helm rollback <release-name> <revision-number> -n production
```

## Post-Rollback Checklist
- [ ] Notify stakeholders in #incidents channel
- [ ] Create Jira ticket for the failed deployment
- [ ] Block the bad commit from being promoted to production in CI/CD
- [ ] Schedule a blameless post-mortem within 48 hours
- [ ] Update deployment checklist if a gap was found
