# Implementation Plan

## Overview
This plan implements the WebSocket production URL fix by following the exploratory bugfix workflow: explore the bug condition first, establish preservation tests, then implement the fix with verification.

---

## Tasks

- [x] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - WebSocket Production URL Construction
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the bug exists in production environment
  - **Scoped PBT Approach**: Scope the property to concrete failing cases - production deployments attempting WebSocket connections with hardcoded localhost URLs
  - Test that WebSocket connections in production environment construct URLs dynamically from `NEXT_PUBLIC_API_URL` with proper protocol transformation
  - Verify that in production with `NEXT_PUBLIC_API_URL=https://griha-ai-theta.vercel.app`:
    - Dashboard scraping uses `wss://griha-ai-theta.vercel.app/api/ws/scrape-progress/${clientId}` (NOT `ws://127.0.0.1:10000`)
    - AgentProgress component uses `wss://griha-ai-theta.vercel.app/api/ws/scrape-progress/${clientId}` (NOT hardcoded localhost)
    - LiveAgentTerminal uses `wss://griha-ai-theta.vercel.app/ws/browser-stream/${huntId}` (NOT fallback localhost)
  - Verify protocol transformation: `https://` → `wss://` (not naive string replacement)
  - Run test on UNFIXED code in production-like environment (Vercel preview or local production build)
  - **EXPECTED OUTCOME**: Test FAILS (this is correct - it proves the bug exists)
  - Document counterexamples found:
    - Browser DevTools shows connection attempts to `ws://127.0.0.1:10000` instead of production URL
    - WebSocket status transitions to CLOSED with connection error
    - Components display "Connection error" or timeout messages
  - Mark task complete when test is written, run, and failures are documented
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Local Development and Message Handling
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for non-buggy scenarios:
    - Local development with `NEXT_PUBLIC_API_URL=http://localhost:10000`
    - WebSocket message handling (progress updates, terminal logs, browser frames)
    - Error handling and reconnection logic
    - HTTP API calls to REST endpoints
  - Write property-based tests capturing observed behavior patterns:
    - **Local Development WebSocket**: For all endpoints in local dev environment, WebSocket URLs should be `ws://localhost:10000/[endpoint]` and connections should succeed
    - **Message Handling**: For all WebSocket message events, `onmessage` handlers should process data and update UI identically to unfixed code
    - **Error Handling**: For all WebSocket error/close events, error handlers should execute retry logic and display messages identically to unfixed code
    - **HTTP API Preservation**: For all HTTP fetch calls (property search, pipeline ops, activity logs), requests should use `NEXT_PUBLIC_API_URL` without modification
    - **Reconnection Logic**: For all intentional WebSocket closures, reconnection attempts should behave identically to unfixed code
  - Property-based testing generates many test cases for stronger guarantees
  - Run tests on UNFIXED code in local development environment
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [ ] 3. Fix for WebSocket production URL construction

  - [x] 3.1 Create centralized WebSocket URL utility
    - Create new file `frontend/src/lib/api.ts`
    - Implement `buildWebSocketUrl(endpoint: string): string` function:
      - Parse `NEXT_PUBLIC_API_URL` environment variable
      - Extract protocol using URL API
      - Transform protocol: `"http:" → "ws:"` and `"https:" → "wss:"`
      - Preserve host, port, and any base path from original URL
      - Handle trailing slashes correctly (no double slashes when appending endpoint)
      - Throw descriptive error if env var undefined in production
      - Provide fallback to `ws://localhost:10000` only in development mode (`process.env.NODE_ENV === 'development'`)
      - Log warnings in development when env var is missing
    - _Bug_Condition: isBugCondition(input) where input.environment = "production" AND input.websocketUrl CONTAINS "127.0.0.1" OR "localhost" AND NOT DERIVED_FROM NEXT_PUBLIC_API_URL_
    - _Expected_Behavior: WebSocket URLs dynamically constructed with proper protocol transformation (https→wss, http→ws)_
    - _Preservation: Local development URLs (ws://localhost:10000), message handling, error handling, HTTP API calls, reconnection logic_
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.3, 3.4_

  - [-] 3.2 Update dashboard/page.tsx to use utility
    - Import utility: `import { buildWebSocketUrl } from "@/lib/api";`
    - Locate `startScraping` function (around line 239)
    - Replace hardcoded URL:
      ```typescript
      // OLD: const ws = new WebSocket(`ws://127.0.0.1:10000/api/ws/scrape-progress/${clientId}`);
      // NEW: const ws = new WebSocket(buildWebSocketUrl(`/api/ws/scrape-progress/${clientId}`));
      ```
    - Verify no other changes to WebSocket message handling, error handling, or component logic
    - _Bug_Condition: Dashboard scraping in production uses hardcoded localhost URL_
    - _Expected_Behavior: Dashboard uses dynamically constructed production WebSocket URL_
    - _Preservation: WebSocket message handling, scraping progress updates, error handling_
    - _Requirements: 2.1, 2.2, 3.2_

  - [-] 3.3 Update AgentProgress.tsx to use utility
    - Import utility: `import { buildWebSocketUrl } from "@/lib/api";`
    - Locate `connectWs` callback (around line 44)
    - Replace hardcoded URL:
      ```typescript
      // OLD: const ws = new WebSocket(`ws://127.0.0.1:10000/api/ws/scrape-progress/${clientId}`);
      // NEW: const ws = new WebSocket(buildWebSocketUrl(`/api/ws/scrape-progress/${clientId}`));
      ```
    - Verify no changes to message handlers, reconnection logic, or UI rendering
    - _Bug_Condition: AgentProgress component in production uses hardcoded localhost URL_
    - _Expected_Behavior: AgentProgress uses dynamically constructed production WebSocket URL_
    - _Preservation: Progress visualization, reconnection logic, error states_
    - _Requirements: 2.1, 2.2, 3.2, 3.3_

  - [-] 3.4 Update LiveAgentTerminal.tsx to use utility
    - Import utility: `import { buildWebSocketUrl } from "@/lib/api";`
    - Locate WebSocket initialization in `useEffect` (around line 21)
    - Replace naive transformation:
      ```typescript
      // OLD: const wsUrl = `${process.env.NEXT_PUBLIC_API_URL?.replace("http", "ws") || "ws://127.0.0.1:10000"}/ws/browser-stream/${hunt.id}`;
      // NEW: const wsUrl = buildWebSocketUrl(`/ws/browser-stream/${hunt.id}`);
      ```
    - Remove fallback logic (now handled by utility)
    - Verify no changes to terminal log rendering, browser frame display, or error handling
    - _Bug_Condition: LiveAgentTerminal in production has incorrect fallback and naive protocol replacement_
    - _Expected_Behavior: LiveAgentTerminal uses correct protocol transformation without silent fallback_
    - _Preservation: Terminal streaming, browser automation display, error handling_
    - _Requirements: 2.1, 2.3, 2.4, 3.2_

  - [ ] 3.5 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Dynamic WebSocket URL Construction
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Deploy to Vercel preview or run production build locally
    - Set `NEXT_PUBLIC_API_URL=https://griha-ai-theta.vercel.app`
    - Run bug condition exploration test from step 1
    - Verify WebSocket URLs are correctly constructed:
      - Dashboard: `wss://griha-ai-theta.vercel.app/api/ws/scrape-progress/${clientId}`
      - AgentProgress: `wss://griha-ai-theta.vercel.app/api/ws/scrape-progress/${clientId}`
      - LiveAgentTerminal: `wss://griha-ai-theta.vercel.app/ws/browser-stream/${huntId}`
    - Verify WebSocket connections succeed (readyState = OPEN)
    - Verify messages are received and processed
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [ ] 3.6 Verify preservation tests still pass
    - **Property 2: Preservation** - Unchanged Local and Message Handling
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run preservation property tests from step 2
    - Test in local development with `NEXT_PUBLIC_API_URL=http://localhost:10000`
    - Verify local WebSocket connections still work (`ws://localhost:10000/[endpoint]`)
    - Verify message handling unchanged (progress updates, terminal logs, frames)
    - Verify error handling unchanged (retry logic, error messages, UI states)
    - Verify HTTP API calls unchanged (property search, pipeline ops, activity logs)
    - Verify reconnection logic unchanged
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all tests still pass after fix (no regressions)
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [ ] 4. Checkpoint - Ensure all tests pass
  - Run complete test suite (bug condition + preservation tests)
  - Verify in both production and development environments
  - Test all three components: Dashboard scraping, AgentProgress, LiveAgentTerminal
  - Verify WebSocket connections work across different scenarios:
    - Production deployment on Vercel with production backend
    - Local development with local backend
    - Various endpoint paths and parameters
  - Check browser DevTools Network tab for correct WebSocket URLs
  - Verify no console errors or warnings
  - Ask the user if any questions or issues arise during testing

---

## Notes

- **Property-Based Testing**: Tests use property-based approach to generate multiple test cases and ensure robust coverage
- **Exploration First**: Task 1 explores the bug on unfixed code to understand root cause before fixing
- **Observation-Based Preservation**: Task 2 observes actual behavior on unfixed code to define preservation properties
- **Centralized Utility**: The fix introduces a single source of truth for WebSocket URL construction
- **Protocol Transformation**: Correct transformation is `http:` → `ws:` and `https:` → `wss:` (not naive string replacement)
- **Environment Awareness**: Utility handles production vs development environments differently
- **No Silent Fallbacks**: Error handling is explicit, no silent fallback to localhost in production
- **All Three Components**: The fix must be applied consistently across dashboard/page.tsx, AgentProgress.tsx, and LiveAgentTerminal.tsx
