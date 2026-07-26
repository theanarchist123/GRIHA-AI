/**
 * Centralized WebSocket URL utility for transforming HTTP/HTTPS base URLs
 * into their WebSocket equivalents (ws/wss).
 */

/**
 * Constructs a WebSocket URL from the NEXT_PUBLIC_API_URL environment variable.
 * 
 * @param endpoint - The WebSocket endpoint path (e.g., "/api/ws/scrape-progress/123")
 * @returns A fully qualified WebSocket URL (ws:// or wss://)
 * @throws Error if NEXT_PUBLIC_API_URL is undefined in production mode
 * 
 * @example
 * // With NEXT_PUBLIC_API_URL="https://griha-ai-theta.vercel.app"
 * buildWebSocketUrl("/api/ws/scrape-progress/abc123")
 * // Returns: "wss://griha-ai-theta.vercel.app/api/ws/scrape-progress/abc123"
 * 
 * @example
 * // With NEXT_PUBLIC_API_URL="http://localhost:10000"
 * buildWebSocketUrl("/ws/browser-stream/456")
 * // Returns: "ws://localhost:10000/ws/browser-stream/456"
 */
export function buildWebSocketUrl(endpoint: string): string {
  const isDevelopment = process.env.NODE_ENV === 'development';
  const baseUrl = process.env.NEXT_PUBLIC_API_URL;

  // Handle missing environment variable
  if (!baseUrl) {
    if (isDevelopment) {
      // Development fallback with warning
      console.warn(
        '[buildWebSocketUrl] NEXT_PUBLIC_API_URL is not defined. Falling back to ws://localhost:10000'
      );
      return buildUrlFromBase('ws://localhost:10000', endpoint);
    } else {
      // Production error - no fallback
      throw new Error(
        'NEXT_PUBLIC_API_URL environment variable is not defined. Cannot construct WebSocket URL in production.'
      );
    }
  }

  // Parse the base URL
  let parsedUrl: URL;
  try {
    parsedUrl = new URL(baseUrl);
  } catch (error) {
    throw new Error(
      `Invalid NEXT_PUBLIC_API_URL: "${baseUrl}". Must be a valid HTTP or HTTPS URL.`
    );
  }

  // Transform protocol: http -> ws, https -> wss
  let wsProtocol: string;
  if (parsedUrl.protocol === 'http:') {
    wsProtocol = 'ws:';
  } else if (parsedUrl.protocol === 'https:') {
    wsProtocol = 'wss:';
  } else {
    throw new Error(
      `Unsupported protocol "${parsedUrl.protocol}" in NEXT_PUBLIC_API_URL. Expected "http:" or "https:".`
    );
  }

  // Construct WebSocket base URL preserving host, port, and pathname
  const wsBaseUrl = `${wsProtocol}//${parsedUrl.host}${parsedUrl.pathname}`;

  return buildUrlFromBase(wsBaseUrl, endpoint);
}

/**
 * Helper function to correctly concatenate base URL and endpoint,
 * handling trailing slashes to avoid double slashes.
 * 
 * @param base - The base WebSocket URL (e.g., "ws://localhost:10000" or "wss://example.com/api")
 * @param endpoint - The endpoint path to append (e.g., "/ws/stream" or "ws/stream")
 * @returns The concatenated URL with correct slash handling
 */
function buildUrlFromBase(base: string, endpoint: string): string {
  // Remove trailing slash from base if present
  const normalizedBase = base.endsWith('/') ? base.slice(0, -1) : base;
  
  // Ensure endpoint starts with a slash
  const normalizedEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  
  return `${normalizedBase}${normalizedEndpoint}`;
}
