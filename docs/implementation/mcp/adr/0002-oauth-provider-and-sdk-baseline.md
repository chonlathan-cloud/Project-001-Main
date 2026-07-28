# ADR-0002: OAuth resource server and SDK baseline

- Status: Partially accepted; managed authorization server pending spike
- Date: 2026-07-28

## Decision

The Foundation uses the official Python MCP SDK stable line pinned to
`mcp==1.28.0` and the 2025-11-25-compatible Streamable HTTP `/mcp` interface.
The v2 SDK is not used because `2.0.0rc1` is still a prerelease on this date.
Upgrade to stable v2 requires a compatibility ADR, protocol/client test evidence,
and a deliberately updated exact pin.

The MCP is an OAuth resource server, not the Product authorization server. It
validates asymmetric JWT access tokens against configured JWKS with exact issuer,
audience/resource, expiry, allowed algorithm, required environment claim and
scope checks. It exposes RFC 9728 protected-resource metadata through the SDK.

The authorization server must support Authorization Code + PKCE S256, discovery,
resource indicators, short-lived access tokens, refresh/revocation and an OpenAI-
compatible client registration approach. Product HMAC session tokens are not MCP
access tokens.

## Pending spike

Identity Platform alone is not assumed to satisfy the full authorization-server
contract. The managed/provider choice remains open until Demo proof covers
discovery/registration, PKCE, resource binding, user linking, revocation and
cross-environment negative tests.

