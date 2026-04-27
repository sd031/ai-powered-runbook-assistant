# SSL Certificate Expiry Runbook

## Overview
Steps to handle expiring or expired SSL/TLS certificates before they cause an outage.

## Detection
- Alert: `SSLCertExpiringSoon` fires when fewer than 30 days remain
- Browser shows: "Your connection is not private" (NET::ERR_CERT_DATE_INVALID)
- curl error: `SSL certificate problem: certificate has expired`

## Check Certificate Expiry

Check a live endpoint:
```bash
echo | openssl s_client -connect <hostname>:443 2>/dev/null | openssl x509 -noout -dates
```

Check a cert file directly:
```bash
openssl x509 -in /etc/ssl/certs/<cert>.pem -noout -enddate
```

## Renewal Procedures

### Let's Encrypt (Certbot)
```bash
sudo certbot renew --dry-run
sudo certbot renew
sudo systemctl reload nginx
```

### AWS Certificate Manager (ACM)
ACM auto-renews certificates. Check renewal status:
```bash
aws acm describe-certificate \
  --certificate-arn <ARN> \
  --region us-east-1 \
  | jq '.Certificate.RenewalSummary'
```
If stuck in `PENDING_VALIDATION`, re-add the CNAME validation records in Route 53.

### Manual Certificate Renewal
1. Generate a CSR: `openssl req -new -key private.key -out request.csr`
2. Submit CSR to your CA (DigiCert / Sectigo / GlobalSign)
3. Download the renewed certificate and chain file
4. Replace the cert: `cp new_cert.pem /etc/ssl/certs/<cert>.pem`
5. Test the config: `nginx -t` or `apache2ctl configtest`
6. Reload the web server: `sudo systemctl reload nginx`

### Kubernetes / cert-manager
```bash
kubectl get certificate -n production
kubectl describe certificate <cert-name> -n production
kubectl delete secret <tls-secret-name> -n production
```
Deleting the secret forces cert-manager to re-issue the certificate automatically.

## Escalation
- **Expired cert in production:** This is a **P1 incident** — page on-call immediately
- Contact: @platform-team in Slack
- Status page: update https://status.yourcompany.com for user-visible impact

## Prevention
- Ensure Prometheus `ssl_expiry` exporter is configured for all domains
- Set two alerting thresholds: 30 days (warning) and 7 days (critical)
