# Render Package Checklist

- [x] Free Render web service only
- [x] Free Render PostgreSQL database
- [x] Celery background worker removed
- [x] Redis/Key Value removed
- [x] In-process job runner enabled
- [x] Root homepage UI at `/`
- [x] Backup app route at `/app`
- [x] Browser UI uses `/web/*`
- [x] Browser does not require `API_KEY`
- [x] Browser does not receive `API_KEY`
- [x] Protected external API still available at `/v1/*`
- [x] `/v1/*` still requires `X-API-Key`
- [x] `OPENAI_API_KEY` remains `sync: false` in `render.yaml`
- [x] Python source compilation passed

Before production, add one of:

- user login
- CAPTCHA
- tenant quotas
- paid worker service
- hosted Redis queue
