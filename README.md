# Public Company Research

Source files for public company and role research exports. Full candidate-specific preparation is kept in the private report library. Published pages are marked `noindex` and contain sourced public research only.

- [Report directory](docs/reports)
- [Combined report data schema](docs/schemas/company-report-v1.schema.json)
- [Legacy research-only schema](docs/schemas/company-report-research-v1.schema.json)
- [Bento interview-brief schema](docs/schemas/company-report-bento-v1.schema.json)

The schemas use JSON Schema Draft 2020-12 and describe the JSON in each HTML page's `company-report-data` script. New reports use the same bento UI as the full local brief, with a public-safe role-context tile in place of the personal prep checklist.
