# Access Control Specification

## Purpose

Defines per-condominium roles (functions and unit links), the permission matrix of each role and role management by the global administrator, conditioning access to screens and data on the role exercised in the condominium.

## Requirements

### Requirement: Roles assigned per condominium

The system SHALL assign roles to a user within the scope of a specific condominium, and SHALL allow the same user to hold different sets of roles in different condominiums.

#### Scenario: Multiple roles in the same condominium
- **WHEN** the administrator assigns user X both "condômino" and "síndico" roles in condominium Y
- **THEN** user X exercises both roles in that condominium, with combined permissions

#### Scenario: Distinct roles across condominiums
- **WHEN** user X holds roles in condominium Y and in condominium Z
- **THEN** the roles of each condominium are independent and never mix

### Requirement: Differentiated role types

The system SHALL distinguish condominium-level function roles (síndico, conselho) from unit-level link roles (condômino, inquilino), and SHALL require the linked unit when the role is a unit link.

#### Scenario: Function role without a unit
- **WHEN** the administrator registers a síndico or a conselho member
- **THEN** the system does not require a linked unit

#### Scenario: Unit link requires a unit
- **WHEN** the administrator registers a condômino or inquilino
- **THEN** the system requires the condominium unit to be linked

### Requirement: Permission matrix per role

The system SHALL apply the following permissions per role:
- Global administrator: all actions in all condominiums;
- Síndico: day-to-day operation of the condominium (units, residents, vehicles/pets, bookings, financial);
- Conselho: read-only consultation in the condominium (balance sheet, bookings, residents), without operations;
- Condômino/Inquilino: self-service restricted to their own universe (own bookings, own vehicles/pets, financial consultation of their own unit).

#### Scenario: Síndico operates the condominium
- **WHEN** a síndico accesses the condominium where they exercise the role
- **THEN** they can create and edit units, residents, vehicles/pets, bookings and financial entries of the condominium

#### Scenario: Conselho reads only
- **WHEN** a conselho member accesses the condominium
- **THEN** they consult the balance sheet, bookings and residents, without executing operations

#### Scenario: Resident restricted to their own universe
- **WHEN** a condômino or inquilino accesses the condominium
- **THEN** they only book, register their own vehicles/pets and consult financial data related to their own unit

#### Scenario: Action beyond the role denied
- **WHEN** a user tries an action beyond their role, such as a condômino recording a condominium expense
- **THEN** the system responds 403

### Requirement: Administrator with global access

The system SHALL allow the global administrator to perform any action and SHALL let the administrator operate within any condominium.

#### Scenario: Maintenance in a condominium
- **WHEN** an administrator accesses a condominium
- **THEN** they receive the full permissions of that condominium, including role management

#### Scenario: Administrator records an expense in a condominium
- **WHEN** an administrator records an expense in a condominium they are operating in
- **THEN** the entry is accepted as if the administrator were the síndico

### Requirement: Role management by the administrator

The system SHALL expose an administrator screen for registering and maintaining roles, binding a user to roles within a condominium and selecting the unit when the role is a unit link.

#### Scenario: Role registration
- **WHEN** the administrator creates a role assignment for a user in a condominium
- **THEN** the assignment takes effect on the user's subsequent accesses to that condominium

#### Scenario: Síndico cannot change functions
- **WHEN** a síndico tries to change function roles (síndico, conselho) in the condominium
- **THEN** the system responds 403
