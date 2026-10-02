# Vehicles and Pets Specification

## Purpose

Registers vehicles tied to a responsible resident and a unit (owner and tenant can use the spot) and pets tied to the resident, with resident self-service.

## Requirements

### Requirement: Vehicle registered with resident and unit

The system SHALL register vehicles (plate, model and vehicle details) linked to a responsible resident — a person with a link in the condominium — and to a unit of the same condominium.

#### Scenario: Tenant's vehicle
- **WHEN** a tenant registers a vehicle to use the rented unit's spot
- **THEN** the vehicle is registered linked to the tenant and the unit

#### Scenario: Non-resident owner's vehicle
- **WHEN** a non-resident owner registers a vehicle in their unit's spot
- **THEN** the vehicle is registered linked to the owner and the unit

### Requirement: Vehicle self-service

The system SHALL allow condômino/inquilino to register and edit only their own vehicles, SHALL allow the síndico to register and edit any vehicle of the condominium, and SHALL allow the global administrator to do so in any condominium.

#### Scenario: Resident registers their own vehicle
- **WHEN** a resident registers one of their own vehicles
- **THEN** the vehicle is created linked to the resident's unit

#### Scenario: Resident edits another person's vehicle
- **WHEN** a resident tries to edit or remove a vehicle belonging to someone else
- **THEN** the system responds 403

### Requirement: Unique plate per condominium

The system SHALL prevent registering the same plate in two units of the same condominium.

#### Scenario: Duplicate plate in the condominium
- **WHEN** someone tries to register a plate that already exists in the same condominium
- **THEN** the system rejects it with a duplicate error

### Requirement: Pets linked to the resident

The system SHALL register pets (name, species and breed) linked to a resident — a person with a link in the condominium —, allowing self-service by the resident and management by the síndico and the global administrator.

#### Scenario: Resident registers their own pet
- **WHEN** a resident registers one of their own pets
- **THEN** the pet is created linked to the resident

#### Scenario: Síndico registers a resident's pet
- **WHEN** the síndico registers a pet for a resident of the condominium
- **THEN** the pet is created linked to the informed resident, within the condominium scope
