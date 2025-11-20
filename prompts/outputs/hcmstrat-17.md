The following report details the sentiment analysis for **HCMSTRAT-17** and its hierarchy.

# Sentiment Analysis for [HCMSTRAT-17](https://issues.redhat.com/browse/HCMSTRAT-17)

**Created on** _Thursday, November 20, 2025_

# TL;DR

Sentiment is **Cautiously Optimistic**. Critical adoption blockers related to Disaster Recovery (ROSA-86) have moved to "Green" status with successful validation in integration. However, observability initiatives (ROSA-383) are recovering from a "Red" status due to reorganization impacts, and other initiatives (ROSA-415) are progressing slowly due to competing priorities.

# Executive Summary

The overall effort to remove ROSA HCP adoption blockers is showing mixed but trending positive results in its most critical areas. The **Disaster Recovery** stream (ROSA-86) has achieved a significant milestone with the team agreeing to move the feature to "Green" following successful performance and restoration tests. This is a major confidence booster for the overall outcome.

However, cross-cutting concerns remain. **Observability** work (ROSA-383) was previously flagged as "Red" due to team capacity and reorganization but is now resuming with a target to deliver dashboards by December. **Etcd storage management** (ROSA-415) is seeing slow progress, identified as a "value add" rather than a hard blocker, which subjects it to deprioritization.

## Cross-cutting observations

*   **Resource Constraints**: Multiple streams (ROSA-415, ROSA-383) mention "team capacity" or "competing priorities" as reasons for slow progress or previous delays.
*   **Inter-team Dependencies**: High dependency on OCM and Service Development teams for API changes (e.g., OCM-19652) and OADP/Velero integration (ACM-26515).
*   **Freshness**: Most critical issues have very recent updates (mid-November 2025), indicating active management.

## Overall sentiment drivers

*   **Positive**: **ROSA-86 (DR Restoration)** moving to Green is the primary positive driver. **ROSA-356 (Day-2 Machine Pool)** integration environment is fully tested and successful.
*   **Negative/Risk**: **ROSA-383 (Correlate Operations)** recovering from Red status. **OSD-31045 (Shared VPC Notifications)** was paused pending customer feedback.

## Suggested watch items

*   **[ROSA-383](https://issues.redhat.com/browse/ROSA-383)**: Verify if the resumed work hits the December 1st target for stage dashboards.
*   **[ROSA-387](https://issues.redhat.com/browse/ROSA-387)**: Watch for the BU/SRE management review of the SOP for 4.16 EOL handling.
*   **[ACM-26515](https://issues.redhat.com/browse/ACM-26515)**: Critical task to reestablish MC backups in OADP v1.5; currently in testing.

## Summary of impact

The success of ROSA-86 (DR) directly unblocks critical reliability concerns for HCP adoption. Delays in observability (ROSA-383) may hinder SRE's ability to troubleshoot effectively at scale but are being addressed. The slow pace of ROSA-415 (Etcd) is a managed risk.

# Supporting Information

## [HCMSTRAT-17](https://issues.redhat.com/browse/HCMSTRAT-17) Removing ROSA HCP Adoption Blockers

*   **Type:** Outcome
*   **Status:** In Progress
*   **Status-Summary:** _None provided_
*   **Status-Summary (calculated):** Mixed - Critical children trending Green, others recovering.
*   **Color-Status (calculated):** Yellow
*   **Comments:** Parent outcome tracking multiple high-priority initiatives.
*   **Sentiment:** Neutral

## [ROSA-86](https://issues.redhat.com/browse/ROSA-86) ROSA HCP - DR restoration improvements

*   **Type:** Feature
*   **Status:** In Progress
*   **Status-Summary:** Nov 7th: Team agrees to move the feature to GREEN. Perf tests in integration are looking good. Restoration tests didn't show any blocker flag.
*   **Status-Summary (calculated):** Green - Major milestones met.
*   **Color-Status (calculated):** Green
*   **Comments:** Recent updates from Nov 18th indicate FVT tests are written and restoration scenarios are being manually tested. The team has explicitly agreed to move the feature status to Green.
*   **Sentiment:** Positive

## [ROSA-383](https://issues.redhat.com/browse/ROSA-383) ROSA HCP: Correlate operations through components

*   **Type:** Initiative
*   **Status:** In Progress
*   **Status-Summary:** Nov 17th: Resume pending dashboards to deliver. Oct 9th: Moving from Yellow to Red as this effort was impacted due the ROSA re-organization.
*   **Status-Summary (calculated):** Recovering from Red.
*   **Color-Status (calculated):** Red
*   **Comments:** The initiative was impacted by re-orgs but work has resumed with a target to have stage ready by Dec 1st.
*   **Sentiment:** Negative (but improving)

## [ROSA-356](https://issues.redhat.com/browse/ROSA-356) Day-2 machine pool support (Technical Enablement)

*   **Type:** Feature
*   **Status:** In Progress
*   **Status-Summary:** Nov 18: Integration environment has been fully tested with capa-annotator and successfully scaled from and to zero.
*   **Status-Summary (calculated):** On Track.
*   **Color-Status (calculated):** Green
*   **Comments:** Integration testing is successful. Currently awaiting architectural decisions on `capa-annotator` vs native Hypershift deployment, but technical validation is complete.
*   **Sentiment:** Positive

## [ROSA-415](https://issues.redhat.com/browse/ROSA-415) Proactive management of etcd storage in managed OpenShift clusters

*   **Type:** Initiative
*   **Status:** In Progress
*   **Status-Summary:** Work is slowly progressing... prioritization fluctuates...
*   **Status-Summary (calculated):** Slow Progress.
*   **Color-Status (calculated):** Yellow
*   **Comments:** Describes work as "slowly progressing" and "value add" rather than a blocker. Milestone 2 is in refinement.
*   **Sentiment:** Neutral

## [ROSA-387](https://issues.redhat.com/browse/ROSA-387) SRE has a process for out of support version HCP clusters

*   **Type:** Initiative
*   **Status:** In Progress
*   **Status-Summary:** 18 November 2025: SOP pull request has received initial review. OCM-20749 identified as requirement.
*   **Status-Summary (calculated):** Blocked/Pending Review.
*   **Color-Status (calculated):** Yellow
*   **Comments:** Progress is heavily dependent on reviews (BU/SRE mgmt) and clarification of security handling (HCMSEC-520).
*   **Sentiment:** Neutral

## [SREP-2576](https://issues.redhat.com/browse/SREP-2576) SRE tasks for ROSA-HCP Shared-VPC

*   **Type:** Epic
*   **Status:** In Progress
*   **Status-Summary:** SOP work is done. Managed Policy is still under review by AWS.
*   **Status-Summary (calculated):** Blocked by External Review.
*   **Color-Status (calculated):** Yellow
*   **Comments:** The remaining work is dependent on AWS review of the Managed Policy.
*   **Sentiment:** Neutral

## [SREP-2315](https://issues.redhat.com/browse/SREP-2315) capa-annotator: Configure environments for autoscaling from zero

*   **Type:** Story
*   **Status:** In Progress
*   **Status-Summary:** Integration environment configured and running.
*   **Status-Summary (calculated):** On Track.
*   **Color-Status (calculated):** Green
*   **Comments:** Integration tested successfully. Pending decision on rollout strategy (rolling into hypershift deployment).
*   **Sentiment:** Positive

## [ACM-26515](https://issues.redhat.com/browse/ACM-26515) Reestablish MC backups in OADP v1.5

*   **Type:** Task
*   **Status:** In Progress
*   **Status-Summary:** _None_
*   **Status-Summary (calculated):** Active Testing.
*   **Color-Status (calculated):** Yellow
*   **Comments:** Critical task for the DR initiative. Code is currently being tested by FM and DR teams.
*   **Sentiment:** Neutral

## [OSD-31045](https://issues.redhat.com/browse/OSD-31045) Send customer notifications for ROSA HCP Shared VPC IAM policy migration

*   **Type:** Story
*   **Status:** In Progress
*   **Status-Summary:** _None_
*   **Status-Summary (calculated):** Paused.
*   **Color-Status (calculated):** Yellow
*   **Comments:** Comments indicate work was paused waiting for customer feedback, with a recent ping (Nov 20) asking if work can continue.
*   **Sentiment:** Negative

 (Stalled**: Sentiment:** Neutral