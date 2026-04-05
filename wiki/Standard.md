# Xcloud Standard

This document defines the integration standards for Xcloud partners.

## Partner Integration Requirements

To be considered "Xcloud compliant," implementations must:

1. **Core Features**
   - Implement the `/api/create`, `/api/delete`, `/api/list`, and `/api/health` endpoints
   - Support both free and premium VM tiers
   - Include the queue system for capacity management

2. **Branding**
   - Use "Powered by Xcloud" logo where applicable
   - Maintain consistent naming (Xcloud, not variations)

3. **Code Redemption**
   - Support Xcloud+ code redemption for premium features
   - Validate codes against configured premium codes

4. **Purchase Integration**
   - Implement Xcloud+ purchase flow
   - Support per-user premium subscriptions

## VM Connection Features

- Browser-based VNC access
- Multi-user connectivity support
- Inactivity-based auto-deletion (free tier)
- Session timeout enforcement

## Commission Program

Partners meeting the full Xcloud standard receive **10% commission** on all paid subscriptions.