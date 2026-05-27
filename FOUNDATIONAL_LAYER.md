# The Foundational Layer (Local Engine)

## Overview
The Foundational Layer represents the core local infrastructure of the AI Personal Employee. It consists of two main components: the Nerve Center (Obsidian) and the Muscle (Claude Code/Qwen CLI).

## The Nerve Center (Obsidian)

### Function
- Acts as the Graphical User Interface (GUI)
- Serves as the Long-Term Memory system
- Provides centralized access to all information and tasks

### Key Files
- **Dashboard.md**: Real-time summary of bank balance, pending messages, and active business projects
- **Company_Handbook.md**: Contains "Rules of Engagement" (e.g., "Always be polite on WhatsApp," "Flag any payment over $500 for my approval")

### Benefits
- Data remains local and secure
- Easy human review and intervention
- Persistent storage of all interactions and decisions

## The Muscle (Claude Code/Qwen CLI)

### Function
- Runs in the terminal environment
- Points directly at the Obsidian vault
- Uses File System tools to read tasks and write reports

### Key Features
- **File System Integration**: Reads from and writes to the Obsidian vault
- **Ralph Wiggum Loop**: Implements a Stop hook that keeps Claude/Qwen iterating until multi-step tasks are complete
- **Continuous Processing**: Works autonomously until tasks are fully resolved

### Configuration
The Claude/Qwen CLI should be configured to:
- Monitor the Obsidian vault for new tasks
- Process tasks according to the Company Handbook rules
- Update Dashboard.md with current status
- Create new files in appropriate directories based on task outcomes

## Integration Points

### Data Flow
1. New tasks appear in the Obsidian vault
2. Claude/Qwen detects and processes these tasks
3. Results are written back to the vault
4. Dashboard.md is updated with current status
5. Human review occurs as needed

### Security
- All sensitive data remains local
- Human approval required for sensitive actions
- Complete audit trail maintained in the vault

## Implementation Notes
- The system should be designed to work offline when possible
- Regular synchronization points should be established
- Error handling and recovery procedures must be robust