# WebSocket Production URL Fix - Bugfix Design

## Overview

The frontend application fails to establish WebSocket connections in production deployments because three components use hardcoded localhost URLs (`ws://127.0.0.1:10000`) instead of dynamically constructing WebSocket URLs from the `NEXT_PUBLIC_API_URL` environment variable. This prevents real-time features (scraping progress, agent terminal streaming) from functioning in production on Vercel, while working correctly in local development.

The fix involves implementing a centralized utility function that transforms HTTP/HTTPS base URLs into their WebSocket equivalents (ws/wss), then updating all three affected components to use this utility instead of hardcoded localhost URLs.

## Glossary

- **Bug_Condition (C)**: The condition that triggers the bug - when WebSocket connections are initialized in production using hardcoded localhost URLs instead of environment-based URLs
- **Property (P)**: The desired behavior - WebSocket URLs should be dynamically constructed from `NEXT_PUBLIC_API_URL` with proper protocol transformation (https→wss, http→ws)
- **Preservation**: Existing WebSocket functionality (message handling, reconnection logic, error states) and HTTP API calls that must remain unchanged by the fix
- **NEXT_PUBLIC_API_URL**: Environment variable containing the backend base URL (e.g., `https://griha-ai-theta.vercel.app` in production, `http://localhost:10000` in development)
- **Protocol Transformation**: Converting HTTP protocols to WebSocket protocols (http → ws, https → wss)
- **dashboard/page.tsx**: The main dashboard component that displays property search results with real-time scraping progress
- **AgentProgress.tsx**: A shared component that visualizes live scraping progress with detailed status updates
- **LiveAgentTerminal.tsx**: An autopilot component that streams browser automation frames and execution logs

## Bug Details

### Bug Condition

The bug manifests when the application is deployed to production on Vercel and a user triggers any feature requiring WebSocket connections (scraping, autopilot). The WebSocket initialization code in three components either uses hardcoded localhost URLs or has incorrect fallback logic, resulting in connection failures to `ws://127.0.0.1:10000` instead of the production backend URL.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type WebSocketConnectionAttempt
  OUTPUT: boolean
  
  RETURN (input.environment = "production") 
         AND (input.websocketUrl CONTAINS "127.0.0.1" OR input.websocketUrl CONTAINS "localhost")
         AND (input.websocketUrl NOT DERIVED_FROM NEXT_PUBLIC_API_URL)
         AND (input.expectedUrl CONTAINS "wss://griha-ai-theta.vercel.app")
END FUNCTION
```

### Examples

**Example 1: Dashboard scraping in production**
- **Input**: User clicks "Scrape Live from Property Sites" button on Vercel deployment
- **Current behavior**: `new WebSocket("ws://127.0.0.1:10000/api/ws/scrape-progress/abc123")` attempts connection to localhost
- **Expected behavior**: `new WebSocket("wss://griha-ai-theta.vercel.app/api/ws/scrape-progress/abc123")` connects to production backend

**Example 2: AgentProgress component in production**
- **Input**: AgentProgress component mounts during live search
- **Current behavior**: Hardcoded `ws://127.0.0.1:10000/api/ws/scrape-progress/${clientId}` fails to connect
- **Expected behavior**: Dynamically constructed `wss://griha-ai-theta.vercel.app/api/ws/scrape-progress/${clientId}` successfully connects

**Example 3: LiveAgentTerminal in production with missing env var**
- **Input**: Autopilot terminal opens but `NEXT_PUBLIC_API_URL` is undefined or malformed
- **Current behavior**: Falls back to `ws://127.0.0.1:10000/ws/browser-stream/${hunt.id}` silently
- **Expected behavior**: Should use environment variable without fallback, or provide clear error message if missing

**Example 4: Local development (edge case - should continue working)**
- **Input**: Developer runs `npm run dev` with `NEXT_PUBLIC_API_URL=http://localhost:10000`
- **Current behavior**: Hardcoded `ws://127.0.0.1:10000` connects successfully (by coincidence)
- **Expected behavior**: Dynamically constructed `ws://localhost:10000` connects successfully (by design)

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- WebSocket message handling logic must continue to process and display scraping progress updates, terminal logs, and browser frames exactly as before
- Reconnection logic and error handling in all three components must remain functional
- HTTP API calls (property search, pipeline operations, activity logs) must continue to use `NEXT_PUBLIC_API_URL` without modification
- WebSocket closure detection and cleanup must continue to work correctly
- All React hooks, state management, and component lifecycle behaviors must remain unchanged

**Scope:**
All inputs that do NOT involve WebSocket URL construction should be completely unaffected by this fix. This includes:
- WebSocket message parsing (`onmessage` handlers)
- WebSocket error handling (`onerror`, `onclose` handlers)
- Component state updates based on WebSocket events
- UI rendering logic for progress bars, terminal logs, and status indicators
- HTTP fetch calls to REST API endpoints
- Component mounting/unmounting behavior

## Hypothesized Root Cause

Based on the bug description and code analysis, the root causes are:

1. **Copy-Paste Development Pattern**: The hardcoded localhost URL `ws://127.0.0.1:10000` appears in both `dashboard/page.tsx` (line 239) and `AgentProgress.tsx` (line 44) with identical structure, suggesting copy-paste without updating for production deployment. Developers likely tested locally where hardcoded localhost works, then forgot to make URLs environment-aware before production deployment.

2. **Inconsistent Environment Variable Usage**: `LiveAgentTerminal.tsx` (line 21) demonstrates awareness of the environment variable by attempting `process.env.NEXT_PUBLIC_API_URL?.replace("http", "ws")`, but uses the `||` operator to fall back to localhost. This creates a silent failure mode where production deployment proceeds without error but connections fail at runtime.

3. **Lack of Centralized URL Construction Utility**: Each component implements (or fails to implement) WebSocket URL construction independently, leading to inconsistency. No shared utility function exists to ensure all components use the same environment-based URL construction logic.

4. **Incomplete Protocol Transformation Logic**: `LiveAgentTerminal.tsx` uses naive string replacement `replace("http", "ws")` which fails for HTTPS URLs. The correct transformation should be `http → ws` AND `https → wss`, not a simple string replacement that would turn `https://` into `wss://`.

## Correctness Properties

Property 1: Bug Condition - Dynamic WebSocket URL Construction in Production

_For any_ WebSocket connection attempt in production environment where the application is deployed to Vercel with `NEXT_PUBLIC_API_URL=https://griha-ai-theta.vercel.app`, the fixed code SHALL construct WebSocket URLs as `wss://griha-ai-theta.vercel.app/[endpoint]` with proper HTTPS-to-WSS protocol transformation, resulting in successful WebSocket connection establishment.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4**

Property 2: Preservation - Local Development Environment Compatibility

_For any_ WebSocket connection attempt in local development environment where `NEXT_PUBLIC_API_URL=http://localhost:10000`, the fixed code SHALL construct WebSocket URLs as `ws://localhost:10000/[endpoint]` with proper HTTP-to-WS protocol transformation, preserving existing development workflow functionality.

**Validates: Requirements 3.1**

Property 3: Preservation - WebSocket Message Handling and UI Updates

_For any_ WebSocket message event received from the backend (progress updates, status messages, terminal logs, browser frames), the fixed code SHALL process and display the data exactly as the original code does, preserving all existing message handling logic, state updates, and UI rendering behaviors.

**Validates: Requirements 3.2**

Property 4: Preservation - Error Handling and Reconnection Logic

_For any_ WebSocket error or connection closure event, the fixed code SHALL execute the same error handling, user notifications, and reconnection logic as the original code, preserving all existing resilience mechanisms.

**Validates: Requirements 3.3**

Property 5: Preservation - HTTP API Call Functionality

_For any_ HTTP fetch request to backend REST endpoints (property search, pipeline operations, activity logs), the fixed code SHALL continue to use `NEXT_PUBLIC_API_URL` exactly as currently implemented without any modifications, preserving all existing HTTP API functionality.

**Validates: Requirements 3.4**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct, we need to implement a centralized URL utility and update all three affected components.

**File**: `frontend/src/lib/api.ts` (new utility file)

**Function**: `buildWebSocketUrl(endpoint: string): string`

**Specific Changes**:
1. **Create Centralized Utility Function**: Add new file `frontend/src/lib/api.ts` with:
   - Function signature: `export function buildWebSocketUrl(endpoint: string): string`
   - Parse `NEXT_PUBLIC_API_URL` environment variable
   - Transform HTTP protocol to WebSocket protocol (http → ws, https → wss)
   - Handle edge cases: missing env var, malformed URLs, trailing slashes
   - Append the endpoint path correctly
   - Return fully qualified WebSocket URL

2. **Protocol Transformation Logic**:
   - Extract protocol from base URL using URL API
   - Map protocols: `"http:" → "ws:"` and `"https:" → "wss:"`
   - Preserve host, port, and any base path from the original URL
   - Ensure no double slashes when appending endpoint

3. **Error Handling**:
   - Throw descriptive error if `NEXT_PUBLIC_API_URL` is undefined in production
   - Provide fallback to `ws://localhost:10000` only in development mode (`process.env.NODE_ENV === 'development'`)
   - Log warnings in development when env var is missing

**File**: `frontend/src/app/dashboard/page.tsx`

**Function**: `startScraping` (around line 239)

**Specific Changes**:
1. Import the utility: `import { buildWebSocketUrl } from "@/lib/api";`
2. Replace hardcoded URL:
   ```typescript
   // OLD: const ws = new WebSocket(`ws://127.0.0.1:10000/api/ws/scrape-progress/${clientId}`);
   // NEW:
   const ws = new WebSocket(buildWebSocketUrl(`/api/ws/scrape-progress/${clientId}`));
   ```

**File**: `frontend/src/components/shared/AgentProgress.tsx`

**Function**: `connectWs` callback (around line 44)

**Specific Changes**:
1. Import the utility: `import { buildWebSocketUrl } from "@/lib/api";`
2. Replace hardcoded URL:
   ```typescript
   // OLD: const ws = new WebSocket(`ws://127.0.0.1:10000/api/ws/scrape-progress/${clientId}`);
   // NEW:
   const ws = new WebSocket(buildWebSocketUrl(`/api/ws/scrape-progress/${clientId}`));
   ```

**File**: `frontend/src/components/autopilot/LiveAgentTerminal.tsx`

**Function**: WebSocket initialization in `useEffect` (around line 21)

**Specific Changes**:
1. Import the utility: `import { buildWebSocketUrl } from "@/lib/api";`
2. Replace naive transformation with utility:
   ```typescript
   // OLD: const wsUrl = `${process.env.NEXT_PUBLIC_API_URL?.replace("http", "ws") || "ws://127.0.0.1:10000"}/ws/browser-stream/${hunt.id}`;
   // NEW:
   const wsUrl = buildWebSocketUrl(`/ws/browser-stream/${hunt.id}`);
   ```

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code in a production-like environment, then verify the fix works correctly across all three components and preserves existing WebSocket functionality.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm or refute the root cause analysis. If we refute, we will need to re-hypothesize.

**Test Plan**: Set up a production-like environment (e.g., Vercel preview deployment or local build with production env vars) and attempt to trigger WebSocket connections in all three components. Run these tests on the UNFIXED code to observe connection failures and confirm the root cause.

**Test Cases**:
1. **Dashboard Scraping in Production**: Set `NEXT_PUBLIC_API_URL=https://griha-ai-theta.vercel.app`, deploy to Vercel or run production build, navigate to dashboard, enter location "Bangalore", click "Scrape Live from Property Sites" (will fail on unfixed code - browser console shows WebSocket error to ws://127.0.0.1:10000)

2. **AgentProgress Component in Production**: Same environment as Test 1, trigger scraping which mounts AgentProgress component (will fail on unfixed code - component displays "Connection error" message)

3. **LiveAgentTerminal in Production**: Set `NEXT_PUBLIC_API_URL=https://griha-ai-theta.vercel.app`, open autopilot terminal feature (will fail on unfixed code if env var is set, but may appear to "work" with fallback logic masking the issue in development)

4. **Missing Environment Variable Test**: Unset or comment out `NEXT_PUBLIC_API_URL`, attempt to trigger any WebSocket feature (will fail on unfixed code - should expose silent fallback behavior in LiveAgentTerminal)

**Expected Counterexamples**:
- Browser DevTools Network tab shows WebSocket connection attempts to `ws://127.0.0.1:10000` instead of production URL
- WebSocket connection status remains in "CONNECTING" state then transitions to "CLOSED" with error code
- Components display "Connection error" or timeout messages
- Possible causes confirmed: hardcoded URLs in dashboard and AgentProgress, incorrect fallback in LiveAgentTerminal

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds (production deployment with WebSocket features), the fixed function produces the expected behavior (successful WebSocket connections).

**Pseudocode:**
```
FOR ALL input WHERE isBugCondition(input) DO
  wsUrl := buildWebSocketUrl_fixed(input.endpoint)
  connection := new WebSocket(wsUrl)
  
  ASSERT wsUrl STARTS_WITH "wss://" 
  ASSERT wsUrl CONTAINS productionDomain
  ASSERT wsUrl NOT CONTAINS "localhost" OR "127.0.0.1"
  ASSERT connection.readyState EVENTUALLY_EQUALS WebSocket.OPEN
  ASSERT connection.onmessage CAN receive messages
END FOR
```

**Testing Approach**: Manual testing in production-like environment with property-based thinking - test multiple endpoints, multiple environment configurations, and verify WebSocket lifecycle.

**Test Cases**:
1. **Production Dashboard Scraping**: Set `NEXT_PUBLIC_API_URL=https://griha-ai-theta.vercel.app`, trigger scraping, verify WebSocket URL is `wss://griha-ai-theta.vercel.app/api/ws/scrape-progress/${clientId}`, verify connection succeeds and progress updates are received

2. **Production AgentProgress**: Same setup as above, verify AgentProgress component connects successfully and displays live status updates

3. **Production LiveAgentTerminal**: Same setup, trigger autopilot feature, verify WebSocket URL is `wss://griha-ai-theta.vercel.app/ws/browser-stream/${hunt.id}`, verify browser frames stream correctly

4. **HTTPS to WSS Transformation**: Verify utility correctly transforms `https://` to `wss://` (not just replacing "http" with "ws")

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold (local development, existing WebSocket message handling, HTTP API calls), the fixed function produces the same result as the original function.

**Pseudocode:**
```
FOR ALL input WHERE NOT isBugCondition(input) DO
  // For local development
  IF input.environment = "development" AND input.baseUrl = "http://localhost:10000" THEN
    ASSERT buildWebSocketUrl_fixed(input.endpoint) = "ws://localhost:10000" + input.endpoint
    ASSERT connection succeeds
  END IF
  
  // For WebSocket message handling
  IF input.type = "websocket_message_event" THEN
    ASSERT handleMessage_original(input) = handleMessage_fixed(input)
  END IF
  
  // For HTTP API calls
  IF input.type = "http_fetch_request" THEN
    ASSERT fetch_original(input) = fetch_fixed(input)
  END IF
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because it provides systematic coverage of the input domain and catches edge cases that manual unit tests might miss.

**Test Plan**: First, observe and document existing behavior on UNFIXED code in local development for all three components. Then, apply the fix and verify all behaviors remain identical.

**Test Cases**:
1. **Local Development WebSocket Connections**: Set `NEXT_PUBLIC_API_URL=http://localhost:10000`, run all three WebSocket features, verify connections to `ws://localhost:10000/...` succeed and behave identically to unfixed code

2. **Message Handling Preservation**: Connect WebSocket in fixed code, send test messages from backend (progress updates, status changes, terminal logs, browser frames), verify all `onmessage` handlers process data identically to unfixed code and UI updates correctly

3. **Error Handling Preservation**: Simulate WebSocket errors (backend offline, network interruption, invalid messages), verify `onerror` and `onclose` handlers behave identically to unfixed code - same error messages, same retry logic, same UI state transitions

4. **HTTP API Preservation**: Make all existing HTTP fetch calls (property search, pipeline operations, activity logs) and verify they continue to use `NEXT_PUBLIC_API_URL` correctly without any interference from the WebSocket URL utility

5. **Reconnection Logic Preservation**: Close WebSocket connections intentionally (simulating backend restart), verify reconnection attempts in AgentProgress work identically to unfixed code

6. **localhost vs 127.0.0.1 Equivalence**: Test both `http://localhost:10000` and `http://127.0.0.1:10000` as `NEXT_PUBLIC_API_URL` values, verify utility handles both correctly (though both should work post-fix)

### Unit Tests

- Test `buildWebSocketUrl` utility with various inputs:
  - `http://localhost:10000` → `ws://localhost:10000/endpoint`
  - `https://griha-ai-theta.vercel.app` → `wss://griha-ai-theta.vercel.app/endpoint`
  - Trailing slashes in base URL or endpoint
  - Missing `NEXT_PUBLIC_API_URL` (should throw error in production, use fallback in development)
  - Base URLs with paths (e.g., `http://example.com/api`)
- Test error cases: undefined env var, invalid URLs, malformed protocols

### Property-Based Tests

- Generate random valid HTTP/HTTPS URLs with various domains, ports, and paths
- Verify `buildWebSocketUrl` always produces valid WebSocket URLs (ws:// or wss://)
- Verify protocol transformation is correct for all inputs
- Verify no double slashes or malformed URL components
- Generate random endpoints with leading/trailing slashes, special characters
- Verify concatenation logic produces valid URLs in all cases

### Integration Tests

- Full end-to-end test: Deploy to Vercel preview environment, trigger scraping feature, verify real-time updates display correctly
- Test all three components in sequence: Dashboard → AgentProgress → LiveAgentTerminal
- Verify WebSocket connections work across browser environments (Chrome, Firefox, Safari)
- Test with real backend WebSocket server sending actual messages
- Verify production deployment with `NODE_ENV=production` uses correct URLs
- Test switching between development and production builds
