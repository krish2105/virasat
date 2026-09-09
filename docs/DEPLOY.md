# Deploying VIRASAT on free tiers

Two hosts. Render runs the API and the Postgres database; Vercel runs the Next.js
frontend. Nothing else is hosted: the pipeline, the vision layer and the LangGraph
agent run on the owner's machine against the same `DATABASE_URL`. That is a design
commitment (`docs/ARCHITECTURE.md` amendment 9), not a limitation of the free plan —
no free tier can host a 14B assessor, and local-first inference is what keeps the
verifier on a model the owner controls.

## Read this first: the 30-day clock

**A free Render Postgres instance is deleted 30 days after it is created.** Render
sends a warning email; when it expires the database and everything in it is gone, and
the API returns 500s until a new one is attached.

Before that date, do one of:

* recreate a fresh free instance and reload it with the steps in §3 (the local
  database on the owner's Mac stays the source of truth, so nothing is lost); or
* move the database to a host without an expiry (Neon and Supabase both have
  permanent free tiers with PostGIS and pgvector) and change one environment
  variable, `DATABASE_URL`, on the Render service. Nothing in the code assumes
  Render — `settings.database_url` accepts any Postgres URL, with or without the
  `+psycopg` driver suffix.

Put the expiry date in a calendar the day you create the database.

Also expect the free web service to sleep after 15 minutes of no traffic. The first
request after that takes roughly 50 seconds while the container starts. Open the site
a minute before demonstrating it.

## 1. Create the Render services

The repository has a blueprint at `render.yaml`, so this is one screen:

1. Render dashboard → **Blueprints** → **New Blueprint Instance**.
2. Connect `github.com/krish2105/virasat`, branch `main`. Render reads `render.yaml`
   and offers to create `virasat-db` (free Postgres 16) and `virasat-api` (free web
   service).
3. `CORS_ORIGINS` is marked `sync: false`, so Render asks you for it. Enter
   `http://localhost:3000` for now; it becomes the Vercel origin in §5.
4. Apply. The first build takes a few minutes — it installs `requirements-api.txt`,
   which is deliberately slim (no torch, no rasterio).

The service will be at `https://virasat-api.onrender.com`, or with a short random
suffix if that name is taken. **Note the real URL — §5 needs it.**

`postgis` and `vector` are created by the first Alembic migration, so there is no
extension step to do by hand.

## 2. Migrate the hosted database

Copy the database's **External Database URL** from the Render dashboard, then, from
the repository on the owner's Mac:

```bash
export RENDER_DB='<external database url from the Render dashboard>'
DATABASE_URL="$RENDER_DB" uv run alembic upgrade head
```

## 3. Load the data

The hosted database is a copy of the local one; the local one remains authoritative
because that is where the pipeline and the agent write.

```bash
pg_dump --data-only --no-owner --no-privileges \
  -t runs -t tiles -t buildings -t clauses -t changes -t findings \
  -t decisions -t officers -t audit_log -t notifications -t site_visits \
  "postgresql://virasat:virasat@localhost:5434/virasat" \
  | psql "$RENDER_DB"
```

`audit_log` has BEFORE UPDATE/DELETE triggers that raise, but INSERT is allowed, so
the restore succeeds and the append-only guarantee is preserved on the copy.

## 4. Create an officer on the hosted database

Password hashes are argon2 and are not copied in a way you should reuse across
environments; make a fresh account:

```bash
DATABASE_URL="$RENDER_DB" uv run seed-admin <username>
```

## 5. The frontend (already deployed)

The Vercel project exists and a production build is live:

* project — `krishnamathur008-1499s-projects/virasat`
* production alias — `https://virasat-krishnamathur008-1499s-projects.vercel.app`

`API_URL` and `NEXT_PUBLIC_API_URL` are both set to `https://virasat-api.onrender.com`,
the URL §1 produces **if Render gives the service that exact name**. If Render appended
a suffix, correct them and redeploy:

```bash
cd web
vercel env rm API_URL production && vercel env add API_URL production
vercel env rm NEXT_PUBLIC_API_URL production && vercel env add NEXT_PUBLIC_API_URL production
vercel --prod
```

Note that `virasat.vercel.app` belongs to an unrelated project — it is not this app.

### Turn off Vercel Deployment Protection

New Vercel projects are protected by SSO, so the deployment currently redirects
visitors to a Vercel login page rather than serving the site. For a demo that anyone
can open, turn it off:

**Vercel dashboard → the `virasat` project → Settings → Deployment Protection →
Vercel Authentication → Disabled → Save.**

There is no CLI command for this setting. Making the frontend public does not expose
data: the officer queue, audit view and dossier endpoints all require a JWT, and the
only public API route is `/map/aggregate`, which returns per-chowkri counts and is
tested to leak no property-level fields.

Finally set `CORS_ORIGINS` on the Render service to
`https://virasat-krishnamathur008-1499s-projects.vercel.app` (no trailing slash) and
let it redeploy. Cookies are `Secure` in production via `COOKIE_SECURE=1`,
so the officer login only works over HTTPS — which both hosts give you.

## 6. Check it

```bash
curl -s https://<render-url>/health
```

Expect `"status":"ok"` and `"mode":"api-only"`. `"ollama":false` is correct here:
`VIRASAT_API_ONLY=1` tells the service it is not supposed to have a model runtime, so
its absence is reported as the intended shape rather than as a fault. If you see
`"status":"degraded"` with `"mode":"local"`, that variable is missing.

Then open the Vercel URL, sign in with the §4 account, and confirm the officer queue
loads. Run Lighthouse against the Vercel URL for the accessibility number quoted in
the README.

## Re-indexing after deployment

`python -m virasat.rag.index` deletes and rewrites the whole `clauses` table.
`findings.clause_id` is a foreign key onto it, so once findings exist the delete will
fail. Re-index before an assessment run, not after one, or clear the findings you are
prepared to lose first.
