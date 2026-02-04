# FlexDash Asset Taxonomy

## Overview

This document defines the standardised classification of flexible assets used in the ADE Flexibility Dashboard.

## Sector Classification

### Domestic

Assets located at residential properties, typically < 100 kW individual capacity.

### Industrial & Commercial (I&C)

Assets at non-domestic premises, typically > 100 kW capacity.

## Asset Classes

### Domestic Assets

| Asset Class | Code | Description | Typical Capacity |
|-------------|------|-------------|------------------|
| Electric Vehicle Charger | EV | Smart EV charging points at homes | 3.6 - 22 kW |
| Heat Pump | HP | Air source or ground source heat pumps | 3 - 12 kW |
| Battery Storage | BESS | Behind-the-meter battery systems | 3 - 13.5 kW |
| Smart Hot Water | HW | Immersion heaters and thermal stores | 2 - 3 kW |
| Wet Appliances | WET | Smart washing machines, dishwashers | 0.5 - 2 kW |

### I&C Assets

| Asset Class | Code | Description | Typical Capacity |
|-------------|------|-------------|------------------|
| Cold Storage | COLD | Refrigeration and cold chain facilities | 50 kW - 2 MW |
| Water Treatment | WATER | Water and wastewater treatment plants | 100 kW - 5 MW |
| Manufacturing | MFG | Industrial process loads | 100 kW - 10 MW |
| Commercial HVAC | HVAC | Commercial heating/cooling systems | 20 kW - 2 MW |
| Commercial Battery | C-BESS | Commercial and industrial batteries | 50 kW - 5 MW |
| Backup Generation | GEN | Diesel/gas backup generators | 100 kW - 5 MW |
| EV Fleet | FLEET | Commercial EV charging depots | 50 kW - 2 MW |

## Flexibility Mechanisms

| Mechanism | Description |
|-----------|-------------|
| Demand Shift | Moving consumption to different time period |
| Demand Reduction | Reducing consumption below baseline |
| Storage | Storing energy for later use |
| Generation | Providing power from on-site generation |

## Service Types

### Frequency Response

| Service | Operator | Description |
|---------|----------|-------------|
| Dynamic Containment | NESO | Sub-second frequency response |
| Dynamic Moderation | NESO | Frequency response (slower) |
| Dynamic Regulation | NESO | Continuous frequency tracking |
| FFR | NESO | Firm Frequency Response |

### Capacity Market

| Service | Description |
|---------|-------------|
| T-1 | One year ahead capacity auction |
| T-4 | Four years ahead capacity auction |

### Balancing Mechanism

| Service | Description |
|---------|-------------|
| BOA | Bid-Offer Acceptances |

### DSO Flexibility

| Service | Description |
|---------|-------------|
| Sustain | Ongoing constraint management |
| Secure | Pre-fault constraint management |
| Dynamic | Real-time network services |

### Time-of-Use Tariffs

| Product (generic) | Description |
|------------------|-------------|
| Dynamic pricing | Half-hourly variable pricing |
| Off-peak EV | Off-peak EV charging |
| Heat pump optimised | Heat pump optimised |
| Smart charging | Smart charging integration |

## Field Mappings

When ingesting data, the following terms are mapped to the standard taxonomy:

```yaml
# EV variations
"Electric Vehicle" -> ev_charger
"EV" -> ev_charger
"EV Charger" -> ev_charger
"Smart Charger" -> ev_charger

# Heat pump variations
"Heat Pump" -> heat_pump
"HP" -> heat_pump
"ASHP" -> heat_pump
"GSHP" -> heat_pump
"Air Source Heat Pump" -> heat_pump

# Battery variations
"Battery" -> battery_storage
"BESS" -> battery_storage
"Home Battery" -> battery_storage

# I&C variations
"Cold Store" -> cold_storage
"Refrigeration" -> cold_storage
"Water Treatment" -> water_treatment
"WTW" -> water_treatment
```

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.1 | 2026-02-04 | Remove supplier attribution from ToU examples; normalise arrow glyphs |
| 1.0 | 2025-01-27 | Initial taxonomy |
