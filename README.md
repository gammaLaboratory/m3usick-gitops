# m3usick GitOps

GitOps manifests for the m3usick Kubernetes deployment on the home cluster.

## Layout

- `app/base/` — shared Kubernetes resources for the web app.
- `app/overlays/dev/` — `m3usick-dev`, `dev.m3usick.com`, app branch `develop`.
- `app/overlays/prod/` — `m3usick-prod`, `m3usick.com`, app branch `main`.
- `infra/argocd/` — Argo CD `Application` resources for dev and prod.

The home cluster root app discovers a single app-of-apps manifest in `miruohotspring/k8s-home`, which points at `infra/argocd/` in this repository.

## Verify locally

```bash
kubectl apply -k app/overlays/dev --dry-run=server -o name
kubectl apply -k app/overlays/prod --dry-run=server -o name
kubectl apply -f infra/argocd --dry-run=server -o name
```
