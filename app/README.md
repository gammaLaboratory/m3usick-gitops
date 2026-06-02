# m3usick App Kubernetes deployment

This deploys the application repository `gammaLaboratory/m3usick` into the home Kubernetes cluster without committing secrets.

## Environments

- `overlays/dev`: `develop` branch image → `https://dev.m3usick.com` → namespace `m3usick-dev`
- `overlays/prod`: `main` branch image → `https://m3usick.com` → namespace `m3usick-prod`

The pod runs an immutable image built by Concourse from `gammaLaboratory/m3usick/Dockerfile` and pushed to ECR. Kustomize `images:` entries in each overlay select the ECR repository and tag. Concourse updates those tags after a successful build:

- dev overlay: automatic after `develop` build/push
- prod overlay: manual gate after `main` build/push

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

Image pulls use the per-namespace `ecr-secret` docker-registry Secret. k8s-home's ECR token refresh systemd timer must refresh `ecr-secret` in both `m3usick-dev` and `m3usick-prod`.

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
