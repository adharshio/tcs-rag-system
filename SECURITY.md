# Security Policy

The **Campus Placement Assistant** team takes the security and privacy of student data and system integrity seriously. This document outlines our vulnerability disclosure policy and reporting process.

For internal team architecture guidelines, prompt injection defenses, and pre-release checklists, see [docs/INTERNAL_SECURITY.md](docs/INTERNAL_SECURITY.md).

---

## Supported Versions

Only the current active release and the `main` branch are actively monitored and supported with security updates.

| Version | Supported          |
| ------- | ------------------ |
| `main`  | :white_check_mark: |
| `< 1.0` | :x:                |

---

## Reporting a Vulnerability

If you discover a security vulnerability, **please do not open a public GitHub issue or discuss it in public channels.**

### Preferred Method
Submit a confidential report via GitHub's [Private Vulnerability Reporting](https://github.com/adharshio/tcs-rag-system/security/advisories/new) feature:
1. Navigate to the repository's **Security** tab.
2. Select **Advisories**.
3. Click **Report a vulnerability**.

### Alternative Method
If you are unable to use GitHub Security Advisories, contact the security maintainers directly:

* **Adharsh** – [adharshkandath@gmail.com](mailto:adharshkandath@gmail.com)
* **Aswin Manoj** – [aswinmanojtj@gmail.com](mailto:aswinmanojtj@gmail.com)

---

## What to Include in Your Report

To help us triage and resolve the issue quickly, please include:

- **Summary:** A concise description of the vulnerability.
- **Affected Component:** The service or endpoint affected (e.g., Document Pipeline, RAG retrieval engine, Backend API, Frontend).
- **Steps to Reproduce:** Clear, step-by-step instructions, including any sample requests, payloads, or screenshots.
- **Impact Assessment:** The potential consequence of the vulnerability (e.g., unauthorized data access, prompt injection bypass, denial of service).
- **Proof of Concept (PoC):** Non-destructive code or test cases demonstrating the vulnerability.

---

## Response Timeline & SLA

We follow coordinated vulnerability disclosure and will do our best to meet the following response targets:

| Stage | Target Timeline |
|---|---|
| **Initial Acknowledgement** | Within **24 hours** |
| **Triage & Severity Assessment** | Within **48 hours** |
| **Status Updates** | Every **3 to 5 business days** until resolution |
| **Fix Deployment** | Prioritized according to severity (critical issues targeted within 48–72 hours) |

---

## Responsible Disclosure & Safe Harbor

We ask that you:
- Give us reasonable time to investigate and resolve an issue before making any details public.
- Make a good-faith effort not to disrupt availability or access data that does not belong to you (especially student records and personal data).
- Avoid exploiting the vulnerability beyond what is strictly necessary to confirm its existence.

If you conduct security research within these guidelines, we will not pursue legal action against you.
# Security Policy

This document covers two things: how to report a vulnerability in the Campus Placement Assistant, and the security rules every team must follow while building it.

## 1. Reporting a vulnerability

If you find a security issue, **do not open a public issue or post it in the team chat.**

- Use GitHub's **Report a vulnerability** button (Security tab > Advisories), or
- Contact the security owners directly: `adharsh` (`adharshkandath@gmail.com`) or `<ayush>` (`ayyushrk`)

Please include:
- What you found and where (endpoint, file, or page)
- Steps to reproduce
- The impact (what data or function is at risk)

We will acknowledge reports within **24 hours** and aim to fix critical issues within **48 hours**.

## 2. Scope

| Component | Owner | Security focus |
|---|---|---|
| Document pipeline (Team 1) | Team 1 | No personal data in indexed documents |
| RAG engine (Team 2) | Team 2 | Prompt injection, grounded answers |
| Backend API (Team 3) | Team 3 | Authentication, authorization, validation |
| Frontend (Team 4) | Team 4 | No secrets in client code, safe rendering |
| Testing, security, deployment (Team 5) | Team 5 | Verification, CI/CD, hosting, monitoring |

## 3. Rules for all contributors

1. **Never commit secrets.** No API keys, tokens, passwords, or `.env` files. Use `.env.example` with fake values.
2. **Never commit student data.** No real names, roll numbers, CGPAs, emails, or phone numbers in code, test data, logs, or documents. Use synthetic data for development and demos.
3. **All changes go through pull requests.** No direct pushes to `main`. CI must pass before merging.
4. **Share secrets only through the approved channel** (password manager or the hosting platform's secret store), never in group chats or screenshots.
5. **If you leak a secret, tell the security owners immediately** and rotate the key. Deleting the commit is not enough.
6. **Enable two-factor authentication** on your GitHub account.

## 4. Team-specific requirements

### Team 1: Data pipeline
- Remove personal data (student names, IDs, contact details) from documents before chunking and indexing.
- Only ingest documents from approved sources. Check files for hidden or embedded instructions (text intended to manipulate the AI).
- Keep metadata limited to what is needed (document, category, company, year).

### Team 2: RAG engine
- Treat retrieved document text as **data, not instructions**. Wrap it in clear delimiters in the prompt.
- The system prompt must state that the assistant only answers from provided context and refuses when the answer is not present.
- The LLM must have **no tools** beyond retrieval: no database writes, no file access, no web access.
- Student-specific facts (for example, CGPA or backlogs) come from the authenticated profile as structured fields, not from free text in the question.
- Log retrieved chunk IDs and scores for debugging, but not full prompts containing student data.
- Set a spending limit on the LLM provider account.

### Team 3: Backend and API
- Every endpoint requires authentication **except** `/api/health`.
- Enforce authorization: a user can only access their own sessions and chat history. Never trust user IDs sent by the client.
- Validate all input with schemas (Pydantic). Set maximum lengths, for example 500 characters for a chat question.
- Rate limit `/api/chat` and authentication endpoints.
- Restrict CORS to the exact frontend domain. Never use `*` in production.
- Hash passwords with bcrypt or argon2. Sign JWTs with a strong secret from the environment and give them an expiry.
- Return generic error messages to clients. Never expose stack traces. Log details server-side.
- Use parameterized queries or the ORM. Never build SQL from user input.
- Disable API docs (`/docs`, `/redoc`) in production.

### Team 4: Frontend
- Anything in `NEXT_PUBLIC_*` variables is visible to everyone. Never put secrets there.
- Do not render model output as raw HTML. Escape it or use a safe markdown renderer.
- Do not store tokens in `localStorage` if an httpOnly cookie is possible.
- Do not display more student data than the screen needs.
- Set security headers (CSP, `X-Content-Type-Options`, `X-Frame-Options`) in the Next.js config.

### Team 5: Testing, security, deployment
- Maintain CI checks: tests, `pip-audit`, `npm audit`, secret scanning, and CodeQL.
- Keep separate `staging` and `production` environments with separate secrets.
- Run the security test suite (authentication, authorization, injection, rate limit, input validation) against staging before every release.
- Maintain `DEPLOY.md` covering deployment, rollback, and key rotation.
- Monitor `/api/health` and keep a tested offline fallback for the demo.

## 5. Data handling

| Data | Allowed in | Not allowed in |
|---|---|---|
| Public placement policies, FAQs, calendars | Repo, vector DB, prompts | none |
| Student profile data (CGPA, backlogs) | Application database, structured prompt fields for that student only | Vector DB, logs, repo, other users' responses |
| Credentials and tokens | Platform secret stores | Repo, chat, logs, frontend code |
| Chat history | Application database, visible only to the owning user | Logs (unredacted), other users' views |

Retention: delete demo and test data after the event.

## 6. Prompt injection defense

Because this system answers using retrieved documents, both user questions and documents can carry attack text.

- Assume any question or document may contain instructions such as "ignore previous instructions."
- Keep system instructions separate from retrieved text and user text.
- Filter outputs for patterns such as roll numbers, emails, and phone numbers before returning them.
- Test regularly with an adversarial question set, including injection text planted inside a test document.
- When the answer is not in the retrieved context, the assistant must say so rather than guess.

## 7. Dependency and code hygiene

- Dependabot is enabled for Python, npm, and GitHub Actions.
- Pin dependency versions in `requirements.txt` and lock files.
- Review new dependencies before adding them. Prefer well-known, maintained packages.
- CodeQL scans run on every pull request and weekly.

## 8. Deployment security

- HTTPS only. Redirect HTTP to HTTPS.
- Production secrets live only in the hosting platform's environment settings, restricted to the `production` environment.
- The backend container runs as a non-root user.
- Production deploys come only from `main` after CI passes.
- Debug mode is off in production.

## 9. Incident response

If you suspect a breach or leak:

1. **Contain:** rotate exposed keys, disable affected accounts or endpoints.
2. **Notify:** inform the security owners immediately.
3. **Investigate:** check logs to find what was accessed and when.
4. **Fix:** patch the cause, deploy, and re-run the security tests.
5. **Record:** write a short note covering what happened, the impact, and the fix.

## 10. Pre-release checklist

- [ ] No secrets in the repo or git history (gitleaks clean)
- [ ] All endpoints except `/api/health` require authentication
- [ ] Cross-user access test passes (student A cannot read student B's data)
- [ ] Rate limiting confirmed on `/api/chat`
- [ ] Input validation tested (empty, oversized, special characters)
- [ ] Prompt injection test set run, no data leaked
- [ ] Out-of-domain and missing-information questions are refused, not invented
- [ ] CORS limited to the frontend domain
- [ ] Debug mode and API docs off in production
- [ ] Dependency audits show no high-severity issues
- [ ] Uptime monitor active and fallback demo ready

## 11. Contacts
| Security and deployment lead | `adharsh` | `adharshkandath@gmail.com` |
| Testing and evaluation lead | `aswin manoj` | `aswinmanojtj@gmail.com` |
