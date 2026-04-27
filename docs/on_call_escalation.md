# On-Call Escalation Runbook

## Overview
When and how to escalate incidents during on-call shifts to ensure fast resolution.

## Severity Levels

| Severity | Definition | Response Time | Who Gets Paged |
|----------|-----------|---------------|----------------|
| P1 | Complete outage, data loss risk | 5 min | Primary on-call + Engineering lead |
| P2 | Major feature broken, 50%+ users impacted | 15 min | Primary on-call |
| P3 | Minor feature degraded, workaround exists | 1 hour | Next business day |
| P4 | Cosmetic or logging issues | 24 hours | Ticket only |

## Escalation Process

### Step 1: Acknowledge the alert
- Acknowledge in PagerDuty within 5 minutes (P1) or 15 minutes (P2)
- Post in #incidents: `🚨 Investigating [alert name] — [your name] is on it`

### Step 2: Initial triage (0–15 min)
- Check dashboards: Grafana → Service Overview
- Check recent deployments: `kubectl rollout history deployment/<app>`
- Check error logs: Datadog → Logs → Filter `status:error service:<name>`

### Step 3: Escalate if unresolved
Escalation chain:
```
Primary On-Call → Team Lead → VP Engineering → CTO (P1 only)
```

Manually page the team lead via PagerDuty CLI:
```bash
pd incident create \
  --title "<incident description>" \
  --service <service-id> \
  --escalation-policy prod-escalation-policy
```

### Step 4: War Room for P1 incidents (> 15 min unresolved)
- Start a Zoom bridge: https://zoom.us/start/videomeeting
- Invite: Engineering Lead, Product Manager, Customer Success Lead
- Post the bridge link in #incidents immediately

## Communication Templates

### Initial notification
```
🚨 P[1/2] Incident: <title>
Impact: <who/what is affected and how>
Started: <HH:MM UTC>
On-call: <your name>
Status: Investigating
```

### Update (every 15 min for P1, every 30 min for P2)
```
📊 Update [HH:MM]: <current status — what was tried, current theory, next steps>
```

### Resolution notification
```
✅ Resolved [HH:MM]
Root cause: <description>
Fix applied: <description>
Follow-up actions: <Jira tickets created>
```

## Key Contacts and Tools
- On-call rotation: PagerDuty → `production-oncall` schedule
- Slack channels: #incidents, #engineering-leads, #platform-team
- Status page (update for P1/P2): https://status.yourcompany.com
- Runbook repo: https://github.com/yourorg/runbooks

## Post-Incident Requirements
- P1: Incident report due within 24 hours
- P2: Incident report due within 72 hours
- All incidents: Blameless post-mortem within one week
