# SOSParser Rules Engine – Known Issues

This directory contains JSON rule collections used by the SOSParser rules engine
to detect known issues in sosreport and supportconfig diagnostic bundles.

## How it works

Each `.json` file in `known_issues/` is a **collection** of rules.  The rules
engine loads every collection at startup, filters rules by the current format
type (`sosreport` or `supportconfig`), reads the targeted file(s) inside the
extracted diagnostic bundle, and applies the configured regex.  When the regex
matches, a health-summary **finding** is produced.

## JSON Schema

```jsonc
{
  // Collection metadata
  "collection": "kernel_issues",          // unique slug
  "description": "Kernel-related issues", // human-readable
  "version": "1.0",                       // semver for tracking changes

  "rules": [
    {
      // Rule identity
      "id": "kernel-panic",
      "name": "Kernel Panic Detected",
      "description": "Detects kernel panic events in logs",

      // Which format types this rule applies to.
      // Valid values: "sosreport", "supportconfig", "both"
      "applies_to": "both",

      // File paths (relative to the extracted root) to scan.
      // Separate lists per format; the engine picks the right one.
      "file_paths": {
        "sosreport": [
          "sos_commands/kernel/dmesg",
          "var/log/messages"
        ],
        "supportconfig": [
          "boot.txt",
          "messages.txt"
        ]
      },

      // Python regex applied to the file content.
      "regex": "\\bKernel panic\\b",

      // Optional regex flags: IGNORECASE, MULTILINE, DOTALL
      "regex_flags": ["IGNORECASE"],

      // Finding severity: "critical" or "warning"
      "severity": "critical",

      // Grouping category shown in the health card
      "category": "Kernel",

      // Short finding title.  {match_count} is substituted at runtime.
      "title": "Kernel panic detected ({match_count} occurrence(s))",

      // Optional detail text.  {match_count} available here too.
      "detail": "Check dmesg and system logs",

      // Tab to navigate to when the finding is clicked
      "section_link": "logs",

      // When true, count all regex matches and report the total.
      // When false (default), a single match is enough to trigger.
      "count_matches": true,

      // Optional: minimum match count to trigger (default: 1)
      "min_matches": 1,

      // Optional: set to true to disable without removing
      "enabled": true
    }
  ]
}
```

## Adding new rules

1. Create a new `.json` file in `known_issues/` (or add rules to an existing
   collection).
2. Follow the schema above.
3. Test against an example sosreport / supportconfig.

No code changes required – the engine picks up new files automatically.
