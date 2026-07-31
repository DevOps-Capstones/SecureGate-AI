# GitLeaks Manual Validation

GitLeaks detects hardcoded secrets in source code and Git history.

Sprint 1 validates GitLeaks manually only. It is not connected to the FastAPI backend or any CI/CD pipeline yet.

## Installation

macOS with Homebrew:

```bash
brew install gitleaks
```

Linux:

```bash
wget https://github.com/gitleaks/gitleaks/releases/latest/download/gitleaks_8.18.4_linux_x64.tar.gz
tar -xzf gitleaks_8.18.4_linux_x64.tar.gz
sudo mv gitleaks /usr/local/bin/
```

Docker:

```bash
docker run --rm -v "$PWD:/path" zricethezav/gitleaks:latest detect --source /path
```

## Example Command

Run from the repository root:

```bash
gitleaks detect .
```

Alternative explicit source command:

```bash
gitleaks detect --source .
```

## Expected Output Examples

No leaks found:

```text
INF scan completed in 1.2s
INF no leaks found
```

Leaks found:

```text
Finding:     aws_access_key_id = AKIA...
Secret:      AKIA...
RuleID:      aws-access-token
File:        example.env
Line:        4
```

## Sprint 1 Validation Checklist

- GitLeaks is installed.
- `gitleaks detect .` runs successfully.
- Output is captured as a screenshot or terminal copy for documentation.
- Any discovered secrets are treated as validation data only during Sprint 1.
