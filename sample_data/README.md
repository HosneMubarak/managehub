# Sample Data for Import Testing

This directory contains sample CSV files for testing the django-import-export functionality.

## Files Included

### 1. business_areas.csv
Sample business areas for the organization:
- IT, CTO, OE, Consumer, Finance, HR, Marketing, Sales
- Includes name, description, and is_active fields

### 2. project_types.csv
Common project types:
- Project, Enhancement, Maintenance, Research, Support, Infrastructure, Security, Training
- Includes name and description fields

### 3. users.csv
Sample user accounts:
- 8 sample users with different roles and occupations
- Includes all user fields: email, names, roles, contact info, etc.
- Default password for imported users: `TempPass123!`

### 4. projects.csv
Sample projects demonstrating various scenarios:
- 5 projects with different statuses, priorities, and assignments
- Includes all project fields: IDs, descriptions, assignments, timelines, etc.
- Shows many-to-many relationships (assigned_users) using pipe separator

## Import Order

For best results, import in this order:
1. **business_areas.csv** - Required for projects
2. **project_types.csv** - Required for projects  
3. **users.csv** - Required for project managers and assignments
4. **projects.csv** - Depends on all above data

## Usage Instructions

1. Go to Django Admin panel
2. Navigate to the model you want to import (e.g., Projects > Projects)
3. Click "Import" button
4. Select the corresponding CSV file
5. Review the preview and confirm import
6. Check for any errors and resolve them

## Field Formats

### Date Fields
- Format: YYYY-MM-DD (e.g., 2024-01-15)

### Choice Fields
- Status: NEW, IN_PROGRESS, COMPLETE, ON_HOLD, CANCELLED
- Priority: LOW, MEDIUM, HIGH, CRITICAL
- Effort Size: S, M, L
- Gender: Male, Female, Other
- Occupation: network_engineer, system_admin, devops_engineer, etc.

### Many-to-Many Fields
- Use pipe separator (|) for multiple values
- Example: user1@email.com|user2@email.com

### Boolean Fields
- Use: True, False (case-sensitive)

## Validation Notes

- Project IDs must be exactly 7 digits
- Email addresses must be valid format
- Required fields cannot be empty
- Foreign key references must exist (import dependencies first)
- Choice fields must use exact values from model definitions
