# Connect questionnaires

Write every answer into `tmp-asc/questionnaires.md`. Cite the evidence (file, SDK, endpoint). Use `UNKNOWN` when evidence is missing.

## Contents

- Age rating
- Export compliance
- Content rights
- App Privacy
- Review information
- Availability
- Account rules

## Age rating

Apple's current questionnaire is capability-based (4+ / 9+ / 12+ / 13+ / 16+ / 17+ / 18+, plus regional maps). Answer from product behavior, not from the desired badge.

Ask and record at least:

- Unrestricted web access
- User-generated content (comments, reviews, chat)
- Social or social-adjacent features
- Violence, horror, sexual content, medical, gambling, alcohol, tobacco, drugs
- Contests, mature themes

Rules:

- In-app comments = UGC. Do not claim "no UGC".
- Login-optional browse does not cancel UGC if posting exists.
- Do not set `socialMedia=true` unless the app is actually a social network. Comments on an author's site are usually UGC without social-media.

`asc age-rating view/edit` can write the declaration after the answers are agreed.

## Export compliance

Three buckets: exempt transport (HTTPS / system TLS only), standard third-party crypto, proprietary crypto.

- HTTPS-only app → exempt. Prefer `ITSAppUsesNonExemptEncryption=false` in Info.plist and rebuild.
- Do not create an encryption declaration that contradicts the binary.
- France store availability is a separate flag; only set it when true.

## Content rights

- Own site / own writing → `uses-third-party-content=false` unless the app embeds others' copyrighted catalogs as a product.
- Embedded quotes, movie posters, or third-party embeds may still need a yes. Record why.

```bash
asc apps content-rights view --app "$APP_ID"
asc apps content-rights edit --app "$APP_ID" --uses-third-party-content=false
```

## App Privacy

Public ASC API cannot finish this. Plan in a file, then apply through an Apple web session:

```bash
asc web privacy pull --app "$APP_ID" --out ./privacy.json
asc web privacy plan --app "$APP_ID" --file ./privacy.json
asc web privacy apply --app "$APP_ID" --file ./privacy.json
asc web privacy publish --app "$APP_ID" --confirm
```

For each data type, record: collected?, used for tracking?, linked to identity?, purpose.

Scan before answering:

- Analytics (OpenPanel, telemetry)
- Crash reporters
- Auth (email, social ids)
- Push tokens
- Photos / pasteboard / disk
- WebView cookies

Do not mark "not collected" for a type an SDK uploads.

## Review information

Always write:

- Contact name, phone, email
- Notes: what the app is, that browse works signed-out if true, how to sign in if review needs it
- Demo account only when signed-out browse is insufficient

First-submit notes should mention the production site URL and the privacy policy URL.

## Availability

- Free vs paid
- Territories (or all)
- Available in new territories

First record is created once. After that, only edit.

## Account rules

If the app has accounts:

- In-app account deletion
- Sign in with Apple when a third-party login is offered as a primary path (Apple's 4.8). Confirm against current guideline text before asserting an exception.

If there are no accounts, say so and skip.
