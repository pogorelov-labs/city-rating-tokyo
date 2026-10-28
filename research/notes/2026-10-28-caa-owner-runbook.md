# CAA owner runbook (CRTKY-35)

**Status: owner verification/application, not an applied change by this PR.** On
2026-10-28, a recursive lookup and an authoritative response from
`ns2.dns-parking.com` returned `pogorelov.dev. CAA 0 issue "letsencrypt.org"`
(TTL 14400). The other listed nameserver, `ns1.dns-parking.com`, timed out from
this environment. The `city-rating.pogorelov.dev` recursive query returned no
CAA answer of its own. This is a point-in-time observation, not a complete
inventory of descendant records or issuers. A direct TLS handshake to that
host timed out, so its current certificate issuer was not established here.
The repository identifies Coolify/Traefik but does not establish every
configured certificate authority for this domain.

## Owner preflight

1. In the DNS provider's authoritative zone, inventory existing apex and
   descendant CAA records, including delegated zones and wildcard use. Confirm
   the authoritative nameservers from the registrar. Do not remove unrelated
   records or add a duplicate.
2. Inventory all services and their configured ACME/CA issuers, including
   renewals, wildcard certificates and any CDN or externally managed service.
   Check actual presented certificates as an additional observation. A single
   served certificate does not prove all future issuers. If any service needs
   another CA, preserve its authorized `issue`/`issuewild` entries; do not
   restrict the zone until the owner resolves the conflict.
3. Check each relevant hostname for its own CAA records: CAA discovery uses the
   nearest applicable record set, so a descendant's record can override the
   apex policy rather than supplement it. Check delegated zones separately.

## Intended record and application

For ordinary issuance by Let's Encrypt, the ticket's intended record is:

```text
Name/host: @ (pogorelov.dev.)
Type: CAA
Flags: 0
Tag: issue
Value: letsencrypt.org
```

Use the DNS provider's CAA fields (or its equivalent quoted presentation),
not a TXT record. Keep the current record if it already matches; no duplicate
is necessary. Use the provider's existing TTL policy. An `issuewild` record,
if present, controls wildcard issuance separately; if absent, `issue` applies
to wildcards as well. Do not add or remove `issuewild` or other CA entries
without confirming the actual wildcard and issuer requirements. Apply only
through the owner-controlled DNS UI after preflight, and record the before and
after record sets and time.

## Verification

Query both authoritative nameservers and a recursive resolver after propagation:

```sh
dig NS pogorelov.dev +short
dig @ns1.dns-parking.com pogorelov.dev CAA +noall +answer +comments
dig @ns2.dns-parking.com pogorelov.dev CAA +noall +answer +comments
dig pogorelov.dev CAA +noall +answer +comments
dig city-rating.pogorelov.dev CAA +noall +answer +comments
```

Substitute the current authoritative nameservers if they changed. Repeat for
all relevant service hostnames and delegated zones; a missing child CAA answer
alone does not prove the effective policy. Check TLS issuer and expiry with
an SNI-aware client, for example:

```sh
openssl s_client -connect city-rating.pogorelov.dev:443 -servername city-rating.pogorelov.dev </dev/null 2>/dev/null | openssl x509 -noout -issuer -subject -dates
```

A successful TLS handshake only checks the existing certificate, not future
issuance. Verify renewal using the owner's established CA staging/renewal
procedure and inspect its result; do not force production issuance merely to
test this record. If renewal fails or an unexpected issuer is required, restore
the recorded prior CAA set via the DNS provider and allow for TTL propagation.

Reference: [RFC 8659 — DNS Certification Authority Authorization](https://www.rfc-editor.org/rfc/rfc8659.html).
