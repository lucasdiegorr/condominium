## Purpose

Registers physical persons and user accounts as distinct concepts, and records the unit links (condômino/inquilino) that make up each condominium's residents roster.

## ADDED Requirements

### Requirement: Person distinct from user

The system SHALL keep the physical person record (name, CPF, contact) independent of the existence of a user account, and SHALL allow a person to exist without a login.

#### Scenario: Resident without login
- **WHEN** the síndico registers a resident who will not have access to the system
- **THEN** the person is registered without a user account

#### Scenario: Account created for a person
- **WHEN** a user account is created linked to a person
- **THEN** the account enables authentication for the person, without altering the person record

### Requirement: Unique CPF and e-mail

The system SHALL enforce unique CPF among persons and unique e-mail among user accounts.

#### Scenario: Duplicate CPF
- **WHEN** a person is registered with an existing CPF
- **THEN** the system rejects the registration with a duplicate error

#### Scenario: Duplicate e-mail
- **WHEN** a user account is created with an e-mail already in use
- **THEN** the system rejects the creation with a duplicate error

### Requirement: Multiple unit links per person

The system SHALL allow a person to hold multiple unit links: several units in the same condominium, or units in different condominiums, as condômino and/or inquilino.

#### Scenario: Owner of two units
- **WHEN** a person owns two units in the same condominium
- **THEN** the system records two condômino links, one per unit

#### Scenario: Links in different condominiums
- **WHEN** a person owns units in different condominiums
- **THEN** the links are kept per condominium, without interference between them

### Requirement: Multiple links per unit

The system SHALL allow a unit to hold multiple condôminos (for example, a couple) and a single inquilino simultaneously.

#### Scenario: Couple as condôminos and an inquilino in the same unit
- **WHEN** a unit has João and Maria as condôminos and Pedro as inquilino
- **THEN** the three links coexist tied to the same unit

### Requirement: Resident registration by the síndico

The system SHALL allow the síndico to register residents (condômino/inquilino unit links) of their condominium, and SHALL allow the global administrator to do so in any condominium.

#### Scenario: Síndico registers a resident
- **WHEN** a síndico registers a resident in their condominium
- **THEN** the unit link is created within the condominium scope

#### Scenario: Síndico out of scope
- **WHEN** a síndico tries to register or edit a resident in another condominium
- **THEN** the system responds 403
