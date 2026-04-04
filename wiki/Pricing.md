# Pricing

## Free Tier

- Limited to **10 concurrent VMs** at a time (configurable via `MAX_GLOBAL_VMS`)
- Each VM is limited to **60 minutes** of usage (configurable via `MAX_SESSION_MINUTES`)
- VMs auto-delete after **5 minutes** of inactivity (configurable via `MAX_INACTIVITY_MINUTES`)
- If you exceed the 10 VM limit, your request will be queued automatically

## Xcloud+

- **$5/month per user**
- Get a dedicated instance that doesn't get deleted unless you cancel
- Premium VMs have no inactivity timeout
- Premium VMs have no session timeout
- Guaranteed resources
- Uptime guarantee of 85%

### How to Use Premium

1. Set premium codes in `.env`:
   ```
   PREMIUM_CODE=CODE1,CODE2
   ```

2. When creating a VM, pass the premium code:
   ```
   /api/create?developer_id=dev1&premium=CODE1
   ```

3. Premium VMs appear with `"premium": true` in API responses

## Partner Program

UBG owners who add Xcloud and are compliant with the full Xcloud standard receive **10% of the sale** as a commission.

## Self-Hosted

Xcloud can be self-hosted with custom limits:

| Variable | Default | Description |
|----------|---------|-------------|
| MAX_GLOBAL_VMS | 10 | Max concurrent VMs |
| MAX_VMS_PER_DEV | 100 | Max VMs per developer |
| MAX_SESSION_MINUTES | 60 | Max session lifetime |
| MAX_INACTIVITY_MINUTES | 5 | Max inactivity before deletion |

Contact for enterprise pricing and custom deployments.
