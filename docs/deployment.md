# Deployment

GitHub Actions builds and deploys separate service images. Backend Dockerfiles
in `api/`, `streaming/`, and `cronjobs/` install dependencies from `uv.lock`
using `uv sync --frozen`. See [deployment and recovery architecture](architecture.md#deployment-and-automatic-recovery)
for the staging deployment path.

## Central market CVD collector

See [market CVD operations and protocol](market-cvd.md) for staged rollout,
retention, ownership, restart and gap semantics.
