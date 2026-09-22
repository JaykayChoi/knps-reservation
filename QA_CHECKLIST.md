# QA Checklist

- [ ] Safe pytest suite passes.
- [ ] Integration suite passes with the live Telegram test excluded.
- [ ] Intercepted Playwright dashboard suite passes.
- [ ] Disposable PostgreSQL forward → verify → rollback → forward test passes.
- [ ] Creating and editing each category sends canonical `options`.
- [ ] Quiet hours default off, persist per monitor, and disable time controls when off.
- [ ] KTX station picker selects names and four-digit codes.
- [ ] General, special, and standing seat checkboxes round-trip.
- [ ] Test Now returns quickly with `queued` or `running`.
- [ ] `/api/ktx/status` is absent.
- [ ] No live Telegram, KNPS, Modu, Korail, Supabase, or Render action occurs during automated tests.
- [ ] Production preflight, backup, migration, verification, deploy, and smoke test are performed only after explicit approval.
