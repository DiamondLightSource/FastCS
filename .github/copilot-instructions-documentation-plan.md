# FastCS Documentation Plan

## Overview

This document outlines a comprehensive plan to create high-quality documentation for the FastCS project using the [Diataxis](https://diataxis.fr) framework. The documentation will enable both humans and AI assistants to effectively use FastCS to create control system drivers for scientific instruments.

## Diataxis Framework

FastCS documentation follows the Diataxis framework, which organizes documentation into four categories:

1. **Tutorials** - Learning-oriented, step-by-step lessons for beginners
2. **How-To Guides** - Task-oriented, practical guides for specific goals
3. **Explanations** - Understanding-oriented, background and design rationale
4. **Reference** - Information-oriented, technical descriptions and APIs

## Current State

### Existing Documentation
- **Tutorials**: Installation, static drivers (comprehensive), dynamic drivers
- **How-To Guides**: Contributing guide only
- **Explanations**: Architecture decisions (ADRs)
- **Reference**: Auto-generated API documentation

### Gaps Identified
1. **How-To Guides**: Limited practical guides for common tasks
2. **Explanations**: Minimal architectural and design documentation
3. **Tutorials**: Missing guides for advanced topics
4. **Examples**: No real-world device driver examples beyond the demo

## Documentation Plan

### Stage 1: Essential How-To Guide ✅ COMPLETE

#### Document: `docs/how-to/create-epics-ioc-with-ca-and-pva.md` ✅

**Status**: Implemented and available - see [docs/how-to/create-epics-ioc-with-ca-and-pva.md](../docs/how-to/create-epics-ioc-with-ca-and-pva.md)

**Purpose**: Enable developers to create a production-ready EPICS IOC using FastCS with both Channel Access (CA) and PV Access (PVA) transports.

**Target Audience**:
- Developers migrating from traditional EPICS IOC implementations
- New FastCS users with EPICS background
- AI assistants helping users create device drivers

**Key Topics Covered**:
- Project setup and installation
- Controller and attribute definition
- Device communication implementation
- Setting up both CA and PVA transports
- Testing and verification
- Converting existing EPICS IOCs to FastCS
- Complete working examples
- Troubleshooting and best practices

**Success Criteria**:
- A developer can create a basic dual-transport IOC in under 30 minutes
- The guide enables successful migration of an existing EPICS IOC
- An AI assistant can use this guide to help implement a new device driver

---

### Stage 2: Additional How-To Guides

Priority order based on user needs:

1. **`how-to/implement-device-connection.md`**
   - Creating custom connection classes
   - TCP/IP, Serial, USB communication
   - Connection pooling and management
   - Error handling and reconnection logic

2. **`how-to/structure-complex-controllers.md`**
   - Using sub-controllers for device hierarchy
   - ControllerVector for arrays of similar devices
   - Sharing AttributeIO between controllers
   - Organizing large device drivers

3. **`how-to/implement-commands-and-methods.md`**
   - Using @command decorator
   - Using @scan decorator for periodic tasks
   - Implementing complex multi-step procedures
   - Progress reporting and cancellation

4. **`how-to/handle-errors-and-validation.md`**
   - Input validation patterns
   - Error propagation to EPICS layer
   - Device fault handling
   - Logging best practices

5. **`how-to/optimize-performance.md`**
   - Choosing appropriate update periods
   - Batching operations
   - Caching strategies
   - Reducing PV update overhead

6. **`how-to/generate-and-customize-guis.md`**
   - Generating Phoebus screens
   - Customizing widget layouts
   - BOY vs BOB format
   - Adding custom widgets

7. **`how-to/test-fastcs-drivers.md`**
   - Unit testing controllers
   - Integration testing with EPICS
   - Mocking devices for testing
   - Continuous integration setup

8. **`how-to/deploy-fastcs-iocs.md`**
   - Containerization with Docker
   - systemd service configuration
   - Environment management
   - Logging and monitoring

---

### Stage 3: Explanation Documents

Deep-dive technical explanations of architecture and design:

1. **`explanations/architecture.md`**
   - Overall FastCS architecture
   - Controller, Attribute, Transport separation
   - Event loop and async design
   - Why FastCS is control-system agnostic

2. **`explanations/transport-layer.md`**
   - How transports work
   - CA vs PVA implementation details
   - Adding custom transports
   - Protocol mapping strategies

3. **`explanations/attribute-system.md`**
   - Attribute types and their purpose
   - AttributeIO design pattern
   - Update mechanisms
   - Type system and validation

4. **`explanations/epics-integration.md`**
   - How FastCS maps to EPICS records
   - PVI (Process Variable Interface) details
   - Record type selection logic
   - Handling EPICS-specific features

5. **`explanations/comparison-with-traditional-epics.md`**
   - FastCS vs asynDriver
   - FastCS vs StreamDevice
   - When to use FastCS
   - Migration considerations

---

### Stage 4: Advanced Tutorials

Learning-oriented guides for advanced topics:

1. **`tutorials/async-operations.md`**
   - Understanding Python asyncio in FastCS
   - Concurrent device operations
   - Async best practices
   - Debugging async code

2. **`tutorials/custom-datatypes.md`**
   - Creating custom DataType classes
   - Complex structured data (Tables)
   - Numpy array handling
   - Type conversion and validation

3. **`tutorials/multi-transport-ioc.md`**
   - Running EPICS, Tango, and REST simultaneously
   - Protocol-specific considerations
   - Unified device interface
   - Cross-protocol testing

4. **`tutorials/real-world-example-zebra.md`**
   - Complete real-world example: Zebra position compare
   - Hardware abstraction
   - Complex register interface
   - Integration with existing systems

---

### Stage 5: Reference Enhancements

1. **`reference/attribute-types.md`**
   - Complete reference for all Attribute types
   - Parameter descriptions
   - Usage examples
   - Type hints and validation

2. **`reference/datatypes.md`**
   - All DataType classes
   - Conversion rules
   - Limits and validation
   - Protocol-specific representations

3. **`reference/transport-options.md`**
   - Complete configuration options for each transport
   - Default values
   - Environment variables
   - Best practices

4. **`reference/migration-guide.md`**
   - Record type mapping table
   - Common patterns conversion
   - API equivalence table
   - Deprecation warnings

---

## Implementation Timeline

### Phase 1 (Immediate - Week 1)
- ✅ Create this documentation plan
- ✅ Create Stage 1 how-to guide (`docs/how-to/create-epics-ioc-with-ca-and-pva.md`)
- Review and feedback
- Publish initial version

### Phase 2 (Weeks 2-3)
- Implement 3-4 priority how-to guides from Stage 2
- Create 1-2 explanation documents from Stage 3
- User feedback and iteration

### Phase 3 (Weeks 4-6)
- Complete remaining Stage 2 how-to guides
- Complete Stage 3 explanations
- Begin Stage 4 advanced tutorials
- Comprehensive review

### Phase 4 (Weeks 7-8)
- Complete Stage 4 tutorials
- Enhance reference documentation
- Real-world examples
- Final review and polish

### Phase 5 (Ongoing)
- Maintain documentation with code changes
- Add community-requested guides
- Update examples for new features
- Collect and incorporate feedback

---

## Documentation Standards

### Writing Style
- Clear, concise language
- Active voice
- Present tense
- Direct instructions
- Code-first examples

### Code Examples
- Complete, runnable code
- Syntax highlighting
- Comments for complex sections
- Both minimal and realistic examples
- Error handling included

### Structure
- Clear headings hierarchy
- Prerequisites section
- Step-by-step for how-tos
- Summary/recap section
- Links to related documents

### Testing
- All code examples must be tested
- Include in CI/CD pipeline
- Automated link checking
- Version compatibility notes

---

## Success Metrics

### Quantitative
- Time to create first IOC (target: <30 min)
- Documentation coverage (target: >80% of public API)
- Broken link rate (target: 0%)
- Code example pass rate (target: 100%)

### Qualitative
- User feedback surveys
- GitHub issue reduction for documentation questions
- Community contributions to docs
- Successful migrations from traditional EPICS

---

## Maintenance Plan

### Regular Updates
- Review docs with each release
- Update for deprecated features
- Add new feature documentation
- Refresh examples

### Community Involvement
- Accept documentation PRs
- Create "good first issue" doc tasks
- Encourage user examples
- Maintain contribution guide

### Quality Assurance
- Quarterly documentation review
- User testing sessions
- Expert review process
- Continuous improvement

---

## Notes for AI Assistants

When using this documentation to help users:

1. **Start with the how-to guides** for specific tasks
2. **Reference tutorials** for learning journeys
3. **Consult explanations** for deeper understanding
4. **Check reference** for API details
5. **Provide complete, working code** whenever possible
6. **Link to relevant docs** for further reading
7. **Adapt examples** to user's specific device
8. **Consider migration path** for existing EPICS users

The Stage 1 document should contain enough information to:
- Understand FastCS concepts and architecture
- Create a basic controller with attributes
- Set up device communication
- Configure both CA and PVA transports
- Test and verify the implementation
- Troubleshoot common issues
- Migrate from existing EPICS IOCs

---

## Related Resources

- FastCS GitHub: https://github.com/DiamondLightSource/FastCS
- Diataxis Framework: https://diataxis.fr
- EPICS Documentation: https://epics-controls.org
- p4p Documentation: https://mdavidsaver.github.io/p4p/
- pythonSoftIOC Documentation: https://github.com/DiamondLightSource/pythonSoftIOC
