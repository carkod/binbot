# Bot status

The bot `status` enum has six stored values. `all` is a query filter.

| Status | Meaning |
| --- | --- |
| `inactive` | Saved configuration that is not trading. |
| `pending` | Waiting for a conditional entry price or an exchange entry fill. |
| `active` | Managing a confirmed position and its exit orders. |
| `completed` | A trading position was closed successfully. |
| `error` | An execution or reconciliation failure requires attention. |
| `closed` | A failed conditional-entry candidate archived for analysis. |

Conditional candidates become `closed` when they expire before submission or
cannot afford the minimum contract. Submitted entries become `closed` only after
cancellation/reconciliation confirms no fills and no remaining position. Partial
fills and uncertain exchange outcomes remain available for reconciliation.

Closing preserves the bot, signal link, deal, orders, entry configuration, and
timestamped reason in its logs. It does not represent a completed trade and does
not permit reactivation. There is no separate `archived` enum value.

Bot GET endpoints hide closed candidates by default, including `status=all`.
Use `status=closed` on the list endpoints to retrieve only closed candidates,
or `include_closed=true` to include them in lists, ID/symbol lookups, and algorithm
rankings. An explicit status filter continues to take precedence over
`include_closed`. Active-pair queries always return only active/pending bots.

The `pybinbot` dependency is pinned to the companion Git commit containing
`Status.closed`; clean installs and CI use that commit until a PyPI release includes it.
Apply the closed-status Alembic migration before deploying API/streaming workers.
Its upgrade safely replays when the enum value already exists. Downgrade retains
the value and archived records because PostgreSQL cannot remove one enum value
without rebuilding its type and rewriting dependent data.
