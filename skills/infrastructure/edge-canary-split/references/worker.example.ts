type Bucket = 'stable' | 'canary';

const COOKIE_NAME = 'canary_bucket';
const FORCE_PARAM = '_canary';
const COOKIE_MAX_AGE = 60 * 60 * 24 * 7;

const readBucketCookie = (request: Request): Bucket | undefined => {
  const cookie = request.headers.get('cookie');
  const match = cookie?.match(/(?:^|;\s*)canary_bucket=(stable|canary)(?:;|$)/);
  return match?.[1] as Bucket | undefined;
};

const rollBucket = (percent: number): Bucket => {
  const [n] = crypto.getRandomValues(new Uint32Array(1));
  return n! % 100 < percent ? 'canary' : 'stable';
};

const bucketCookie = (bucket: Bucket) =>
  `${COOKIE_NAME}=${bucket}; Path=/; Max-Age=${COOKIE_MAX_AGE}; Secure; SameSite=Lax`;

const withBucketCookie = (response: Response, bucket: Bucket): Response => {
  const res = new Response(response.body, response);
  res.headers.append('set-cookie', bucketCookie(bucket));
  return res;
};

// The zone's Browser Cache TTL rewrites cache-control on zone-cached canary
// responses to a 4h max-age; documents must stay revalidate-always in the
// browser or rollout-percent changes take hours to reach returning visitors.
const withBrowserNoCache = (response: Response, url: URL): Response => {
  const isDocument =
    response.headers.get('content-type')?.includes('text/html') || url.pathname.endsWith('.data');
  if (!isDocument) return response;
  const res = new Response(response.body, response);
  res.headers.set('cache-control', 'public, max-age=0, must-revalidate');
  return res;
};

const originHost = (env: Env, bucket: Bucket) =>
  bucket === 'canary' ? env.CANARY_ORIGIN : env.STABLE_ORIGIN;

// Fetching the origin by its own hostname is the whole point: the Cloudflare
// cache keys on the subrequest URL, so stable and canary get separate cache
// partitions instead of fighting over the public URL.
const fetchOrigin = (request: Request, env: Env, bucket: Bucket, url: URL) => {
  const originUrl = new URL(url);
  originUrl.host = originHost(env, bucket);
  // Under Flexible SSL the Worker sees request.url as http://, and an http
  // subrequest makes Vercel answer 308-to-https for every document — always
  // talk to the origins over https regardless of how the eyeball arrived.
  originUrl.protocol = 'https:';
  // Zone cache rules DO evaluate subrequests (verified 2026-07-08: a rule
  // keyed on the origin full_uri turns MISS→HIT), but every existing rule
  // matches public hostnames, so nothing opts the vercel.app origin hosts
  // in. cacheEverything keeps eligibility self-contained instead of tying
  // it to dashboard rules that must track the origin list; TTLs come from
  // the origins' Cloudflare-CDN-Cache-Control headers.
  const cf: RequestInitCfProperties | undefined =
    request.method === 'GET' || request.method === 'HEAD' ? { cacheEverything: true } : undefined;
  return fetch(new Request(originUrl, request), { cf });
};

export default {
  async fetch(request, env): Promise<Response> {
    const url = new URL(request.url);

    const forced = url.searchParams.get(FORCE_PARAM);
    if (forced === '1' || forced === '0') {
      const bucket: Bucket = forced === '1' ? 'canary' : 'stable';
      url.searchParams.delete(FORCE_PARAM);
      return new Response(null, {
        status: 302,
        headers: {
          'location': url.toString(),
          'set-cookie': bucketCookie(bucket),
          'cache-control': 'no-store',
        },
      });
    }

    const assigned = readBucketCookie(request);
    let bucket = assigned;
    if (!bucket) {
      // KV wins over the env var so the percent can change without a deploy;
      // cacheTtl keeps it at one KV read per edge location per minute.
      const kvPercent = await env.CANARY.get('percent', { cacheTtl: 60 });
      const raw = Number(kvPercent ?? env.CANARY_PERCENT);
      const percent = Number.isFinite(raw) ? Math.min(100, Math.max(0, raw)) : 0;
      bucket = rollBucket(percent);
    }

    let response: Response;
    try {
      response = await fetchOrigin(request, env, bucket, url);
      if (bucket === 'canary') response = withBrowserNoCache(response, url);
      if (
        bucket === 'canary' &&
        response.status >= 500 &&
        ['GET', 'HEAD'].includes(request.method)
      ) {
        console.info(
          JSON.stringify({
            event: 'canary_5xx_fallback',
            status: response.status,
            path: url.pathname,
          }),
        );
        const stable = await fetchOrigin(request, env, 'stable', url);
        return withBucketCookie(stable, 'stable');
      }
    } catch (error) {
      if (bucket === 'canary' && ['GET', 'HEAD'].includes(request.method)) {
        console.info(
          JSON.stringify({
            event: 'canary_fetch_error_fallback',
            path: url.pathname,
            error: String(error),
          }),
        );
        const stable = await fetchOrigin(request, env, 'stable', url);
        return withBucketCookie(stable, 'stable');
      }
      return new Response('Bad Gateway', { status: 502 });
    }

    return assigned ? response : withBucketCookie(response, bucket);
  },
} satisfies ExportedHandler<Env>;
