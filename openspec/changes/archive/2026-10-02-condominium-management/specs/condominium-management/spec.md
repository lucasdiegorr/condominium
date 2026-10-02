## Purpose

Registers and maintains condominiums and user associations, guaranteeing that all domain data is always handled within the condominium scope.

## ADDED Requirements

### Requirement: Condominium CRUD by the administrator

The system SHALL allow the global administrator to create, edit and deactivate condominiums, providing at least name and address.

#### Scenario: Condominium creation
- **WHEN** the administrator creates a condominium with valid data
- **THEN** the condominium becomes available for management, user association and scoped data

#### Scenario: Condominium deactivation
- **WHEN** the administrator deactivates a condominium
- **THEN** the condominium stops appearing in listings and new actions are blocked, preserving its existing data

#### Scenario: Non-administrator cannot create condominiums
- **WHEN** a user without an administrator role tries to create a condominium
- **THEN** the system responds 403

### Requirement: User–condominium association

The system SHALL maintain many-to-many associations between users and condominiums, which are the basis for listing and access scoping.

#### Scenario: Association created
- **WHEN** the administrator associates a user with a condominium
- **THEN** the condominium starts to appear in that user's listing

#### Scenario: Association removed
- **WHEN** a user's association with a condominium is removed
- **THEN** the user stops accessing the condominium and seeing its scoped data

### Requirement: Data scoped to the condominium

The system SHALL keep all domain data (units, residents, vehicles, pets, common areas, bookings, financial) associated with a condominium and SHALL always handle it within that condominium context.

#### Scenario: Cross-query blocked
- **WHEN** a user tries to access data from a condominium outside their token's scope
- **THEN** the system responds 403 without exposing data from the other condominium

#### Scenario: Creation associated with the scope's condominium
- **WHEN** a user creates a domain record (e.g., unit, resident, entry)
- **THEN** the record is automatically associated with the condominium of the scoped token
