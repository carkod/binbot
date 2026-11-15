# Deployment

GitHub Actions builds and deploys separate service images. Backend Dockerfiles
in `api/`, `streaming/`, and `cronjobs/` install dependencies from `uv.lock`
using `uv sync --frozen`. See [deployment and recovery architecture](architecture.md#deployment-and-automatic-recovery)
for the staging deployment path.

## CVD in the streaming worker

The existing streaming service starts CVD collection automatically in the same
Python process. Apply the CVD migration before restarting streaming; no extra
service, image, or Compose profile is required. Allow 30 seconds for graceful
shutdown. See [market CVD operations and protocol](market-cvd.md) for rollout,
retention, ownership, restart and gap semantics.
