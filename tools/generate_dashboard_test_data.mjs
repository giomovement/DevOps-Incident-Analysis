import fs from 'node:fs';
import path from 'node:path';

const outputDir = path.resolve('generated_dashboard_test_data');
fs.mkdirSync(outputDir, { recursive: true });

const incidents = [
  ['01','postgres-replica-failover','Postgres replica failover stalled','orders-api','production','critical','active','database',null,3],
  ['02','checkout-cross-zone-dns','Checkout cross-zone DNS outage','checkout-api','production','critical','active','networking',null,2],
  ['03','kubernetes-node-pressure','Kubernetes node memory pressure','recommendations-api','production','critical','active','infrastructure',null,3],
  ['04','identity-credential-attack','Credential stuffing against customer login','identity-api','production','critical','active','security',null,2],
  ['05','payment-gateway-collapse','Payment gateway authorization collapse','payments-api','production','critical','resolved','dependency',42,2],
  ['06','catalog-storage-exhaustion','Catalog image storage exhausted','catalog-media','production','critical','resolved','capacity',95,2],
  ['07','search-p99-regression','Search p99 latency regression','search-api','production','high','active','performance',null,1],
  ['08','cart-release-regression','Cart release validation regression','cart-api','staging','high','active','deployment',null,2],
  ['09','oauth-key-rotation','OAuth signing-key rotation failure','identity-api','production','high','active','authentication',null,1],
  ['10','redis-eviction-storm','Redis eviction storm','session-api','production','high','resolved','capacity',18,2],
  ['11','kafka-consumer-lag','Order-event Kafka consumer lag','fulfilment-worker','production','high','resolved','performance',73,1],
  ['12','inventory-deadlock','Inventory database deadlocks','inventory-api','production','high','resolved','database',240,2],
  ['13','cdn-cache-miss','CDN cache-miss increase','storefront-web','production','medium','active','performance',null,1],
  ['14','staging-certificate-warning','Staging TLS certificate warning','edge-gateway','staging','medium','resolved','networking',8,1],
  ['15','email-queue-depth','Transactional email queue depth','notification-worker','production','medium','resolved','capacity',27,2],
  ['16','recommendation-canary','Recommendation canary anomaly','recommendations-api','test','medium','resolved','deployment',55,1],
  ['17','warehouse-api-retries','Warehouse API retry increase','fulfilment-api','production','medium','resolved','dependency',360,1],
  ['18','admin-login-expiry','Admin session token expiry','admin-portal','development','medium','resolved','authentication',1440,1],
  ['19','synthetic-error-budget','Synthetic error-budget notification','synthetics','test','low','active','application',null,1],
  ['20','nightly-backup-delay','Nightly backup completed late','backup-worker','production','low','resolved','performance',12,1],
  ['21','development-dns-retry','Development DNS retry recovered','developer-portal','development','low','resolved','networking',33,1],
  ['22','feature-flag-validation','Feature flag validation notice','pricing-api','staging','low','resolved','deployment',120,1],
  ['23','cache-key-auth-refresh','Cache key authentication refresh','profile-api','test','low','resolved','authentication',720,1],
  ['24','worker-error-budget','Worker error-budget sampling event','analytics-worker','development','low','resolved','application',2880,1],
];

const issueText = {
  database: ['Database health baseline recorded', 'Postgres connection pool saturation detected', 'Database writes failed with SQLSTATE=08001', 'Connection pool recovered after failover'],
  networking: ['Network resolver baseline recorded', 'DNS lookup timeout increased across the zone', 'DNS resolution failed after repeated attempts', 'DNS and socket health checks recovered'],
  infrastructure: ['Kubernetes workload baseline recorded', 'Node memory pressure is increasing', 'Pod eviction and CrashLoopBackOff affected workloads', 'Kubernetes pods stabilized on replacement nodes'],
  security: ['Authentication baseline recorded', 'Suspicious unauthorized login attempts increased', 'Brute-force credential attack threshold exceeded', 'Malicious sources blocked and login rate normalized'],
  dependency: ['Upstream dependency baseline recorded', 'Upstream service returned intermittent 503 responses', 'Dependency service unavailable and requests failed', 'Traffic shifted and upstream availability recovered'],
  capacity: ['Resource capacity baseline recorded', 'Disk quota or cache capacity crossed warning threshold', 'No space left and resource pool exhausted', 'Capacity expanded and backlog cleared'],
  performance: ['Latency baseline recorded', 'p95 latency exceeded the operating threshold', 'Request timeout rate increased and SLO was breached', 'Latency returned to the expected range'],
  deployment: ['Deployment validation started', 'New release revision produced warning signals', 'Deployment regression caused failed requests', 'Rollback completed and validation passed'],
  authentication: ['Authentication health baseline recorded', 'OAuth token expiry warnings increased', 'Authentication failed because signing keys were unavailable', 'Token validation and login success recovered'],
  application: ['Application error budget baseline recorded', 'Error budget monitor recorded a low-impact anomaly', 'Transient application error sample remained below alert threshold', 'Error rate returned to baseline'],
};

const severityLevels = {
  critical: ['INFO','WARN','CRITICAL','INFO'],
  high: ['INFO','WARN','ERROR','INFO'],
  medium: ['INFO','WARN','WARN','INFO'],
  low: ['DEBUG','INFO','INFO','DEBUG'],
};

const base = Date.parse('2026-09-06T00:00:00Z');
const manifest = [];

for (const [index, slug, title, service, environment, severity, status, issue, resolutionMinutes, fileCount] of incidents) {
  const startHour = (Number(index) * 5) % 23;
  const incidentFiles = [];
  for (let fileIndex = 1; fileIndex <= fileCount; fileIndex++) {
    const filename = fileCount === 1 ? `${index}-${slug}.json` : `${index}-${slug}-part-${fileIndex}.json`;
    incidentFiles.push(filename);
    const count = 4 + ((Number(index) + fileIndex) % 7);
    const events = [];
    for (let eventIndex = 0; eventIndex < count; eventIndex++) {
      const phase = Math.min(3, Math.floor(eventIndex * 4 / count));
      const eventTime = new Date(base + startHour * 3600000 + fileIndex * 180000 + eventIndex * 210000);
      const primaryService = fileIndex === 1 ? service : `${service}-dependency`;
      const correlation = `${slug}-${String(Math.floor(eventIndex / 2) + 1).padStart(3, '0')}`;
      const event = {
        timestamp: eventTime.toISOString(),
        level: severityLevels[severity][phase],
        service: primaryService,
        component: fileIndex === 1 ? 'application' : 'dependency-client',
        environment,
        region: Number(index) % 3 === 0 ? 'us-east-1' : Number(index) % 3 === 1 ? 'eu-west-2' : 'ap-southeast-1',
        correlation_id: eventIndex === count - 1 && Number(index) % 4 === 0 ? null : correlation,
        message: `${issueText[issue][phase]}; sample=${eventIndex + 1} incident=${slug}`,
        affected_users: phase === 2 ? Number(index) * 137 + eventIndex * 11 : 0,
        failed_requests: phase === 2 ? Number(index) * 43 + eventIndex * 7 : 0,
        error_rate_percent: phase === 2 ? Number((Number(index) * 0.91 + eventIndex / 10).toFixed(2)) : Number((phase * 0.17).toFixed(2)),
        p95_ms: 80 + phase * 620 + eventIndex * 17,
        availability_percent: Number((99.99 - phase * Number(index) * 0.37).toFixed(2)),
        change_id: issue === 'deployment' ? `chg-20260906-${index}` : null,
        deployment: `${service}-2026.09.${String(Number(index)).padStart(2, '0')}`,
      };
      if (eventIndex === 1 && Number(index) % 5 === 0) delete event.timestamp;
      events.push(event);
    }
    fs.writeFileSync(path.join(outputDir, filename), JSON.stringify(events, null, 2) + '\n');
  }
  manifest.push({
    incident_number: Number(index), slug, title,
    description: `Dashboard coverage fixture for a ${severity} ${issue} incident affecting ${service}.`,
    service, environment,
    deployment: `${service}-2026.09.${index}`,
    expected_severity: severity,
    desired_status: status,
    resolve_after_minutes: resolutionMinutes,
    files: incidentFiles,
  });
}

fs.writeFileSync(path.join(outputDir, 'incident-manifest.json'), JSON.stringify(manifest, null, 2) + '\n');
const totalLogFiles = manifest.reduce((sum, item) => sum + item.files.length, 0);
fs.writeFileSync(path.join(outputDir, 'README.md'), `# Dashboard test-data pack

This pack contains 24 incident scenarios and ${totalLogFiles} JSON log files. Each log file uses the same array-of-event-objects format as the supplied examples.

Use \`incident-manifest.json\` to create each incident and upload every file listed for it. After analysis, set the incident to \`desired_status\`. For resolved fixtures, \`resolve_after_minutes\` describes the intended MTTR spread; the current application calculates MTTR from the actual database creation and resolution timestamps, not from log timestamps.

Coverage includes all four severities, active and resolved states, nine classifier families, four environments, multiple regions, single- and multi-file incidents, missing timestamps, missing correlation IDs, quiet chart buckets, and event bursts.
`);

console.log(`Generated ${manifest.length} incidents and ${totalLogFiles} log files in ${outputDir}`);
