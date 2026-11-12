"""Claude Academy (academy.claude.com) course catalog, curated for learning to build Claude agents.

Formerly "Anthropic Academy" on anthropic.skilljar.com; renamed and moved to academy.claude.com on 2026-08-20.
All courses are free. Titles, durations, lesson counts and lesson outlines were copied from the course pages
on CHECKED_ON. Re-check the site when this goes stale: courses get added and reworked.
"""

from __future__ import annotations

BASE_URL = "https://academy.claude.com"
CHECKED_ON = "2026-11-12"

# Track ids
AGENTS = "agents"          # the recommended order for building Claude agents
PRODUCTS = "products"      # using Claude, Cowork and Tag
FLUENCY = "fluency"        # AI Fluency and mental models
CLOUD = "cloud"            # Claude on Bedrock / Vertex
ORG = "org"                # rollout and team adoption

GROUPS = [
    {"id": AGENTS, "title": "Agent builder track",
     "summary": "The courses that teach you to build, extend and ship Claude agents, in the order to take them."},
    {"id": PRODUCTS, "title": "Using Claude's products",
     "summary": "Claude, Cowork and Claude Tag (Slack) as a user. Good context, not required for building agents."},
    {"id": FLUENCY, "title": "AI fluency and mental models",
     "summary": "How LLMs work, what they can't do, and how to work with them. Model-agnostic."},
    {"id": CLOUD, "title": "Claude on cloud platforms",
     "summary": "The API course again, taught on Amazon Bedrock or Google Cloud Vertex AI."},
    {"id": ORG, "title": "Rolling Claude out to a team",
     "summary": "Enterprise rollout and team adoption decisions."},
]


def _c(slug, title, group, hours, lessons, quizzes, badge, summary, *, order=None, level="", why="",
       outline=None, prereqs=""):
    return {
        "slug": slug, "title": title, "group": group, "order": order, "hours": hours, "lessons": lessons,
        "quizzes": quizzes, "badge": badge, "level": level, "summary": summary, "why": why, "prereqs": prereqs,
        "outline": outline or [], "url": f"{BASE_URL}/courses/{slug}",
    }


# outline = list of (section title, [lesson titles]); empty when not captured.
COURSES = [
    # ------------------------------------------------------------------ agent builder track (in order)
    _c("claude-platform-101", "Claude Platform 101", AGENTS, 1.5, 13, 1, True,
       "Building on the Claude Platform from your first API call to a production agent. No prior LLM-building "
       "experience assumed.",
       order=1, level="Beginner",
       why="The shortest map of the whole platform: the agent loop, tool use, thinking, built-in tools, skills, "
           "MCP, context management and managed agents. Take it first so every later course slots into place.",
       outline=[("Course", ["What is the Claude Platform?", "Your first API call", "Choosing the right model",
                            "The agent loop explained", "What is tool use?", "What is thinking?", "Built-in tools",
                            "Skills", "MCP", "Context management", "What are managed agents?",
                            "Building your first managed agent", "Building with Claude Code"])]),
    _c("building-with-the-claude-api", "Building with the Claude API", AGENTS, 9, 67, 8, True,
       "The full developer course: prompting, prompt evals, tool use, RAG and agentic search, Claude features, "
       "MCP, Claude Code and computer use, and agent/workflow patterns.",
       order=2, level="Intermediate", prereqs="Python, basic JSON, a Claude Console API key",
       why="The core course. Sections 4 (tool use) and 9 (agents and workflows: chaining, routing, "
           "parallelization, workflows vs agents) are the heart of agent design. Do the code, not just the videos.",
       outline=[
           ("Accessing Claude with the API", ["Accessing the API", "Getting an API key", "Making a request",
                                              "Multi-turn conversations", "System prompts", "Temperature",
                                              "Response streaming", "Structured data"]),
           ("Prompt evaluation", ["Prompt evaluation", "A typical eval workflow", "Generating test datasets",
                                  "Running the eval", "Model based grading", "Code based grading"]),
           ("Prompt engineering techniques", ["Prompt engineering", "Being clear and direct", "Being specific",
                                              "Structure with XML tags", "Providing examples"]),
           ("Tool use with Claude", ["Introducing tool use", "Project overview", "Tool functions", "Tool schemas",
                                     "Handling message blocks", "Sending tool results",
                                     "Multi-turn conversations with tools", "Implementing multiple turns",
                                     "Using multiple tools", "Fine grained tool calling", "The text edit tool",
                                     "The web search tool"]),
           ("RAG and agentic search", ["Introducing Retrieval Augmented Generation", "Text chunking strategies",
                                       "Text embeddings", "The full RAG flow", "Implementing the RAG flow",
                                       "BM25 lexical search", "A multi-index RAG pipeline"]),
           ("Features of Claude", ["Extended thinking", "Image support", "PDF support", "Citations",
                                   "Prompt caching", "Rules of prompt caching", "Prompt caching in action",
                                   "Code execution and the Files API"]),
           ("Model Context Protocol", ["Introducing MCP", "MCP clients", "Project setup", "Defining tools with MCP",
                                       "The server inspector", "Implementing a client", "Defining resources",
                                       "Accessing resources", "Defining prompts", "Prompts in the client"]),
           ("Anthropic apps: Claude Code and computer use", ["Anthropic apps: Claude Code and computer use",
                                                             "Claude Code setup", "Claude Code in action",
                                                             "Adding MCP servers to Claude Code"]),
           ("Agents and workflows", ["Agents and workflows", "Parallelization workflows", "Chaining workflows",
                                     "Routing workflows", "Agents and tools", "Environment inspection",
                                     "Workflows vs agents"]),
       ]),
    _c("tool-use-with-the-messages-api", "Tool use with the Messages API", AGENTS, 1.5, 9, 1, True,
       "The reliability, latency and cost problems that show up once basic tool use works, told through one "
       "consultancy's fixes. Python SDK.",
       order=3, level="Intermediate", prereqs="Basic tool use (the API course), a Claude Console API key",
       why="Production tool design: tools Claude actually picks, strict tool use, parallel and streamed tool calls, "
           "server tools (code execution, web search), computer use, and cutting the cost of tool-heavy agents.",
       outline=[("Course", ["Creating tools that Claude picks", "Strict tool use: stop rejecting your own calls",
                            "Parallel tool calling: cut the latency", "Streaming tool calls: no more frozen spinners",
                            "Code execution: Claude runs the code it writes", "Web search: answers from the sites you trust",
                            "Computer use: automate desktop software with no API",
                            "Cut the cost of tool-heavy workflows", "Start fixing your own tools"])]),
    _c("introduction-to-model-context-protocol", "Introduction to Model Context Protocol", AGENTS, 1, 10, 1, True,
       "Build MCP servers and clients from scratch with the Python SDK: tools, resources and prompts, ending in a "
       "document-management project.",
       order=4, level="Intermediate", prereqs="Python",
       why="MCP is how agents get tools and data from outside. Overlaps the MCP section of the API course; "
           "skim the parts you already did and build the project.",
       outline=[("Course", ["Introducing MCP", "MCP clients", "Defining tools with MCP", "The server inspector",
                            "Implementing a client", "Defining resources", "Accessing resources",
                            "Defining prompts", "Prompts in the client", "MCP review"])]),
    _c("model-context-protocol-advanced-topics", "Model Context Protocol: Advanced topics", AGENTS, 1.5, 11, 1, True,
       "Sampling, notifications and roots, plus the JSON message types and the STDIO and StreamableHTTP transports. "
       "For engineers building production MCP servers.",
       order=5, level="Advanced", prereqs="Introduction to Model Context Protocol",
       why="Architect-level MCP: how servers ask the client's model to reason (sampling), progress and logging, "
           "filesystem scoping (roots), and stateful vs stateless HTTP transports for scaling.",
       outline=[("Core MCP features", ["Sampling", "Sampling walkthrough", "Log and progress notifications",
                                       "Notifications walkthrough", "Roots", "Roots walkthrough"]),
                ("Transports and communication", ["JSON message types", "The STDIO transport",
                                                  "The StreamableHTTP transport", "StreamableHTTP in depth",
                                                  "State and the StreamableHTTP transport"])]),
    _c("claude-code-101", "Claude Code 101", AGENTS, 1.5, 12, 1, True,
       "What Claude Code is, how it works, and the core daily workflows. For developers new to AI coding agents.",
       order=6, level="Beginner",
       why="Claude Code is a production agent harness you can study from the inside: the agent loop, context "
           "management, CLAUDE.md memory, subagents, skills, MCP and hooks.",
       outline=[("What is Claude Code?", ["What is Claude Code?", "How Claude Code works"]),
                ("Your first prompt", ["Installing Claude Code", "Your first prompt"]),
                ("Daily workflows", ["The explore, plan, code, commit workflow", "Context management", "Code review"]),
                ("Customizing Claude Code", ["The CLAUDE.md file", "Subagents", "Skills", "MCP", "Hooks"])]),
    _c("claude-code-in-action", "Claude Code in action", AGENTS, 1, 9, 1, True,
       "Running longer, less supervised Claude Code sessions: steering, instructions and rules, permission modes, "
       "hooks, scheduled and headless runs, GitHub Actions, verifying unattended work, plugins.",
       order=7, level="Intermediate", prereqs="Claude Code 101",
       why="Autonomy with guardrails: permission modes, hooks as control points, headless and CI runs, and how to "
           "verify work no human watched. The same questions an agent architect has to answer.",
       outline=[("Steer the work", ["Steering long sessions"]),
                ("Configure Claude", ["A CLAUDE.md that follows", "Verification skills", "Permission modes", "Hooks"]),
                ("Automate repeat work", ["Scheduled tasks and headless", "GitHub Actions and Code Review"]),
                ("Verify and share", ["Trust it: verifying unsupervised runs", "Plugins"])]),
    _c("introduction-to-subagents", "Introduction to subagents", AGENTS, 0.75, 4, 0, False,
       "Decompose complex tasks across parallel Claude subagents and orchestrate them deterministically.",
       order=8, level="Intermediate", prereqs="Claude Code 101",
       why="Multi-agent orchestration in practice: when to split work, how to keep each agent's context clean, "
           "and how to design subagents that return what the orchestrator needs.",
       outline=[("Course", ["What are subagents?", "Creating a subagent", "Designing effective subagents",
                            "Using subagents effectively"])]),
    _c("introduction-to-agent-skills", "Introduction to agent skills", AGENTS, 1, 6, 0, False,
       "Build, configure and share Skills: reusable markdown instructions Claude applies automatically to matching "
       "tasks.",
       order=9, level="Intermediate", prereqs="Claude Code 101",
       why="Skills are progressive-disclosure context for agents. Learn how they differ from CLAUDE.md, subagents, "
           "hooks and MCP, and how to package and share them.",
       outline=[("Course", ["What are skills?", "Creating your first skill", "Configuration and multi-file skills",
                            "Skills vs. other Claude Code features", "Sharing skills", "Troubleshooting skills"])]),
    _c("introduction-to-evals", "Introduction to evals", AGENTS, 1, 4, 1, True,
       "Build a small eval on your own data, choose a model by accuracy then cost, fix the prompt before upgrading "
       "the model, and keep checking quality after launch.",
       order=10, level="Intermediate",
       why="Evals are what separate an agent demo from an agent product, and a staple of architect interviews: "
           "model selection, minimum viable evals, CI and batch evals, drift.",
       outline=[("Course", ["When to use what model", "Build a minimum viable eval",
                            "Iterate the prompt before you upgrade the model",
                            "Evals in production: CI, batch, and drift"])]),
    _c("ai-native-sdlc-playbook", "The AI-native SDLC playbook", AGENTS, 1, 14, 0, False,
       "Twelve plays for using Claude at each stage of the software lifecycle, for engineering, platform and "
       "security leads whose teams already use Claude Code. About an hour of reading.",
       order=11, level="Advanced",
       why="The organisational layer an architect owns: plan mode as default, skills as institutional knowledge, "
           "continuous evals in CI, hooks as approval gates, and closing the loop on metrics.",
       outline=[("Introduction", ["What changes and where to start"]),
                ("Stage 1: Plan", ["Capture as intent.md"]),
                ("Stage 2: Design", ["Requirements and design"]),
                ("Stage 3: Build", ["Claude Code plan mode as the default starting point", "The CLAUDE.md",
                                    "Skills as institutional knowledge", "Parallel sessions and subagents"]),
                ("Stage 4: Test", ["Give Claude a feedback loop", "Continuous evals in CI"]),
                ("Stage 5: Deploy", ["AI in the PR review loop", "Hooks as approval gates",
                                     "CI/CD integration and deployment"]),
                ("Stage 6: Maintain", ["Closing the loop on metrics"]),
                ("Closing", ["Closing thoughts and resources"])]),

    # ------------------------------------------------------------------ products
    _c("claude-101", "Claude 101", PRODUCTS, 2.5, 13, 1, True,
       "Everyday use of Claude: first conversation, effective prompting, Projects, artifacts, skills and connected "
       "tools.", level="Beginner"),
    _c("introduction-to-claude-cowork", "Introduction to Claude Cowork", PRODUCTS, 2.5, 14, 1, True,
       "Delegate multi-step work to Claude in Cowork: workspaces, context, task loops, and plugins for research, "
       "documents and browser tasks.", level="Beginner"),
    _c("introduction-to-claude-tag", "Introduction to Claude Tag", PRODUCTS, 2.5, 11, 1, True,
       "Tagging Claude into Slack for team work.", level="Beginner"),

    # ------------------------------------------------------------------ fluency
    _c("building-effective-human-agent-teams", "Building effective human-agent teams (beta)", FLUENCY, 0.75, 5, 1,
       True, "Moving from single-player to multiplayer AI, and preparing a team for the shift.",
       why="Short and relevant to agent design: where humans sit in the loop when agents join a team."),
    _c("ai-capabilities-and-limitations", "AI capabilities and limitations", FLUENCY, 3.5, 13, 1, True,
       "An accurate mental model of what LLMs can and can't do: next-token prediction, knowledge, working memory, "
       "steerability, context limits."),
    _c("ai-fluency-framework-foundations", "AI Fluency: Framework and foundations", FLUENCY, 4, 14, 1, True,
       "Collaborating with AI effectively, efficiently, ethically and safely, using the 4D framework: Delegation, "
       "Description, Discernment and Diligence."),
    _c("ai-fluency-for-builders", "AI Fluency for builders", FLUENCY, None, 9, 1, True,
       "AI fluency for owning a problem through to a shipped solution."),
    _c("ai-fluency-for-creative-work", "AI Fluency for creative work", FLUENCY, None, 8, 1, True,
       "Deliberate AI decisions in creative practice while protecting original work."),
    _c("ai-fluency-for-educators", "AI Fluency for educators", FLUENCY, None, 4, 1, True,
       "Applying AI fluency to teaching practice and institutional strategy."),
    _c("ai-fluency-for-k-12-educators", "AI Fluency for pK-12 educators", FLUENCY, None, 10, 1, True,
       "AI fluency materials for pK-12 educators."),
    _c("ai-fluency-for-pk-12-train-the-trainer", "AI Fluency for pK-12: Train the trainer", FLUENCY, None, 4, 0,
       False, "Train-the-trainer version of the pK-12 course."),
    _c("teaching-ai-fluency", "AI Fluency for facilitators", FLUENCY, None, 7, 1, True,
       "Teaching and assessing AI fluency in instructor-led settings."),
    _c("ai-fluency-for-nonprofits", "AI Fluency for nonprofits", FLUENCY, None, 9, 1, True,
       "Improving nonprofit impact and efficiency with AI while staying true to mission."),
    _c("ai-fluency-for-small-businesses", "AI Fluency for small businesses", FLUENCY, None, 8, 1, True,
       "Improving small-business impact and efficiency with AI."),
    _c("ai-fluency-for-students", "AI Fluency for students", FLUENCY, None, 5, 1, True,
       "AI fluency for learning, career planning and academic success."),

    # ------------------------------------------------------------------ cloud
    _c("claude-with-amazon-bedrock", "Claude with Amazon Bedrock", CLOUD, 8, 65, 8, True,
       "The full API course on Amazon Bedrock (originally an AWS accreditation training).",
       why="Take instead of the API course if you'll deploy agents on AWS."),
    _c("claude-with-google-cloud-s-vertex-ai", "Claude on Google Cloud", CLOUD, 8.5, 66, 9, True,
       "The full API course on Google Cloud Vertex AI.",
       why="Take instead of the API course if you'll deploy agents on Google Cloud."),

    # ------------------------------------------------------------------ org
    _c("deploying-claude-enterprise-with-confidence",
       "Deploying Claude Enterprise with confidence: the five decisions that shape your rollout", ORG, 2.5, 14, 1,
       True, "Structure and identity, access, governance, spend and visibility, recorded as a rollout plan."),
]

BY_SLUG = {c["slug"]: c for c in COURSES}
AGENT_TRACK = sorted((c for c in COURSES if c["group"] == AGENTS), key=lambda c: c["order"])

# The study path built from the agent track (see api/claude.py).
PATH_SLUG = "claude-academy-agents"
PATH_TITLE = "Claude Academy: Building Claude agents"
PATH_SUMMARY = ("Anthropic's free Claude Academy courses for building agents, in order: platform basics, the API, "
                "production tool use, MCP, Claude Code, subagents, skills, evals and the AI-native SDLC. "
                "Each lesson links to its course on academy.claude.com.")
