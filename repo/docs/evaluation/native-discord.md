# Native Discord evaluation

Runtime result: `PASS_NATIVE` for local normalization, roster authorization,
thread routing and persisted links. Duplicate and edited/deleted event behavior
has demonstrated limits; full gateway/provider/channel acceptance remains
`INCONCLUSIVE`.

## DISCORD-01: local events and fresh-process mapping

`native-discord-v1-seed.json` and `native-discord-v1-restart.json` exercise the
pinned source plus `/tmp/kirocrew-offline-9aj0edac/data/repo` offline. The native
`DiscordClient._on_dispatch` and `DiscordTransport.receive` consume authored
events for a simulated owner, bot, unknown sender, approved thread and unapproved
thread. Only the authorized DM and exact approved thread reach the local turn
observer. An empty roster denies access. A waiting callback in one conversation
does not prevent another conversation from advancing. No network client session
is opened and no real message is sent.

Native `SessionMap` persists the provider session, own-channel link and dashboard
mirror. A fresh process reloads them exactly; a removed roster principal cannot
receive a proactive send. The outbound target is checked using a local client
fixture. This proves stored mapping, not an actual dashboard/provider resume.

The same `MESSAGE_CREATE` ID submitted twice dispatches twice at this layer.
`MESSAGE_UPDATE` and `MESSAGE_DELETE` cause no turn callback. After restart,
a rephrased issue and a structurally different issue both dispatch as messages.
The transport has no semantic issue identity. These observations demonstrate
that this layer cannot enforce the exact one-initial-owner-ping invariant
(`SAFETY_GAP` for relying on transport alone); they do not claim every higher
gateway or outbound path lacks deduplication. Edit/delete propagation at this
client boundary is a `FEATURE_GAP`. No new notification system is introduced.

## Native design and remaining scope

Native Discord normalizes inbound events through `MessagingTransport` and
shares `TurnDriver`, approval handling and output redaction with other channels.
`ChannelLink` and namespaced session keys connect a conversation to durable Crew
state. Discord-specific transport, rendering, attachments, gateway and resume
code live under `src/kiro_crew/discord/`.

The shipped integration supports allow-listed users in DMs, exact approved
server threads, and an optional channel setting that opens a new public thread.
Empty user authorization denies access. This transport/conversation identity
is useful, but does not by itself prove that a paraphrased owner issue is matched
to an existing decision. That distinction requires the handoff's simulated
owner issue/revision scenarios.

Test routing, owner authentication, durable conversation mapping, dashboard
continuity, waiting without blocking unrelated work, edited/deleted replies,
restart and duplicate prevention. One underlying issue must retain one visible
conversation through rewording, expansion and new evidence.

Use an isolated simulated owner. Do not send automated questions to the real
owner.

Sources: [messaging](../system-specs/modules/messaging.md),
[persistent channels](../system-specs/modules/persistent-agent-channels.md).
