# Paper trading removal

Staging now tests the same real-trading API and execution code as production,
using its own backend, database, and exchange credentials. Paper trading and test
autotrade are retired. Signals with `autotrade=False` remain non-trading signals;
they are never promoted to real orders by this change.

The `/paper-trading` routes and `/autotrade-settings/paper-trading` routes are
removed, along with their terminal pages, Redux state, and environment variables.
The shared pybinbot package no longer exports `TestAutotradeSettingsSchema`, the
`test_autotrade_settings` document value, paper bot client methods or URLs, or
simulated KuCoin orders. Collection selectors in read-only client methods accept
only `bots`; retired collection names raise `ValueError` before any request.

Deploy the accompanying binquant caller updates before upgrading its pybinbot
package or removing the API routes. Publish the updated pybinbot package and
update consumer dependency locks as part of release. Stop older API and streaming
workers before migrating so they cannot query or recreate the retired tables.

Alembic revision `d7e8f9a0b1c2` follows `a7b4e9c261f0`. It drops `fake_order`,
`paper_trading`, and `test_autotrade`, and deletes deals linked exclusively to
paper bots. Deals also used by real bots and unrelated unowned deals are kept.
It tolerates any of those tables already being absent and can be replayed.
Historical revisions remain intact for upgrades from older databases.

The migration permanently deletes paper history. Its downgrade fails explicitly;
recovering that history requires a database backup. The code change does not
apply the migration to a running environment or place trades.
