# Listing fields

## Contents

- Limits
- Voice
- Keywords
- File shape

## Limits

Apple counts characters, not bytes. One CJK glyph = 1.

| Field | Limit | Notes |
| --- | --- | --- |
| Name | 30 | Per locale. Do not stuff keywords. |
| Subtitle | 30 | Complements the name; do not repeat it. |
| Promotional text | 170 | Editable without a new binary. |
| Description | 4000 | First two lines show in search. |
| Keywords | 100 | Comma-separated, **no space after commas**. No words already in the name. |
| What's New | 4000 | First release: short "初版 / First release" list. |

Always run `scripts/validate-listing.py` before calling the pack done.

## Voice

- State what the downloader can do in the first two lines.
- If the binary is locked to one site, name that site and write as its reader.
- If it is a generic client, say which backend it needs.
- Prefer the product's own nouns (文章 / 手记 / 思考) over generic "content".
- No competitor brands (Android, Google Play, Medium).

## Keywords

- Locale-aware, not literal translations of the Chinese list.
- Include the author or product search terms people actually type.
- Leave unused budget empty rather than stuffing near-duplicates.

## File shape

Write `tmp-asc/listing.md` with one section per locale (`zh-Hans`, `ja`, `en-US`). Each section contains fenced blocks labeled exactly:

`名称` / `副标题` / `宣传文本` / `关键词` / `描述` / `此版本新增内容`

English locale may use `Name` / `Subtitle` / `Promotional Text` / `Keywords` / `Description` / `What's New`.

Also list:

- Support URL
- Privacy policy URL
- Marketing URL
- Copyright
- Primary category
- Screenshot captions (must match the slide headlines)
