# PROJECT_BRIEF.md

## Name

SignalGraph

## One-liner

Credibility-adjusted traction for GitHub repositories.

## Problem

GitHub stars are often used as shorthand for technical traction, but visible popularity can be noisy and potentially manipulated. Investors and diligence teams need a more trustworthy signal.

## Solution

SignalGraph detects suspicious starring behavior and produces a credibility-adjusted view of repository traction using:

- manipulation risk
- star integrity
- adoption
- builder quality
- durability

## MVP

Input a public GitHub repo URL and receive:

- scorecard
- suspicious timeline windows
- explanation of major drivers
- raw stars vs adjusted score comparison

## Product principles

- explainability first
- conservative language
- modular scoring
- demoable even with mock data

## Research context

See `PROGRESS.md` at repo root for paper links (StarScout / ICSE 2026), GH Archive, and GitHub star semantics. External claims about prevalence of manipulation should be cited from primary sources.
