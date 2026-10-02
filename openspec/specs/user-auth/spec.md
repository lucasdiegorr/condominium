# User Auth Specification

## Purpose

Authenticates users with two-stage JWT (identity token → condominium-scoped token), ensuring that the login screen is the only public route and that all data access is restricted to the user's condominium.

## Requirements

### Requirement: Login returns only an identity token

The system SHALL authenticate an active user by e-mail and password and SHALL return only an identity JWT, without listing condominiums, roles or any user-related data in the login response.

#### Scenario: Successful login
- **WHEN** an active user provides valid e-mail and password
- **THEN** the system returns a valid identity token and no other user information

#### Scenario: Invalid credentials
- **WHEN** a user provides an incorrect e-mail or password
- **THEN** the system responds 401 with a generic message, without revealing whether the e-mail exists

#### Scenario: Inactive user
- **WHEN** a deactivated user tries to authenticate
- **THEN** the system responds 401 as if the credentials were invalid

### Requirement: Condominium listing restricted to the association

The system SHALL expose an authenticated endpoint that returns only the condominiums to which the user has an active association.

#### Scenario: Associated user
- **WHEN** a logged-in user requests the condominium list
- **THEN** the response contains only the condominiums where the user has an active association

#### Scenario: User with no association
- **WHEN** a logged-in user with no associations requests the list
- **THEN** the response is an empty list, without mentioning existing condominiums

### Requirement: Condominium selection issues a scoped token

The system SHALL validate the user's association to a condominium and SHALL issue a scoped token containing the condominium identifier and the user's roles in that condominium.

#### Scenario: Valid selection
- **WHEN** an associated user selects a condominium they belong to
- **THEN** the system issues a scoped token with the condominium and the user's roles

#### Scenario: Selection without association
- **WHEN** a user tries to select a condominium they are not associated with
- **THEN** the system responds 403 without indicating whether the condominium exists

### Requirement: Route protection

The system SHALL require a scoped token for all data routes; the login is the only public route.

#### Scenario: Access without token
- **WHEN** a data route is accessed without any token
- **THEN** the system responds 401

#### Scenario: Identity token on a data route
- **WHEN** a user presents only the identity token on a data route
- **THEN** the system responds 401 or 403, requiring condominium selection

### Requirement: Expiration and renewal of scoped tokens

The system SHALL issue scoped tokens with a short expiration and SHALL revalidate the user's association when renewing access.

#### Scenario: Expired scoped token
- **WHEN** an expired scoped token is presented
- **THEN** the system responds 401 and requires a new selection or scope renewal

#### Scenario: Association revoked after issuance
- **WHEN** a user whose association was revoked tries to renew the scoped token
- **THEN** the system denies the renewal and responds 401 or 403
