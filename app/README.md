# m3usick App Kubernetes deployment

This deploys the application repository `gammaLaboratory/m3usick` into the home Kubernetes cluster without committing secrets.

## Environments

- `overlays/dev`: `develop` branch → `https://dev.m3usick.com` → namespace `m3usick-dev`
- `overlays/prod`: `main` branch → `https://m3usick.com` → namespace `m3usick-prod`

The pod builds the selected Git branch at startup from the public GitHub repository with pinned `pnpm@8.15.9` and Go `1.23.10`. The init container builds the Vite SPA and the Go server binary, then the web container runs the Go server on port `8080` and serves the SPA from `web/dist`.

This avoids needing a container registry for the first migration from Vercel. Later, this should be replaced by CI-built immutable images.

## Runtime environment

The manifests pass Go server runtime env explicitly instead of importing the whole Vercel env file. This keeps NextAuth-only variables such as `NEXTAUTH_TABLE` and `NEXTAUTH_URL` out of the pod environment.

Required values configured in manifests:

- `APP_ENV`
- `AWS_REGION`
- `M3USICK_AUTH_TABLE`
- `SESSION_COOKIE_NAME`
- `CSRF_COOKIE_NAME`
- `ALLOWED_ORIGINS`
- `SESSION_TTL_HOURS`
- `WEB_DIST_DIR`
- `HTTP_ADDR`

Secret-backed values read from the existing `m3usick-env` Secret:

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AUTH_TOKEN_PEPPER` is sourced from the existing `AUTH_SECRET` key during the Vite + Go migration. Rotate to a dedicated `AUTH_TOKEN_PEPPER` key when auth cutover is ready.

The init container clones the private app repository with a separate `m3usick-git` Secret:

- `GITHUB_TOKEN`
- `GITHUB_USERNAME` (optional)

## Secrets

Vercel env values are pulled into ignored local files in the application repo and converted to Kubernetes Secrets directly:

```bash
cd ~/ghq/github.com/gammaLaboratory/m3usick
vercel env pull .env.k8s.production --environment=production --yes
vercel env pull .env.k8s.preview --environment=preview --yes

kubectl create namespace m3usick-prod --dry-run=client -o yaml | kubectl apply -f -
kubectl -n m3usick-prod create secret generic m3usick-env \
  --from-env-file=.env.k8s.production \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl create namespace m3usick-dev --dry-run=client -o yaml | kubectl apply -f -
kubectl -n m3usick-dev create secret generic m3usick-env \
  --from-env-file=.env.k8s.preview \
  --dry-run=client -o yaml | kubectl apply -f -
```

Do not commit `.env.k8s.*` or rendered Secret YAML.

## Apply

```bash
cd ~/ghq/github.com/gammaLaboratory/jarvis-miruo-v2
kubectl apply -k projects/m3usick/app/overlays/dev
kubectl apply -k projects/m3usick/app/overlays/prod
```

Task 19 applies only the dev overlay. Production apply is intentionally deferred.

## Verify

```bash
kubectl -n m3usick-dev rollout status deploy/m3usick-web
kubectl -n m3usick-prod rollout status deploy/m3usick-web
kubectl -n m3usick-dev get pod,svc,ingress
kubectl -n m3usick-prod get pod,svc,ingress
curl -i https://dev.m3usick.com/api/v1/healthz
curl -i https://dev.m3usick.com/login
```

Before switching public DNS away from Vercel, verify the ingress path internally with the correct `Host` header through `ingress-nginx-controller`.
