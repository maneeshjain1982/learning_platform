"""Curated certifications for Agentic AI and Generative AI, checked against official pages on CHECKED_ON.

Prices are list prices in USD before tax. Where a detail came only from a third-party guide, `notes` says so.
The "Refresh" button on the Career tab asks the LLM for anything newer than this list (see agents/career.py).
"""

from __future__ import annotations

CHECKED_ON = "2026-11-12"

TIERS = [
    {"id": "architect", "title": "Architect-level exams",
     "summary": "Proctored exams that test designing, governing and running agent systems. The most weight for an "
                "Agentic AI Architect role."},
    {"id": "developer", "title": "Developer and engineer exams",
     "summary": "Proctored exams that test building and shipping GenAI apps and agents on one platform."},
    {"id": "courses", "title": "Courses with a certificate",
     "summary": "Structured learning with projects and a completion certificate. Good for skills, lighter as a "
                "credential."},
    {"id": "foundational", "title": "Foundational",
     "summary": "Entry-level exams. Useful for non-specialists; skip if you are already building agents."},
]


def _cert(name, issuer, tier, url, *, code="", kind="Proctored exam", price="", duration="", fmt="", validity="",
          access="Open to anyone", focus="", fit="", notes="", top=False):
    return {"name": name, "issuer": issuer, "tier": tier, "url": url, "code": code, "kind": kind, "price": price,
            "duration": duration, "format": fmt, "validity": validity, "access": access, "focus": focus,
            "fit": fit, "notes": notes, "top_pick": top}


CERTS = [
    # ------------------------------------------------------------------ architect
    _cert("Claude Certified Architect – Foundations", "Anthropic", "architect",
          "https://anthropic-partners.skilljar.com/page/partner-certifications", code="CCAR-F",
          price="$125", duration="120 min", fmt="Multiple choice and scenario questions; pass mark 720 of 1,000",
          validity="12 months", access="Employees of Claude Partner Network organisations only",
          focus="Building production solutions with Claude: Claude Code, the Agent SDK, the API and MCP, with "
                "agentic architecture the largest domain.",
          fit="The most direct proof of Claude agent skills, and it matches the Claude Academy track. Blocked unless "
              "your employer is a Claude partner.",
          notes="Price rose from $99 on 30 Jun 2026. Domain weighting is from third-party prep guides.", top=True),
    _cert("Claude Certified Architect – Professional", "Anthropic", "architect",
          "https://anthropic-partners.skilljar.com/page/partner-certifications", code="CCAR-P",
          price="$175", duration="120 min", fmt="Multiple choice and scenario questions; pass mark 720 of 1,000",
          validity="12 months", access="Employees of Claude Partner Network organisations only",
          focus="Designing and governing Claude solutions at enterprise scale.",
          fit="The senior Claude credential. Foundations is not a prerequisite."),
    _cert("Google Cloud Professional Agentic Architect", "Google Cloud", "architect",
          "https://cloud.google.com/learn/certification/agentic-architect", kind="Exam + hands-on labs",
          price="$200", duration="2 hr exam, then labs", fmt="50-60 multiple-choice questions (Pearson), then "
          "hands-on labs in Google Skills", validity="1 year",
          focus="Low-code agent tools, coding agents, custom agents, evaluating and deploying agentic workflows, "
                "security and governance.",
          fit="One of the few agent exams with a hands-on lab part. Best if you build on Google Cloud.",
          notes="Recommends 3+ years on cloud and 1+ year building agents on Google Cloud. General availability "
                "around November 2026; check the page for dates.", top=True),
    _cert("Microsoft Certified: Multi-Agent AI Solutions Expert", "Microsoft", "architect",
          "https://learn.microsoft.com/en-us/credentials/certifications/resources/study-guides/ai-500", code="AI-500",
          price="$165", fmt="Proctored exam; pass mark 700", validity="1 year, renewed with a free online assessment",
          focus="Architecting multi-agent systems (15-20%), building them on Azure (30-35%), evaluation and "
                "monitoring (20-25%), security, guardrails and deployment (20-25%). Covers MCP, A2A, LangGraph, "
                "memory, context management and orchestration patterns.",
          fit="The closest syllabus to an Agentic AI Architect job, even if you don't use Azure.",
          notes="Requires AI-103 first, per third-party guides. Price from third-party guides.", top=True),
    _cert("Microsoft Certified: Agentic AI Business Solutions Architect Expert", "Microsoft", "architect",
          "https://learn.microsoft.com/en-us/credentials/certifications/resources/study-guides/ab-100", code="AB-100",
          price="$165", fmt="Proctored exam; pass mark 700", validity="1 year, renewed with a free online assessment",
          focus="Planning (35-40%), designing (30-35%) and deploying (20-25%) agent solutions with Copilot Studio, "
                "Microsoft Foundry, Dynamics 365 and Power Platform, including MCP, A2A, ROI and governance.",
          fit="Strong if you work with Microsoft business apps; less useful outside that stack.",
          notes="Needs an associate certification first, per third-party guides."),
    _cert("NVIDIA-Certified Professional: Agentic AI", "NVIDIA", "architect",
          "https://www.nvidia.com/en-us/learn/certification/agentic-ai-professional/", code="NCP-AAI",
          price="$200", duration="120 min", fmt="60-70 questions, online remotely proctored", validity="2 years",
          focus="Agent architecture and development (30%), evaluation and tuning, deployment and scaling, "
                "cognition, planning and memory, knowledge integration, safety and human oversight. About 7% is "
                "NVIDIA-specific.",
          fit="Mostly vendor-neutral agent engineering, so it carries across clouds.",
          notes="Registration showed 'Coming soon' on the official page on 12 Nov 2026."),

    # ------------------------------------------------------------------ developer
    _cert("AWS Certified Generative AI Developer – Professional", "AWS", "developer",
          "https://aws.amazon.com/certification/certified-generative-ai-developer-professional/", code="AIP-C01",
          price="$300", duration="180 min", fmt="75 multiple-choice and multiple-response questions; test centre or "
          "online", focus="Building and deploying production GenAI apps on AWS (Amazon Bedrock), with security and "
          "cost efficiency.",
          fit="The AWS credential for GenAI builders. Pick it if your target employers run on AWS.",
          notes="Recommends 2+ years building on AWS and 1 year with GenAI."),
    _cert("Claude Certified Developer – Foundations", "Anthropic", "developer",
          "https://anthropic-partners.skilljar.com/page/partner-certifications", code="CCDV-F",
          price="$125", duration="120 min", fmt="Multiple choice and scenario questions; pass mark 720 of 1,000",
          validity="12 months", access="Employees of Claude Partner Network organisations only",
          focus="Building with Claude as a developer.",
          fit="Developer counterpart to the Claude Architect exam."),
    _cert("Microsoft Certified: Azure AI Apps and Agents Developer Associate", "Microsoft", "developer",
          "https://learn.microsoft.com/en-us/credentials/certifications/resources/study-guides/ai-103", code="AI-103",
          price="$165", duration="120 min", fmt="Proctored exam; pass mark 700",
          validity="1 year, renewed with a free online assessment",
          focus="Building generative AI apps and agents on Azure and Microsoft Foundry.",
          fit="The step before AI-500. Replaced AI-102 in 2026.",
          notes="Price and duration from third-party guides."),
    _cert("GitHub Certified: Agentic AI Developer", "GitHub (Microsoft)", "developer",
          "https://learn.microsoft.com/en-us/credentials/certifications/resources/study-guides/gh-600", code="GH-600",
          price="$165", duration="120 min", fmt="Proctored exam",
          focus="Agentic software development with GitHub's coding agents and tooling.",
          fit="Good if your work centres on AI-assisted software delivery.",
          notes="Price and duration from third-party guides."),
    _cert("Databricks Certified Generative AI Engineer Associate", "Databricks", "developer",
          "https://www.databricks.com/learn/certification/genai-engineer-associate",
          price="$200", duration="90 min", fmt="45 scored multiple-choice questions; online or test centre",
          validity="2 years",
          focus="App development (30%), assembling and deploying (22%), design (14%), data prep (14%), evaluation "
                "and monitoring (12%), governance (8%), using Vector Search, Model Serving, MLflow, Unity Catalog.",
          fit="Strong for RAG and data-heavy GenAI roles on Databricks."),

    # ------------------------------------------------------------------ courses
    _cert("Agentic AI (DeepLearning.AI, Andrew Ng)", "DeepLearning.AI", "courses",
          "https://www.deeplearning.ai/courses/agentic-ai/", kind="Course + certificate",
          price="Free to audit; certificate needs Pro ($25/mo billed yearly)", duration="About 10 hr",
          fmt="31 videos, 7 code examples, 8 graded assignments",
          focus="Reflection, tool use, planning and multi-agent patterns, plus evaluation, error analysis, latency "
                "and cost.",
          fit="The best short course on agent design patterns. Pairs well with the Claude Academy track.", top=True),
    _cert("IBM RAG and Agentic AI Professional Certificate", "IBM (Coursera)", "courses",
          "https://www.coursera.org/professional-certificates/ibm-rag-and-agentic-ai", kind="Course + certificate",
          price="Coursera subscription (free audit per course)", duration="10 courses, about 100 hr",
          fmt="Video courses with labs and a capstone",
          focus="RAG, vector databases, LangChain, LangGraph, CrewAI, AG2, BeeAI, MCP and multi-agent systems.",
          fit="Broad hands-on coverage of the open-source agent frameworks employers list in JDs."),
    _cert("Hugging Face AI Agents Course", "Hugging Face", "courses",
          "https://huggingface.co/learn/agents-course/unit0/introduction", kind="Course + certificate",
          price="Free, including both certificates", fmt="Units, use-case assignment and a final challenge",
          focus="Agent fundamentals, smolagents, LlamaIndex and LangGraph, plus bonus units on function-calling "
                "fine-tuning and agent observability and evaluation.",
          fit="Free and practical. The final challenge is a good portfolio piece."),
    _cert("Agentic AI Nanodegree", "Udacity", "courses", "https://www.udacity.com/course/agentic-ai--nd900",
          kind="Course + certificate", price="Udacity subscription", duration="About 53 hr",
          fmt="4 courses, 4 projects with reviews",
          focus="Prompting for reasoning and planning, agentic workflows, building agents and multi-agent systems.",
          fit="Project-heavy, with mentor-reviewed work."),

    # ------------------------------------------------------------------ foundational
    _cert("AWS Certified AI Practitioner", "AWS", "foundational",
          "https://aws.amazon.com/certification/certified-ai-practitioner/", code="AIF-C01", price="$100",
          duration="90 min", fmt="65 questions", focus="AI, ML and GenAI concepts and AWS AI services.",
          fit="Entry level. Skip if you already build agents.", notes="Details from third-party guides."),
    _cert("Google Cloud Generative AI Leader", "Google Cloud", "foundational",
          "https://cloud.google.com/learn/certification/generative-ai-leader", price="$99",
          focus="GenAI strategy and Google Cloud's GenAI offerings, for business and technical leaders.",
          fit="For leaders and pre-sales. Not technical.", notes="Price from third-party guides."),
    _cert("NVIDIA-Certified Associate: Generative AI LLMs", "NVIDIA", "foundational",
          "https://www.nvidia.com/en-us/learn/certification/generative-ai-llm-associate/", code="NCA-GENL",
          price="$125", duration="60 min", fmt="Online proctored",
          focus="LLM fundamentals, prompting, data, and NVIDIA's GenAI tools.",
          fit="Entry level before NCP-AAI.", notes="Details from third-party guides."),
]
