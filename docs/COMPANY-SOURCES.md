# Company-board sources

Lever and Ashby are supported as optional, configured integrations. They read
published postings from named company boards, not platform-wide searches.

Set these in `backend/.env` (or the root Compose environment):

```dotenv
LEVER_BOARDS=your-lever-slug|Company Name,another-slug|Another Company
ASHBY_BOARDS=your-ashby-slug|Company Name
```

Use real slugs from the companies' careers pages; these examples are placeholders.
Empty lists disable the source. Restart the API/scheduler after changing config.
Up to 25 boards per integration are supported per run. Lever fetches pages of 100
with a 10-page cap; exceeding it reports failure instead of silent success.
Requests use the existing timeout and retry configuration. A failed board is
isolated and a mixed result is reported as PARTIAL in source-health records.

The scraper preserves location restrictions and original posting URLs. Ashby
unlisted postings are excluded. Hybrid work is kept distinct from remote work.
Compensation remains source text; currency conversion and reliable salary
filtering are separate roadmap items. Lever posting dates are left unknown.

Fixture tests cover normalization, failure isolation, malformed responses,
pagination, unlisted jobs and hybrid locations. Live company boards have not
been smoke-tested or enabled by default. Before commercial aggregation, confirm
appropriate use and attribution for each selected source/company.

Implementation references:
- [Lever Postings API](https://github.com/lever/postings-api)
- [Ashby Job Postings API](https://developers.ashbyhq.com/docs/public-job-posting-api)

URL deduplication now retains job-identifying query parameters and hash routes.
Only known advertising parameters are removed from the in-run comparison key.
Cross-run and cross-source semantic deduplication remain future work.
