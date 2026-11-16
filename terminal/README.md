[![Test Production](https://github.com/carkod/binbot/actions/workflows/pr.yml/badge.svg)](https://github.com/carkod/binbot/actions/workflows/pr.yml)

## Requirements

- Docker and docker-compose
- Python 3
- Pipenv. If not installed, run `pip install pipenv`

## Running back-end api

1. Run `pipenv shell` to activate the virtual environment
2. Comment out api service and `docker-compose up -d`
3. Run vscode debugger to start the FastAPI application

New packages or installing from scratch:

- `pipenv lock --clear`
- `pipenv install`

## Running front-end web app

1. Run `npm run install:clean`
2. Run `npm start`
3. Attach vscode debugger if needed

## UI components and palette

The terminal uses Mantine for layout, forms, navigation, tables, dialogs, and
typography. The application has a fixed light color scheme, a dark sidebar, and
the original warm gray page background. There is no theme switch.

Use the shared [theme](./src/theme.ts) for semantic colors: `primary`, `info`,
`success`, `warning`, and `danger`. Shade 5 retains the original palette; darker
shades are available for readable text on light surfaces. Prefer Mantine props
and components over custom CSS: `Title` supports six heading levels, `Text`
supports size, weight, and color, and `Highlight`, `Mark`, `Badge`, `Alert`, and
`Blockquote` cover emphasized content. Keep domain-specific chart and trading
styles in [terminal.css](./src/styles/terminal.css).

Form inputs retain native events for React Hook Form and chart field focus.
Keep chart components mounted across tab changes to preserve chart state, and
dispatch a resize event after revealing a chart or changing the sidebar width.

From this directory, validate changes with `npm run lint`, `npm run type-check`,
`npm test`, and `npm run build`.

## UI animations

Motion is installed as `motion`; import components and hooks from `motion/react`.
Vite needs no additional configuration. The application root uses `MotionConfig`
with `chartTransition` from [src/utils/motion.ts](./src/utils/motion.ts) and
`reducedMotion="never"`, so the internal terminal app always uses the full
animations.

The dashboard reveals chart cards after their initial queries load. Use
`chartRevealVariants` from [src/utils/motion.ts](./src/utils/motion.ts) for the same
fade and 12 px upward slide elsewhere:

```tsx
<motion.div initial="hidden" animate="visible" variants={chartRevealVariants}>
  <Chart />
</motion.div>
```

Keep the animated element mounted when data refreshes, so polling updates do not
replay the entrance.

Use [LivePlotlyChart](./src/app/components/LivePlotlyChart.tsx) for updating
microstructure and aggregate CVD charts. It applies the shared reveal and Plotly
transition settings while preserving legend selections across refreshes. Supply
stable point IDs and explicit nulls for gaps; keep data and layout memoized so
unrelated renders do not restart transitions.

Futures bot detail uses centrally stored per-symbol CVD: one-minute points over
a rolling 15-minute window, refreshed every 30 seconds. It shares the collector hosted by
the existing streaming worker with the Dashboard's aggregate card. See [CVD operations](../docs/market-cvd.md)
for deployment, coverage and history limits.

## Deployment

1. Merge changes to master
2. Test on local:

- `cd web && yarn build` This is to avoid docker javascript leap out of memory error
- Build and test docker container `docker build --tag binbot . && docker run -ti -p 8000:80 binbot`
- Publish to docker hub `docker build --tag binbot . && docker tag binbot carloswufei/binbot:latest && docker push carloswufei/binbot`

3. Wait for check to pass. Github action will publish to Docker Hub

If docker-compose doesn't exist: 3. Copy `scp docker-compose.yml <USERNAME>@<SERVER_IP>:/var/www/binbot.carloswu.com` 4. Modify details to match production needs

or `docker build --tag binbot . && docker tag binbot carloswufei/binbot:latest && docker push carloswufei/binbot`

In production: 5. `docker-compose pull && docker-compose up -d` 6. If `.env.prod` is modified, scp to remote server and replace `.env` in production with new `.env.prod`

## Test production

1. Run `docker build --tag binbot .`
2. Run `docker-compose up`

If issues are encountered downloading prod DB to local

1. Dump database from the source Postgres instance.
2. Restore it into your local Postgres instance.

## Detailed documentation

https://carkod.github.io/binbot/
