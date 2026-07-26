# Validation

- Python source compilation: passed
- Compile errors: 0
- Secure browser UI route: `/`
- Backup browser UI route: `/app`
- Browser helper API route prefix: `/web`
- Protected external API route prefix: `/v1`
- Browser no longer asks for `API_KEY`
- Browser JavaScript does not embed `API_KEY`
- Celery removed from free runtime path
- Redis removed from free runtime path
- Render Blueprint resources: web + Postgres only

Security note: `API_KEY` protects external `/v1/*` API usage. The public UI calls
same-origin `/web/*` endpoints instead of sending the key to the browser. For a
public production product, add login, CAPTCHA, or per-user quotas.
- Startup script added: `scripts/start-render.sh`
- Render dockerCommand simplified: `sh ./scripts/start-render.sh`
