---
title: "Authentication"
description: "How to authenticate with DataFlow API"
---

# Authentication

Learn how to authenticate your requests to {{ page.metadata.product_name }} {{ page.metadata.product_version }}.

## API Keys

All requests to `{{ page.metadata.api_base_url }}` must include an API key in the `Authorization` header.

### Getting Your API Key

1. Sign in to your {{ page.metadata.product_name }} dashboard
2. Navigate to Settings → API Keys  
3. Generate a new API key for {{ page.metadata.product_version }}

### Making Authenticated Requests

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     {{ page.metadata.api_base_url }}/users
```

## Authentication Methods

{{ page.metadata.product_name }} {{ page.metadata.product_version }} supports:

- **API Keys** (recommended for v2.0)
- **OAuth 2.0** (enterprise only)
- **JWT Tokens** (new in v2.0!)

## Rate Limits

The stable 2.0 release includes these rate limits:

- **Free tier**: 1,000 requests/hour
- **Pro tier**: 10,000 requests/hour
- **Enterprise**: Unlimited

## Security Best Practices

When using DataFlow API 2.0:

1. Never commit API keys to version control
2. Rotate keys regularly
3. Use environment variables for API endpoints

---

<!-- Template footer will automatically display:
     "DataFlow API 2.0 - Released 2025-10-01" 
     from cascaded metadata -->
     
**Note:** This page inherits `product_name`, `product_version`, `api_base_url`, `release_date`, and `status` from the section cascade. Your template can display these values in headers, footers, or version badges!

