# API Reference - Autonomous Financial Research Platform

## Base URL
```
http://localhost:8000/api/v1
```

## Authentication
Currently using API key headers (to be implemented):
```
Authorization: Bearer <api_key>
```

## Research Endpoints

### Start Autonomous Research
```
POST /research/start
```

**Request Body**:
```json
{
  "company": "string",
  "query": "string",
  "auto_approve": "boolean (default: false)",
  "custom_context": "object (optional)"
}
```

**Response** (202 Accepted):
```json
{
  "research_id": "string",
  "status": "string",
  "message": "string",
  "plan": {
    "plan_id": "string",
    "company": "string",
    "query": "string",
    "complexity": "simple|moderate|complex|comprehensive",
    "estimated_duration_seconds": "integer",
    "steps": [
      {
        "step_id": "string",
        "agent_type": "string",
        "dependencies": ["string"],
        "parallel_group": "string|null",
        "estimated_duration_seconds": "integer",
        "priority": "integer"
      }
    ]
  }
}
```

**Status Values**:
- `pending_approval` - Awaiting human approval
- `executing` - Plan execution in progress
- `completed` - All steps finished successfully
- `partial_failure` - Some steps failed
- `failed` - Critical failure

---

### Get Research Status
```
GET /research/{research_id}
```

**Response** (200 OK):
```json
{
  "research_id": "string",
  "company": "string",
  "query": "string",
  "status": "string",
  "plan_id": "string|null",
  "started_at": "ISO8601 datetime|null",
  "completed_at": "ISO8601 datetime|null",
  "duration_seconds": "float",
  "results": {
    "step_id": {
      "status": "completed|failed",
      "agent": "string",
      "duration_seconds": "float",
      "data": "object"
    }
  },
  "conclusions": ["string"],
  "error": "string|null"
}
```

---

### Get Research History
```
GET /research/history
```

**Query Parameters**:
- `company` (optional): Filter by company
- `limit` (default: 20, max: 100): Number of results
- `status` (optional): Filter by status

**Response** (200 OK):
```json
{
  "research_history": [
    {
      "research_id": "string",
      "company": "string",
      "query": "string",
      "status": "string",
      "started_at": "ISO8601 datetime",
      "completed_at": "ISO8601 datetime|null",
      "duration_seconds": "float"
    }
  ]
}
```

---

### Get System Status
```
GET /research/status
```

**Response** (200 OK):
```json
{
  "active_research": "integer",
  "max_parallel": "integer",
  "timestamp": "ISO8601 datetime"
}
```

---

## Watchlist Endpoints

### Create Watchlist
```
POST /watchlists
```

**Request Body**:
```json
{
  "name": "string",
  "description": "string (default: \"\")",
  "type": "personal|portfolio|sector|thematic|competitor (default: \"personal\")",
  "owner_id": "string",
  "companies": ["string"] (optional)
}
```

**Response** (201 Created):
```json
{
  "watchlist_id": "string",
  "name": "string",
  "description": "string",
  "type": "string",
  "owner_id": "string",
  "items": [
    {
      "company": "string",
      "ticker": "string|null",
      "added_at": "ISO8601 datetime",
      "notes": "string",
      "tags": ["string"],
      "target_price": "float|null",
      "stop_loss": "float|null",
      "position_size": "float|null"
    }
  ],
  "alert_rules": [],
  "created_at": "ISO8601 datetime",
  "updated_at": "ISO8601 datetime",
  "is_active": "boolean"
}
```

---

### List Watchlists
```
GET /watchlists
```

**Query Parameters**:
- `owner_id` (optional): Filter by owner

**Response** (200 OK):
```json
{
  "watchlists": [
    {
      "watchlist_id": "string",
      "name": "string",
      "type": "string",
      "owner_id": "string",
      "item_count": "integer",
      "is_active": "boolean"
    }
  ]
}
```

---

### Get Watchlist Details
```
GET /watchlists/{watchlist_id}
```

**Response** (200 OK):
```json
{
  "watchlist_id": "string",
  "name": "string",
  "description": "string",
  "type": "string",
  "owner_id": "string",
  "items": [...],
  "alert_rules": [...],
  "created_at": "ISO8601 datetime",
  "updated_at": "ISO8601 datetime",
  "is_active": "boolean"
}
```

---

### Add Company to Watchlist
```
POST /watchlists/{watchlist_id}/companies
```

**Request Body**:
```json
{
  "company": "string",
  "ticker": "string|null",
  "notes": "string (default: \"\")",
  "target_price": "float|null",
  "stop_loss": "float|null"
}
```

**Response** (200 OK):
```json
{
  "success": "boolean",
  "message": "string"
}
```

---

### Remove Company from Watchlist
```
DELETE /watchlists/{watchlist_id}/companies/{company}
```

**Response** (200 OK):
```json
{
  "success": "boolean",
  "message": "string"
}
```

---

### Create Alert Rule
```
POST /watchlists/{watchlist_id}/alerts
```

**Request Body**:
```json
{
  "name": "string",
  "description": "string",
  "conditions": {
    "price_above": "float",
    "price_below": "float",
    "price_change_pct": "float",
    "volume_spike": "float",
    "rsi_above": "float",
    "rsi_below": "float",
    "news_sentiment": "float",
    "news_count": "integer",
    "agent_signal": {
      "agent": "string",
      "signal": "string"
    }
  },
  "severity": "info|warning|critical (default: \"warning\")",
  "channels": ["email", "slack", "discord", "webhook", "console", "in_app"],
  "company": "string|null",
  "cooldown_minutes": "integer (default: 60)"
}
```

**Response** (201 Created):
```json
{
  "rule_id": "string",
  "watchlist_id": "string",
  "name": "string",
  "description": "string",
  "company": "string|null",
  "conditions": "object",
  "severity": "string",
  "channels": ["string"],
  "cooldown_minutes": "integer",
  "is_active": "boolean",
  "created_at": "ISO8601 datetime",
  "last_triggered": "ISO8601 datetime|null",
  "trigger_count": "integer"
}
```

---

## Approval Endpoints

### Get Approval Request
```
GET /approval/{request_id}
```

**Response** (200 OK):
```json
{
  "request_id": "string",
  "title": "string",
  "description": "string",
  "request_type": "string",
  "reference_id": "string",
  "reference_type": "string",
  "requester_id": "string",
  "requester_name": "string",
  "approvers": [
    {
      "user_id": "string",
      "name": "string",
      "email": "string",
      "role": "string",
      "is_required": "boolean",
      "order": "integer"
    }
  ],
  "status": "pending|approved|rejected|changes_requested|escalated|expired|cancelled",
  "current_approver_index": "integer",
  "actions": [
    {
      "action_id": "string",
      "action_type": "approve|reject|request_changes|escalate|delegate|comment",
      "user_id": "string",
      "user_name": "string",
      "comment": "string",
      "timestamp": "ISO8601 datetime"
    }
  ],
  "created_at": "ISO8601 datetime",
  "updated_at": "ISO8601 datetime",
  "completed_at": "ISO8601 datetime|null",
  "expires_at": "ISO8601 datetime|null"
}
```

---

### Process Approval Action
```
POST /approval/{request_id}/action
```

**Request Body**:
```json
{
  "action": "approve|reject|request_changes|escalate|delegate|comment",
  "user_id": "string",
  "user_name": "string",
  "comment": "string (default: \"\")",
  "metadata": "object (optional)"
}
```

**Response** (200 OK): Updated approval request object

**Action Details**:
| Action | Description | Metadata |
|--------|-------------|----------|
| `approve` | Approve and move to next approver | - |
| `reject` | Reject request | - |
| `request_changes` | Request modifications | - |
| `escalate` | Escalate to higher authority | `escalated_to`, `escalated_name`, `escalated_email` |
| `delegate` | Delegate to another approver | `delegate_to`, `delegate_name`, `delegate_email` |
| `comment` | Add comment without state change | - |

---

### List Approval Requests
```
GET /approval
```

**Query Parameters**:
- `user_id` (optional): Filter by approver
- `status` (optional): Filter by status

**Response** (200 OK):
```json
{
  "requests": [
    {
      "request_id": "string",
      "title": "string",
      "status": "string",
      "requester_name": "string",
      "created_at": "ISO8601 datetime",
      "current_approver": "string"
    }
  ]
}
```

---

## Report Endpoints

### Generate Report
```
POST /reports/generate
```

**Request Body**:
```json
{
  "report_type": "executive_summary|analyst_report|investment_thesis|company_snapshot|industry_analysis|daily_briefing|weekly_briefing|monthly_intelligence",
  "company": "string",
  "session_id": "string|null",
  "format": "markdown|html|json (default: \"markdown\")",
  "custom_data": "object (optional)"
}
```

**Response** (200 OK):
```json
{
  "report_id": "string",
  "report_type": "string",
  "format": "string",
  "content": "string",
  "generated_at": "ISO8601 datetime",
  "file_path": "string",
  "metadata": "object"
}
```

---

### List Reports
```
GET /reports
```

**Query Parameters**:
- `company` (optional): Filter by company
- `limit` (default: 20, max: 100): Number of results

**Response** (200 OK):
```json
{
  "reports": [
    {
      "report_id": "string",
      "report_type": "string",
      "company": "string",
      "format": "string",
      "generated_at": "ISO8601 datetime",
      "file_path": "string"
    }
  ]
}
```

---

## Error Responses

All endpoints may return standard error responses:

### 400 Bad Request
```json
{
  "detail": "Invalid request parameters"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 409 Conflict
```json
{
  "detail": "Resource already exists or conflict"
}
```

### 422 Unprocessable Entity
```json
{
  "detail": [
    {
      "loc": ["body", "field"],
      "msg": "Validation error",
      "type": "value_error"
    }
  ]
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

---

## Rate Limiting

Default limits (configurable):
- 100 requests per minute per IP
- Higher limits for authenticated users

Headers returned:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 99
X-RateLimit-Reset: 1699999999
```

---

## Webhooks

For real-time updates, configure webhook endpoints:

### Research Completion
```json
{
  "event": "research.completed",
  "research_id": "string",
  "company": "string",
  "status": "completed",
  "timestamp": "ISO8601"
}
```

### Alert Triggered
```json
{
  "event": "alert.triggered",
  "alert_id": "string",
  "watchlist_id": "string",
  "company": "string",
  "rule_name": "string",
  "severity": "string",
  "data": "object",
  "timestamp": "ISO8601"
}
```

### Approval Required
```json
{
  "event": "approval.required",
  "request_id": "string",
  "title": "string",
  "approver_email": "string",
  "expires_at": "ISO8601",
  "timestamp": "ISO8601"
}
```

---

## Example Workflows

### Complete Research with Approval
```bash
# 1. Start research
curl -X POST http://localhost:8000/api/v1/research/start \
  -H "Content-Type: application/json" \
  -d '{"company": "NVDA", "query": "Full investment thesis", "auto_approve": false}'

# Response: {"research_id": "abc123", "status": "pending_approval", ...}

# 2. Check approval request
curl http://localhost:8000/api/v1/approval

# 3. Approve (as senior analyst)
curl -X POST http://localhost:8000/api/v1/approval/{request_id}/action \
  -H "Content-Type: application/json" \
  -d '{"action": "approve", "user_id": "senior_analyst", "user_name": "Jane Doe"}'

# 4. Poll for results
curl http://localhost:8000/api/v1/research/abc123
```

### Auto-Approved Research
```bash
curl -X POST http://localhost:8000/api/v1/research/start \
  -H "Content-Type: application/json" \
  -d '{"company": "AAPL", "query": "Quick financial snapshot", "auto_approve": true}'
```

### Watchlist with Alerts
```bash
# Create watchlist
curl -X POST http://localhost:8000/api/v1/watchlists \
  -H "Content-Type: application/json" \
  -d '{"name": "My Portfolio", "type": "portfolio", "owner_id": "user1", "companies": ["AAPL", "MSFT", "GOOGL"]}'

# Add price alert
curl -X POST http://localhost:8000/api/v1/watchlists/{watchlist_id}/alerts \
  -H "Content-Type: application/json" \
  -d '{"name": "5% Move Alert", "conditions": {"price_change_pct": 5.0}, "channels": ["email", "slack"]}'
```

### Generate Report
```bash
curl -X POST http://localhost:8000/api/v1/reports/generate \
  -H "Content-Type: application/json" \
  -d '{"report_type": "analyst_report", "company": "NVDA", "session_id": "abc123", "format": "html"}'
```

---

## Data Models

### ExecutionPlan
```typescript
interface ExecutionPlan {
  plan_id: string;
  query: string;
  company: string;
  complexity: "simple" | "moderate" | "complex" | "comprehensive";
  steps: ExecutionStep[];
  estimated_total_duration: number;
  metadata: object;
}

interface ExecutionStep {
  step_id: string;
  agent_type: string;
  task: object;
  dependencies: string[];
  parallel_group: string | null;
  estimated_duration_seconds: number;
  priority: number;
  metadata: object;
}
```

### PlanExecution
```typescript
interface PlanExecution {
  plan_id: string;
  plan: ExecutionPlan;
  step_results: Record<string, StepResult>;
  status: "pending" | "running" | "completed" | "partial_failure" | "failed";
  started_at: string | null;
  completed_at: string | null;
  total_duration_seconds: number;
  error: string | null;
  metadata: object;
  shared_context: object;
  completed_steps: number;
  total_steps: number;
}

interface StepResult {
  step_id: string;
  agent_type: string;
  status: "pending" | "running" | "completed" | "failed" | "skipped";
  result: object | null;
  error: string | null;
  started_at: string | null;
  completed_at: string | null;
  duration_seconds: number;
  metadata: object;
}
```

### ResearchSession
```typescript
interface ResearchSession {
  session_id: string;
  company: string;
  query: string;
  plan_id: string | null;
  status: string;
  steps: object[];
  results: object;
  conclusions: string[];
  reports: string[];
  started_at: string;
  completed_at: string | null;
  duration_seconds: number;
  error: string | null;
  metadata: object;
}
```

### WatchlistData
```typescript
interface WatchlistData {
  watchlist_id: string;
  name: string;
  description: string;
  type: "personal" | "portfolio" | "sector" | "thematic" | "competitor";
  owner_id: string;
  items: WatchlistItemData[];
  alert_rules: AlertRuleData[];
  created_at: string;
  updated_at: string;
  is_active: boolean;
  metadata: object;
}

interface WatchlistItemData {
  company: string;
  ticker: string | null;
  added_at: string;
  notes: string;
  tags: string[];
  target_price: number | null;
  stop_loss: number | null;
  position_size: number | null;
  metadata: object;
}

interface AlertRuleData {
  rule_id: string;
  watchlist_id: string;
  name: string;
  description: string;
  company: string | null;
  conditions: object;
  severity: "info" | "warning" | "critical";
  channels: string[];
  cooldown_minutes: number;
  is_active: boolean;
  created_at: string;
  last_triggered: string | null;
  trigger_count: number;
}
```

### ApprovalRequest
```typescript
interface ApprovalRequest {
  request_id: string;
  title: string;
  description: string;
  request_type: string;
  reference_id: string;
  reference_type: string;
  requester_id: string;
  requester_name: string;
  approvers: Approver[];
  status: "pending" | "approved" | "rejected" | "changes_requested" | "escalated" | "expired" | "cancelled";
  current_approver_index: number;
  actions: ApprovalActionRecord[];
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  expires_at: string | null;
  metadata: object;
}

interface Approver {
  user_id: string;
  name: string;
  email: string;
  role: string;
  is_required: boolean;
  order: number;
}

interface ApprovalActionRecord {
  action_id: string;
  request_id: string;
  action_type: "approve" | "reject" | "request_changes" | "escalate" | "delegate" | "comment";
  user_id: string;
  user_name: string;
  comment: string;
  timestamp: string;
  metadata: object;
}
```

### Report
```typescript
interface Report {
  report_id: string;
  report_type: "executive_summary" | "analyst_report" | "investment_thesis" | "company_snapshot" | "industry_analysis" | "daily_briefing" | "weekly_briefing" | "monthly_intelligence";
  format: "markdown" | "html" | "json";
  content: string;
  generated_at: string;
  file_path: string | null;
  metadata: object;
}
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.5.0 | 2026-07-18 | Phase 7: Autonomous Research Workflows |

---

## Support

For API issues or questions, refer to:
- Implementation Report: `IMPLEMENTATION_REPORT.md`
- Architecture: `WORKFLOW_ARCHITECTURE.md`
- Research Engine: `RESEARCH_ENGINE.md`