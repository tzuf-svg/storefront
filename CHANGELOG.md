# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Project governance files (CONTRIBUTING, SECURITY, CODEOWNERS, CHANGELOG).
- Pre-commit hooks (ruff + detect-secrets).
- Multi-stage hardened Dockerfile and `.dockerignore`.
- Coverage configuration with `fail_under = 70`.

### Changed
- Django settings: removed hardcoded SECRET_KEY fallback, made DEBUG and ALLOWED_HOSTS env-driven, added production SECURE_* settings.
