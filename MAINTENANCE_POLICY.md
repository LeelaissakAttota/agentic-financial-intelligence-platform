# Maintenance Policy
## Financial Research Agent v2.0.0

**Effective Date**: 2026-07-18  
**Version**: v2.0.0-stable  
**Status**: Long-Term Maintenance Mode

---

## Policy Overview

This project is now in **Long-Term Maintenance Mode**. It serves as the Financial Intelligence Engine for the JARVIS AI CEO ecosystem. No new features will be developed in this repository. All future feature development will occur within the JARVIS AI CEO repository.

---

## Permitted Activities

### ✅ Bug Fixes
- Fix regressions in existing functionality
- Correct incorrect calculations or logic errors
- Resolve edge cases causing crashes or incorrect outputs
- Fix test failures due to environmental changes

### ✅ Security Patches
- Update dependencies with known CVEs
- Patch authentication/authorization vulnerabilities
- Fix injection vulnerabilities (SQL, prompt, path traversal)
- Update cryptographic implementations

### ✅ Dependency Updates
- Patch version updates (x.y.Z) for all dependencies
- Minor version updates (x.Y.z) after compatibility testing
- Major version updates (X.y.z) only when required for security

### ✅ Documentation Improvements
- Clarify existing API documentation
- Add usage examples
- Fix broken links
- Improve README and guides

### ✅ Performance Optimizations (Non-Breaking)
- Query optimization
- Caching improvements
- Memory usage reduction
- Latency reduction
- Throughput improvement

**Requirement**: All optimizations must pass full regression test suite (398 tests) and maintain API compatibility.

---

## Prohibited Activities

### ❌ New Modules
- No new agent types
- No new data sources
- No new analysis engines
- No new dashboard features

### ❌ Architecture Redesign
- No database schema changes (except additive migrations for bug fixes)
- No API contract changes
- No authentication/authorization model changes
- No message queue/transport changes

### ❌ Feature Development
- No new report types
- No new pattern detectors
- No new alert conditions
- No new risk metrics
- No new forecasting models
- No new visualization components

### ❌ Breaking Changes
- No API endpoint modifications
- No response schema changes
- No configuration structure changes
- No authentication flow changes
- No database column removals or type changes

---

## Change Control Process

### For Permitted Changes

1. **Create Issue**: Document the bug/security issue/dependency update
2. **Branch**: Create feature branch from `main`
3. **Implement**: Make minimal change
4. **Test**: Run full test suite (`pytest tests/ -q`)
5. **Verify**: All 398 tests pass, coverage ≥90%
6. **Review**: Self-review or pair review
7. **Merge**: Squash merge to `main`
8. **Tag**: Increment patch version (v2.0.1, v2.0.2, etc.)
9. **Deploy**: Update Docker images

### Emergency Security Patches

1. Hotfix branch from `main`
2. Minimal fix only
3. Run affected tests + security tests
4. Fast-track merge
5. Immediate tag and deploy

---

## Versioning Scheme

```
v2.0.0-stable (current)
  │
  ├── v2.0.1 - Bug fixes only
  ├── v2.0.2 - Security patches
  ├── v2.0.3 - Dependency updates
  └── ...
```

**No minor or major version bumps** without explicit architecture review board approval.

---

## Support Timeline

| Phase | Duration | Support Level |
|-------|----------|---------------|
| Active Maintenance | 2026-07-18 to 2027-07-18 | Full bug/security support |
| Extended Maintenance | 2027-07-18 to 2028-07-18 | Security patches only |
| End of Life | 2028-07-18 | No further updates |

---

## Integration with JARVIS AI CEO

- This repository provides **stable APIs** that JARVIS will consume
- JARVIS team may fork for internal customizations
- Upstream fixes will be cherry-picked to JARVIS fork as needed
- No backward-incompatible changes will be introduced upstream

---

## Contacts

- **Maintainer**: Release Manager (this project)
- **Integration**: JARVIS AI CEO Architecture Team
- **Security**: security@jarvis-ai.com

---

**Policy Frozen**: 2026-07-18  
**Next Review**: 2027-01-18