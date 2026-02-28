---
name: github-project
description: "GitHub Project management via `gh` CLI: create projects, add items, set custom fields (Priority, Size, Dates), configure views, and manage workflows. Use when: (1) creating or managing GitHub Projects, (2) adding tasks as Draft Issues, (3) setting Priority/Size/Dates, (4) viewing project status, (5) automating task workflows. NOT for: repository operations (use github skill), issue/PR management without project context."
---

# GitHub Project Skill

Manage GitHub Projects using the `gh` CLI with custom fields, views, and workflows.

## When To Use

✅ **USE this skill when:**

- Creating or configuring GitHub Projects
- Adding tasks/items to a Project
- Setting custom fields (Priority, Size, Start Date, Target Date)
- Viewing project status and items
- Managing Board/Table/Roadmap views
- Automating task workflows

## When NOT to Use

❌ **DON'T use this skill when:**

- Repository operations (clone, push, pull) → use `git` directly
- Issue/PR management without Project context → use `github` skill
- Complex API queries → use `gh api` directly

## Setup

### 1. Authentication

GitHub Projects requires additional scope:

```bash
# Add project scope
gh auth refresh -s read:project

# Verify
gh auth status
```

### 2. Verify Project Access

```bash
# List projects in an organization
gh project list --owner <org-name>

# Example
gh project list --owner onizuka-agi-co
```

## Common Commands

### Project Information

```bash
# List all projects
gh project list --owner <org-name>

# Get project ID
gh project list --owner <org-name> --format json | jq -r '.projects[] | "\(.number)\t\(.title)\t\(.id)"'

# List fields in a project
gh project field-list <project-number> --owner <org-name> --format json

# List items in a project
gh project item-list <project-number> --owner <org-name> --format json
```

### Adding Items

```bash
# Add a Draft Issue to a project
gh project item-add <project-number> --owner <org-name> \
  --title "Task Title" \
  --body "Task description"

# Add an existing Issue to a project
gh project item-add <project-number> --owner <org-name> \
  --url https://github.com/owner/repo/issues/123
```

### Editing Items

```bash
# Get field IDs first
gh project field-list <project-number> --owner <org-name> --format json

# Get item IDs
gh project item-list <project-number> --owner <org-name> --format json

# Set Single Select field (Priority, Size, Status)
gh project item-edit --project-id <project-id> \
  --id <item-id> \
  --field-id <field-id> \
  --single-select-option-id <option-id>

# Set Date field (Start Date, Target Date)
gh project item-edit --project-id <project-id> \
  --id <item-id> \
  --field-id <field-id> \
  --date "2026-02-28"

# Set Number field (Estimate)
gh project item-edit --project-id <project-id> \
  --id <item-id> \
  --field-id <field-id> \
  --number 5

# Set Text field
gh project item-edit --project-id <project-id> \
  --id <item-id> \
  --field-id <field-id> \
  --text "Custom text"

# Clear a field
gh project item-edit --project-id <project-id> \
  --id <item-id> \
  --field-id <field-id> \
  --clear
```

## Field Types

### Single Select Fields

Common fields: Status, Priority, Size

```bash
# List options for a Single Select field
gh project field-list <project-number> --owner <org-name> --format json | \
  jq '.fields[] | select(.name == "Priority") | .options'

# Set Status
gh project item-edit --project-id PVT_kwDOD7cTBc4BQW8J \
  --id PVTI_lADOD7cTBc4BQW8JzgmV2BE \
  --field-id PVTSSF_lADOD7cTBc4BQW8Jzg-gICI \
  --single-select-option-id f75ad846

# Set Priority
gh project item-edit --project-id PVT_kwDOD7cTBc4BQW8J \
  --id PVTI_lADOD7cTBc4BQW8JzgmV2BE \
  --field-id PVTSSF_lADOD7cTBc4BQW8Jzg-gIGo \
  --single-select-option-id 0a877460
```

### Date Fields

Common fields: Start Date, Target Date

```bash
# Set Start Date
gh project item-edit --project-id PVT_kwDOD7cTBc4BQW8J \
  --id PVTI_lADOD7cTBc4BQW8JzgmV2BE \
  --field-id PVTF_lADOD7cTBc4BQW8Jzg-gIG0 \
  --date "2026-02-28"

# Set Target Date
gh project item-edit --project-id PVT_kwDOD7cTBc4BQW8J \
  --id PVTI_lADOD7cTBc4BQW8JzgmV2BE \
  --field-id PVTF_lADOD7cTBc4BQW8Jzg-gIG4 \
  --date "2026-03-07"
```

## Workflow Templates

### Initial Project Setup

```bash
# 1. Create project (via GitHub UI)
# Go to https://github.com/orgs/<org-name>/projects

# 2. Get project info
gh project list --owner <org-name>
# Note the project number and ID

# 3. Add custom fields (via GitHub UI)
# - Status: Backlog, Ready, In progress, In review, Done
# - Priority: P0, P1, P2
# - Size: XS, S, M, L, XL
# - Start date (Date)
# - Target date (Date)

# 4. Get field IDs
gh project field-list <project-number> --owner <org-name> --format json > fields.json
```

### Add Multiple Tasks

```bash
# Create a script to add multiple tasks
PROJECT_ID="PVT_kwDOD7cTBc4BQW8J"
ORG="onizuka-agi-co"
PROJECT_NUM="1"

# Define tasks
tasks=(
  "Task 1|Description for task 1|P1|M|2026-02-28|2026-02-28"
  "Task 2|Description for task 2|P1|S|2026-02-28|2026-03-01"
  "Task 3|Description for task 3|P2|L|2026-03-01|2026-03-07"
)

# Add each task
for task in "${tasks[@]}"; do
  IFS='|' read -r title body priority size start target <<< "$task"
  
  # Add item
  item_id=$(gh project item-add $PROJECT_NUM --owner $ORG \
    --title "$title" \
    --body "$body" \
    --format json | jq -r '.id')
  
  echo "Added: $title (ID: $item_id)"
done
```

### Update Task Status

```bash
# Move task to "In progress"
gh project item-edit --project-id PVT_kwDOD7cTBc4BQW8J \
  --id PVTI_lADOD7cTBc4BQW8JzgmV2BE \
  --field-id PVTSSF_lADOD7cTBc4BQW8Jzg-gICI \
  --single-select-option-id 47fc9ee4

# Move task to "Done"
gh project item-edit --project-id PVT_kwDOD7cTBc4BQW8J \
  --id PVTI_lADOD7cTBc4BQW8JzgmV2BE \
  --field-id PVTSSF_lADOD7cTBc4BQW8Jzg-gICI \
  --single-select-option-id 98236657
```

## Querying Project Data

### View All Items with Details

```bash
# Get all items with key fields
gh project item-list <project-number> --owner <org-name> --format json | \
  jq -r '.items[] | "\(.title)\n  Status: \(.status // "None")\n  Priority: \(.priority // "None")\n  Size: \(.size // "None")\n  Start: \(.["start date"] // "None")\n  Target: \(.["target date"] // "None")\n"'
```

### Filter by Status

```bash
# Get all items in "Backlog"
gh project item-list <project-number> --owner <org-name> --format json | \
  jq -r '.items[] | select(.status == "Backlog") | .title'

# Get all items in "In progress"
gh project item-list <project-number> --owner <org-name> --format json | \
  jq -r '.items[] | select(.status == "In progress") | .title'
```

### Filter by Priority

```bash
# Get all P1 tasks
gh project item-list <project-number> --owner <org-name> --format json | \
  jq -r '.items[] | select(.priority == "P1") | "\(.title) (Status: \(.status))"'
```

## Best Practices

### 1. Naming Conventions

- **Project Name**: `<Org Name> Roadmap` or `<Team> Sprint Board`
- **Status Values**: Backlog → Ready → In progress → In review → Done
- **Priority Values**: P0 (Critical) / P1 (High) / P2 (Medium) / P3 (Low)
- **Size Values**: XS (< 1h) / S (< 4h) / M (< 1d) / L (< 3d) / XL (< 1w)

### 2. Workflow

1. **Planning**: Add tasks to Backlog with Priority and Size
2. **Sprint Start**: Move tasks to Ready, set Start Date
3. **Work**: Move to In Progress when starting
4. **Review**: Move to In Review when ready
5. **Complete**: Move to Done, update Target Date if needed

### 3. Automation

- Use GitHub Actions to auto-add Issues to Project
- Auto-move items based on PR creation/merge
- Send notifications to Discord/Slack on status changes

### 4. Views

- **Board View**: Kanban-style for daily work
- **Table View**: Detailed list for planning
- **Roadmap View**: Timeline for stakeholders

## Common Pitfalls

- **Missing scope**: Run `gh auth refresh -s read:project` before using
- **Wrong field type**: Use `--single-select-option-id` for dropdowns, `--date` for dates
- **Field not found**: Check field ID with `field-list` command
- **Item not found**: Check item ID with `item-list` command

## Resources

- `scripts/add_tasks.py`: Batch add tasks from CSV/JSON
- `scripts/update_status.py`: Update task status programmatically
- `references/field_ids.md`: Common field IDs for ONIZUKA AGI projects

## Example Requests

- "Add 5 tasks to the GitHub Project with P1 priority"
- "Update all P1 tasks to start on 2026-03-01"
- "Show me all tasks in 'In progress' status"
- "Create a roadmap view with start and target dates"
