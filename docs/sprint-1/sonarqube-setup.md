# SonarQube Setup

## Access URL

After starting Docker Compose, open:

```text
http://localhost:9000
```

SonarQube may take a few minutes to initialize.

## Default Credentials

- Username: `admin`
- Password: `admin`

You may be prompted to change the default password on first login.

## Create a Project

1. Log in to SonarQube.
2. Select `Create Project`.
3. Choose `Manually`.
4. Enter a project display name, for example `SecureGate AI`.
5. Enter a project key, for example `securegate-ai`.
6. Select `Set Up`.

## Generate a Token

1. Open the user menu in the top-right corner.
2. Select `My Account`.
3. Open the `Security` tab.
4. Enter a token name, for example `securegate-local-token`.
5. Select `Generate`.
6. Copy the token and store it securely.

## Sprint 1 Notes

SonarQube is deployed and validated manually in Sprint 1. Automated scanner execution and backend integration are planned for later sprints.
