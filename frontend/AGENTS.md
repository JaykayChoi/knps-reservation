# FRONTEND KNOWLEDGE BASE

## OVERVIEW
Single-page application for managing reservation alert settings.

## TECH STACK
- Tailwind CSS (CDN)
- Vanilla JavaScript
- Fetch API for backend communication

## CONVENTIONS
- Use modern Tailwind utility classes for layout.
- Sync state with backend immediately upon "Save" action.
- Use `localStorage` only for UI-only persistence (e.g., dark mode, if any), but core settings must come from the server.

## UI COMPONENTS
- **Frequency/Day Picker**: Checkboxes for Fri/Sat/Sun + Week count.
- **Specific Date Range**: Calendar inputs for custom ranges.
- **Facility/Park Selectors**: Checkbox groups for filtering.
- **Notification Config**: Token and Chat ID fields.
- **Status Dashboard**: Last check time and result log.
