# Unit Management Specification

## Purpose

Registers condominium units with their ideal fraction and the parking spots tied to each unit, providing the basis for financial allocation.

## Requirements

### Requirement: Unit CRUD per condominium

The system SHALL allow the síndico to create, edit and remove units of their condominium (number, tower/block when applicable, ideal fraction and type), and SHALL allow the global administrator to do so in any condominium.

#### Scenario: Unit creation
- **WHEN** the síndico registers a valid unit in their condominium
- **THEN** the unit becomes part of the condominium

#### Scenario: Unit out of scope
- **WHEN** a user tries to create or edit a unit of a condominium outside the token's scope
- **THEN** the system responds 403

### Requirement: Validated ideal fraction

The system SHALL record the ideal fraction of each unit as a positive value and SHALL prevent the sum of unit fractions from exceeding the condominium total (100%).

#### Scenario: Fraction sum exceeds the total
- **WHEN** registering a unit would push the sum of fractions above 100%
- **THEN** the system rejects it with a validation error

#### Scenario: Negative fraction
- **WHEN** someone tries to register a unit with a negative or zero ideal fraction
- **THEN** the system rejects it with a validation error

### Requirement: Parking spots tied to units

The system SHALL register parking spots (identifier and type, such as covered/uncovered) linked to a unit of the same condominium.

#### Scenario: Spot for a unit
- **WHEN** the síndico registers a spot and links it to a unit of the condominium
- **THEN** the spot becomes part of the unit, within the condominium scope

#### Scenario: Spot linked to a unit of another condominium
- **WHEN** someone tries to link a spot to a unit of another condominium
- **THEN** the system responds 403 or a validation error
