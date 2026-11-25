# FinCo Software Development and Change Management Policy

*This is a fictional policy written for testing PolicyLens. FinCo does not exist.*

## 1. Purpose and Scope

This policy sets out how FinCo builds, changes and releases software that supports its mobile wallet and payment services. It applies to all employees, contractors and vendors who write or deploy code for FinCo systems, including web applications, mobile apps and internal tools.

## 2. Roles and Responsibilities

The Head of Engineering owns this policy. Team leads make sure their teams follow it. The Information Security team reviews the policy once a year and advises on exceptions. Every developer is responsible for writing code that follows the secure coding guidelines in section 3.

## 3. Secure Software Development

FinCo maintains secure coding guidelines based on industry practice, covering input validation, authentication, session handling, error handling and cryptography. All developers must complete secure coding training when they join and once every year afterwards. Training covers the common ways software is attacked and how to avoid introducing those weaknesses.

Every code change must be reviewed by at least one other developer before it is merged. Reviewers check the change against the secure coding guidelines. Changes to authentication or payment logic also need a review from a member of the Information Security team.

Source code is scanned automatically for security weaknesses in the build pipeline. A build with a high severity finding cannot be released until the finding is fixed or formally accepted by Information Security.

## 4. Environments and Test Data

Development, testing and production environments are kept separate, and developers do not have routine access to production. Live customer data and real payment card numbers must never be used in development or testing. Test data is created artificially or fully masked.

## 5. Change Management

All changes to production systems need a change request that describes the change, the reason for it, and the systems affected. Each request is approved by the team lead and, for high-risk changes, by the Change Advisory Board before it is deployed.

Every change must have a tested rollback plan. Changes are tested in a staging environment before release. Emergency changes may be approved verbally but must be documented within two working days.

## 6. Vulnerability Management

FinCo will fix security vulnerabilities in a timely manner.

## 7. Third-Party and Open-Source Components

Teams should be aware of the libraries and components they use and should keep them reasonably up to date.

## 8. Web Applications

Web applications should be secure.

## 9. Exceptions

Exceptions to this policy must be requested in writing, justified, and approved by Information Security. Approved exceptions are recorded and reviewed at least once a year.
