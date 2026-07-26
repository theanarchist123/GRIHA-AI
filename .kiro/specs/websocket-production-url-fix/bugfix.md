# Bugfix Requirements Document

## Introduction

The frontend application fails to establish WebSocket connections in production deployment on Vercel. The application uses hardcoded localhost URLs (`ws://127.0.0.1:10000`) instead of dynamically selecting the appropriate backend URL based on the deployment environment. This prevents real-time scraping progress updates from functioning in production, while the environment variable `NEXT_PUBLIC_API_URL` exists but is not consistently used for WebSocket connections.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN the application is deployed to production on Vercel AND a user triggers scraping features THEN the system attempts to connect to `ws://127.0.0.1:10000/api/ws/scrape-progress/{clientId}` resulting in connection failure

1.2 WHEN the WebSocket connection is initialized in `dashboard/page.tsx` (line 239) THEN the system uses hardcoded localhost URL instead of the production backend URL

1.3 WHEN the WebSocket connection is initialized in `AgentProgress.tsx` (line 44) THEN the system uses hardcoded localhost URL instead of the production backend URL

1.4 WHEN the WebSocket connection is initialized in `LiveAgentTerminal.tsx` (line 21) THEN the system falls back to localhost URL when the environment variable is not properly configured or the URL transformation is incorrect

### Expected Behavior (Correct)

2.1 WHEN the application is deployed to production on Vercel AND a user triggers scraping features THEN the system SHALL connect to `wss://griha-ai-theta.vercel.app/api/ws/scrape-progress/{clientId}` successfully

2.2 WHEN the WebSocket connection is initialized in `dashboard/page.tsx` THEN the system SHALL dynamically construct the WebSocket URL using `NEXT_PUBLIC_API_URL` environment variable with proper protocol transformation (https→wss, http→ws)

2.3 WHEN the WebSocket connection is initialized in `AgentProgress.tsx` THEN the system SHALL dynamically construct the WebSocket URL using `NEXT_PUBLIC_API_URL` environment variable with proper protocol transformation (https→wss, http→ws)

2.4 WHEN the WebSocket connection is initialized in `LiveAgentTerminal.tsx` THEN the system SHALL use the environment variable without falling back to localhost, or SHALL provide a clear error message if the environment variable is missing

### Unchanged Behavior (Regression Prevention)

3.1 WHEN the application runs in local development environment with `NEXT_PUBLIC_API_URL=http://localhost:10000` THEN the system SHALL CONTINUE TO connect to `ws://localhost:10000/api/ws/scrape-progress/{clientId}` successfully

3.2 WHEN the WebSocket connection is established AND messages are received from the backend THEN the system SHALL CONTINUE TO process and display scraping progress updates correctly

3.3 WHEN the WebSocket connection closes or encounters errors THEN the system SHALL CONTINUE TO handle reconnection logic and error states as currently implemented

3.4 WHEN other HTTP API calls are made to the backend THEN the system SHALL CONTINUE TO function correctly with the existing `NEXT_PUBLIC_API_URL` configuration

---

## Bug Condition Analysis

### Bug Condition Function

```pascal
FUNCTION isBugCondition(X)
  INPUT: X of type WebSocketConnectionAttempt
  OUTPUT: boolean
  
  // Returns true when WebSocket URL is hardcoded to localhost
  // in production environment
  RETURN (X.environment = "production") AND 
         (X.websocketUrl CONTAINS "127.0.0.1" OR 
          X.websocketUrl CONTAINS "localhost") AND
         (X.websocketUrl NOT DERIVED_FROM X.environmentVariable)
END FUNCTION
```

### Fix Checking Property

```pascal
// Property: Fix Checking - Dynamic WebSocket URL Construction
FOR ALL X WHERE isBugCondition(X) DO
  result ← constructWebSocketUrl'(X)
  ASSERT (result DERIVED_FROM NEXT_PUBLIC_API_URL) AND
         (X.environment = "production" IMPLIES result CONTAINS "wss://griha-ai-theta.vercel.app") AND
         (X.environment = "development" IMPLIES result CONTAINS "ws://localhost") AND
         (websocket_connection_succeeds(result))
END FOR
```

### Preservation Checking Property

```pascal
// Property: Preservation Checking - Existing Functionality
FOR ALL X WHERE NOT isBugCondition(X) DO
  // For components already using environment variables correctly
  // or for non-WebSocket functionality
  ASSERT F(X) = F'(X)
END FOR
```

Where:
- **F**: The original code with hardcoded WebSocket URLs
- **F'**: The fixed code with dynamic environment-based WebSocket URLs
- **NEXT_PUBLIC_API_URL**: Environment variable containing the backend base URL
