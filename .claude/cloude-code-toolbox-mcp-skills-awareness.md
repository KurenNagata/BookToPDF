# Cloude Code ToolBox — MCP & Skills awareness

_Generated: 2026-07-14T04:32:00.026Z_

## How to use this report

- **Saved copy:** This file is **`.claude/cloude-code-toolbox-mcp-skills-awareness.md`** — refreshed whenever the toolbox runs an MCP & Skills scan (including on workspace open when auto-scan is enabled). It is meant for **Claude Code workspace context** together with `CLAUDE.md` (which gets a shorter replaceable summary when auto-merge is on).
- **MCP:** Lists **configured** servers from Claude Code config (`~/.claude.json` for user scope, `.mcp.json` for project scope). Use `/mcp` in the Claude Code panel to connect servers for your session.
- **Skills:** **On-disk** folders with `SKILL.md`. Claude Code does not auto-load them; attach `SKILL.md` or paths in chat when useful.
- **Task routing:** When the user’s request matches a server’s purpose (e.g. Confluence → Confluence/Atlassian MCP), prefer that **server id** from the tables below.

---

## MCP — workspace

Workspace `mcp.json` _(folder: BookToPDF)_

- **c:\Users\xxxxx\BookToPDF\.mcp.json** — _File missing_

_No active workspace servers in mcp.json._

## MCP — user profile

- **C:\Users\xxxxx\.claude.json** — _File exists — no servers defined_

_No active user-scoped servers in mcp.json._

## Skills (local `SKILL.md` folders)

### Project-scoped

_None found (or no workspace open)._

### User-scoped

- **agents-sdk** — `C:\Users\xxxxx\.copilot\skills\agents-sdk`
  - Build AI agents on Cloudflare Workers using the Agents SDK. Load when creating stateful agents, durable workflows, real-time WebSocket apps, scheduled tasks, MCP servers, chat applications, voice agents, or browser autom

- **cloudflare** — `C:\Users\xxxxx\.copilot\skills\cloudflare`
  - Comprehensive Cloudflare platform skill covering Workers, Pages, storage (KV, D1, R2), AI (Workers AI, Vectorize, Agents SDK), feature flags (Flagship), networking (Tunnel, Spectrum), security (WAF, DDoS), and infrastruc

- **cloudflare-email-service** — `C:\Users\xxxxx\.copilot\skills\cloudflare-email-service`
  - Send and receive transactional emails with Cloudflare Email Service (Email Sending + Email Routing). Use when building email sending (Workers binding or REST API), email routing, Agents SDK email handling, or integrating

- **durable-objects** — `C:\Users\xxxxx\.copilot\skills\durable-objects`
  - Create and review Cloudflare Durable Objects. Use when building stateful coordination (chat rooms, multiplayer games, booking systems), implementing RPC methods, SQLite storage, alarms, WebSockets, or reviewing DO code f

- **sandbox-sdk** — `C:\Users\xxxxx\.copilot\skills\sandbox-sdk`
  - Build sandboxed applications for secure code execution. Load when building AI code execution, code interpreters, CI/CD systems, interactive dev environments, or executing untrusted code. Covers Sandbox SDK lifecycle, com

- **turnstile-spin** — `C:\Users\xxxxx\.copilot\skills\turnstile-spin`
  - Set up Cloudflare Turnstile end-to-end in a project — scan the codebase, create the widget via the Cloudflare API, deploy the managed siteverify Worker, write the frontend snippets, validate, and persist the skill. Load 

- **web-perf** — `C:\Users\xxxxx\.copilot\skills\web-perf`
  - Analyzes web performance using Chrome DevTools MCP. Measures Core Web Vitals (LCP, INP, CLS) and supplementary metrics (FCP, TBT, Speed Index), identifies render-blocking resources, network dependency chains, layout shif

- **workers-best-practices** — `C:\Users\xxxxx\.copilot\skills\workers-best-practices`
  - Reviews and authors Cloudflare Workers code against production best practices. Load when writing new Workers, reviewing Worker code, configuring wrangler.jsonc, or checking for common Workers anti-patterns (streaming, fl

- **wrangler** — `C:\Users\xxxxx\.copilot\skills\wrangler`
  - Cloudflare Workers CLI for deploying, developing, and managing Workers, KV, R2, D1, Vectorize, Hyperdrive, Workers AI, Containers, Queues, Workflows, Pipelines, and Secrets Store. Load before running wrangler commands to

- **agents-sdk** — `C:\Users\xxxxx\.claude\skills\agents-sdk`
  - Build AI agents on Cloudflare Workers using the Agents SDK. Load when creating stateful agents, durable workflows, real-time WebSocket apps, scheduled tasks, MCP servers, chat applications, voice agents, or browser autom

- **algorithmic-art** — `C:\Users\xxxxx\.claude\skills\algorithmic-art`
  - Creating algorithmic art using p5.js with seeded randomness and interactive parameter exploration. Use this when users request creating art using code, generative art, algorithmic art, flow fields, or particle systems. C

- **canvas-design** — `C:\Users\xxxxx\.claude\skills\canvas-design`
  - Create beautiful visual art in .png and .pdf documents using design philosophy. You should use this skill when the user asks to create a poster, piece of art, design, or other static piece. Create original visual designs

- **claude-api** — `C:\Users\xxxxx\.claude\skills\claude-api`
  - |-

- **cloudflare** — `C:\Users\xxxxx\.claude\skills\cloudflare`
  - Comprehensive Cloudflare platform skill covering Workers, Pages, storage (KV, D1, R2), AI (Workers AI, Vectorize, Agents SDK), feature flags (Flagship), networking (Tunnel, Spectrum), security (WAF, DDoS), and infrastruc

- **cloudflare-email-service** — `C:\Users\xxxxx\.claude\skills\cloudflare-email-service`
  - Send and receive transactional emails with Cloudflare Email Service (Email Sending + Email Routing). Use when building email sending (Workers binding or REST API), email routing, Agents SDK email handling, or integrating

- **doc-coauthoring** — `C:\Users\xxxxx\.claude\skills\doc-coauthoring`
  - Guide users through a structured workflow for co-authoring documentation. Use when user wants to write documentation, proposals, technical specs, decision docs, or similar structured content. This workflow helps users ef

- **docx** — `C:\Users\xxxxx\.claude\skills\docx`
  - Use this skill whenever the user wants to create, read, edit, or manipulate Word documents (.docx files). Triggers include: any mention of 'Word doc', 'word document', '.docx', or requests to produce professional documen

- **durable-objects** — `C:\Users\xxxxx\.claude\skills\durable-objects`
  - Create and review Cloudflare Durable Objects. Use when building stateful coordination (chat rooms, multiplayer games, booking systems), implementing RPC methods, SQLite storage, alarms, WebSockets, or reviewing DO code f

- **frontend-design** — `C:\Users\xxxxx\.claude\skills\frontend-design`
  - Guidance for distinctive, intentional visual design when building new UI or reshaping an existing one. Helps with aesthetic direction, typography, and making choices that don't read as templated defaults.

- **mcp-builder** — `C:\Users\xxxxx\.claude\skills\mcp-builder`
  - Guide for creating high-quality MCP (Model Context Protocol) servers that enable LLMs to interact with external services through well-designed tools. Use when building MCP servers to integrate external APIs or services, 

- **pdf** — `C:\Users\xxxxx\.claude\skills\pdf`
  - Use this skill whenever the user wants to do anything with PDF files. This includes reading or extracting text/tables from PDFs, combining or merging multiple PDFs into one, splitting PDFs apart, rotating pages, adding w

- **pptx** — `C:\Users\xxxxx\.claude\skills\pptx`
  - Use this skill any time a .pptx file is involved in any way — as input, output, or both. This includes: creating slide decks, pitch decks, or presentations; reading, parsing, or extracting text from any .pptx file (even 

- **sandbox-sdk** — `C:\Users\xxxxx\.claude\skills\sandbox-sdk`
  - Build sandboxed applications for secure code execution. Load when building AI code execution, code interpreters, CI/CD systems, interactive dev environments, or executing untrusted code. Covers Sandbox SDK lifecycle, com

- **skill-creator** — `C:\Users\xxxxx\.claude\skills\skill-creator`
  - Create new skills, modify and improve existing skills, and measure skill performance. Use when users want to create a skill from scratch, edit, or optimize an existing skill, run evals to test a skill, benchmark skill pe

- **slack-gif-creator** — `C:\Users\xxxxx\.claude\skills\slack-gif-creator`
  - Knowledge and utilities for creating animated GIFs optimized for Slack. Provides constraints, validation tools, and animation concepts. Use when users request animated GIFs for Slack like "make me a GIF of X doing Y for 

- **theme-factory** — `C:\Users\xxxxx\.claude\skills\theme-factory`
  - Toolkit for styling artifacts with a theme. These artifacts can be slides, docs, reportings, HTML landing pages, etc. There are 10 pre-set themes with colors/fonts that you can apply to any artifact that has been creatin

- **turnstile-spin** — `C:\Users\xxxxx\.claude\skills\turnstile-spin`
  - Set up Cloudflare Turnstile end-to-end in a project — scan the codebase, create the widget via the Cloudflare API, deploy the managed siteverify Worker, write the frontend snippets, validate, and persist the skill. Load 

- **web-artifacts-builder** — `C:\Users\xxxxx\.claude\skills\web-artifacts-builder`
  - Suite of tools for creating elaborate, multi-component claude.ai HTML artifacts using modern frontend web technologies (React, Tailwind CSS, shadcn/ui). Use for complex artifacts requiring state management, routing, or s

- **web-perf** — `C:\Users\xxxxx\.claude\skills\web-perf`
  - Analyzes web performance using Chrome DevTools MCP. Measures Core Web Vitals (LCP, INP, CLS) and supplementary metrics (FCP, TBT, Speed Index), identifies render-blocking resources, network dependency chains, layout shif

- **webapp-testing** — `C:\Users\xxxxx\.claude\skills\webapp-testing`
  - Toolkit for interacting with and testing local web applications using Playwright. Supports verifying frontend functionality, debugging UI behavior, capturing browser screenshots, and viewing browser logs.

- **workers-best-practices** — `C:\Users\xxxxx\.claude\skills\workers-best-practices`
  - Reviews and authors Cloudflare Workers code against production best practices. Load when writing new Workers, reviewing Worker code, configuring wrangler.jsonc, or checking for common Workers anti-patterns (streaming, fl

- **wrangler** — `C:\Users\xxxxx\.claude\skills\wrangler`
  - Cloudflare Workers CLI for deploying, developing, and managing Workers, KV, R2, D1, Vectorize, Hyperdrive, Workers AI, Containers, Queues, Workflows, Pipelines, and Secrets Store. Load before running wrangler commands to

- **xlsx** — `C:\Users\xxxxx\.claude\skills\xlsx`
  - Use this skill any time a spreadsheet file is the primary input or output. This means any task where the user wants to: open, read, edit, or fix an existing .xlsx, .xlsm, .csv, or .tsv file (e.g., adding columns, computi

- **agents-sdk** — `C:\Users\xxxxx\.cursor\skills\agents-sdk`
  - Build AI agents on Cloudflare Workers using the Agents SDK. Load when creating stateful agents, durable workflows, real-time WebSocket apps, scheduled tasks, MCP servers, chat applications, voice agents, or browser autom

- **cloudflare** — `C:\Users\xxxxx\.cursor\skills\cloudflare`
  - Comprehensive Cloudflare platform skill covering Workers, Pages, storage (KV, D1, R2), AI (Workers AI, Vectorize, Agents SDK), feature flags (Flagship), networking (Tunnel, Spectrum), security (WAF, DDoS), and infrastruc

- **cloudflare-email-service** — `C:\Users\xxxxx\.cursor\skills\cloudflare-email-service`
  - Send and receive transactional emails with Cloudflare Email Service (Email Sending + Email Routing). Use when building email sending (Workers binding or REST API), email routing, Agents SDK email handling, or integrating

- **durable-objects** — `C:\Users\xxxxx\.cursor\skills\durable-objects`
  - Create and review Cloudflare Durable Objects. Use when building stateful coordination (chat rooms, multiplayer games, booking systems), implementing RPC methods, SQLite storage, alarms, WebSockets, or reviewing DO code f

- **sandbox-sdk** — `C:\Users\xxxxx\.cursor\skills\sandbox-sdk`
  - Build sandboxed applications for secure code execution. Load when building AI code execution, code interpreters, CI/CD systems, interactive dev environments, or executing untrusted code. Covers Sandbox SDK lifecycle, com

- **turnstile-spin** — `C:\Users\xxxxx\.cursor\skills\turnstile-spin`
  - Set up Cloudflare Turnstile end-to-end in a project — scan the codebase, create the widget via the Cloudflare API, deploy the managed siteverify Worker, write the frontend snippets, validate, and persist the skill. Load 

- **web-perf** — `C:\Users\xxxxx\.cursor\skills\web-perf`
  - Analyzes web performance using Chrome DevTools MCP. Measures Core Web Vitals (LCP, INP, CLS) and supplementary metrics (FCP, TBT, Speed Index), identifies render-blocking resources, network dependency chains, layout shif

- **workers-best-practices** — `C:\Users\xxxxx\.cursor\skills\workers-best-practices`
  - Reviews and authors Cloudflare Workers code against production best practices. Load when writing new Workers, reviewing Worker code, configuring wrangler.jsonc, or checking for common Workers anti-patterns (streaming, fl

- **wrangler** — `C:\Users\xxxxx\.cursor\skills\wrangler`
  - Cloudflare Workers CLI for deploying, developing, and managing Workers, KV, R2, D1, Vectorize, Hyperdrive, Workers AI, Containers, Queues, Workflows, Pipelines, and Secrets Store. Load before running wrangler commands to

---

## Suggested next steps

- **MCP:** Use this extension’s hub **MCP** tab, or `claude mcp list` in the terminal. In Claude Code, use `/mcp` to connect servers for the session.
- **Edit config:** Open `~/.claude.json` (user MCP) or `<workspace>/.mcp.json` (project MCP) via the extension commands.
- **Refresh this report:** run **Intelligence — scan MCP & Skills awareness** again after changing MCP config or adding skills.

_Report from Cloude Code ToolBox extension._
