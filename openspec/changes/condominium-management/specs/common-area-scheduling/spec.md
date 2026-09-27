## Purpose

Registers the condominium's common areas and supports simple booking with time-conflict checking and status, without payment or an approval flow in this version.

## ADDED Requirements

### Requirement: Common area registration

The system SHALL allow the síndico and the global administrator to register the condominium's common areas, with name, description and capacity when applicable.

#### Scenario: Common area creation
- **WHEN** the síndico registers a valid common area in the condominium
- **THEN** the area becomes available for booking in that condominium

### Requirement: Booking without time conflict

The system SHALL allow common-area bookings with start and end times and SHALL prevent overlapping time slots in the same area.

#### Scenario: Valid booking
- **WHEN** a resident books an area in a free time slot
- **THEN** the booking is created with reserved status

#### Scenario: Overlap rejected
- **WHEN** someone tries to book a time slot that overlaps an existing booking in the same area
- **THEN** the system rejects it and does not create the reservation

#### Scenario: End before start
- **WHEN** someone tries to create a booking whose end is before its start
- **THEN** the system rejects it with a validation error

### Requirement: Booking status

The system SHALL keep the booking status (reserved or cancelled) and SHALL allow cancellation of reserved bookings.

#### Scenario: Cancellation
- **WHEN** the responsible party, the síndico or the administrator cancels a reserved booking
- **THEN** the status becomes cancelled and the time slot becomes free again

### Requirement: Booking scope

The system SHALL allow condômino/inquilino to book only for themselves (their unit/person) and SHALL allow síndico/administrator to book or cancel any booking of the condominium.

#### Scenario: Resident books for themselves
- **WHEN** a resident books an area
- **THEN** the booking is linked to the resident's person/unit

#### Scenario: Resident does not book on behalf of others
- **WHEN** a resident tries to book on behalf of another unit or cancel someone else's booking
- **THEN** the system responds 403
