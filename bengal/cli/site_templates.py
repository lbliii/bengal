"""Site templates for the 'bengal new site' command."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class PageTemplate:
    """Represents a page template with path and content."""

    path: str  # Relative path from content directory
    content: str


@dataclass
class SiteTemplate:
    """Represents a complete site template."""

    name: str
    description: str
    pages: list[PageTemplate]
    additional_dirs: list[str]  # Additional directories to create


def get_current_date() -> str:
    """Get current date in ISO format."""
    return datetime.now().strftime("%Y-%m-%d")


# ============================================================================
# BLOG TEMPLATE
# ============================================================================

BLOG_PAGES = [
    PageTemplate(
        path="index.md",
        content="""---
title: My Blog
description: Welcome to my blog where I share thoughts and ideas
layout: home
---

# Welcome to My Blog

This is your new Bengal blog! I write about technology, life, and everything in between.

## Recent Posts

Check out my latest posts below or browse by [tags](/tags) and [categories](/categories).
""",
    ),
    PageTemplate(
        path="about.md",
        content="""---
title: About
description: Learn more about me
---

# About Me

Hi! I'm a blogger passionate about sharing knowledge and experiences.

## What I Write About

- Technology and programming
- Personal development
- Life lessons and reflections

## Get in Touch

Feel free to reach out via email or social media.
""",
    ),
    PageTemplate(
        path="posts/first-post.md",
        content=f"""---
title: My First Blog Post
date: {get_current_date()}
tags: [welcome, introduction]
category: meta
description: Welcome to my new blog built with Bengal SSG
---

# My First Blog Post

Welcome to my blog! This is my first post, and I'm excited to start sharing my thoughts and ideas.

## Why I Started This Blog

I wanted a place to document my journey and share what I learn along the way.

## What to Expect

- Regular posts about topics I'm passionate about
- Tutorials and how-to guides
- Personal reflections and experiences

Stay tuned for more content!
""",
    ),
    PageTemplate(
        path="posts/second-post.md",
        content=f"""---
title: Getting Started with Bengal SSG
date: {get_current_date()}
tags: [bengal, tutorial, ssg]
category: technology
description: Learn how to build fast static sites with Bengal
---

# Getting Started with Bengal SSG

Bengal is a powerful static site generator that makes building websites easy and fun.

## Key Features

1. **Fast Builds** - Parallel processing for quick build times
2. **Asset Optimization** - Automatic minification and fingerprinting
3. **SEO Friendly** - Built-in sitemap and RSS generation
4. **Developer Experience** - Live reload and hot module replacement

## Next Steps

Try editing this post or creating a new one with:

```bash
bengal new page my-new-post --section posts
```

Then build and serve your site:

```bash
bengal serve
```
""",
    ),
]

BLOG_TEMPLATE = SiteTemplate(
    name="blog",
    description="A blog with posts, tags, and categories",
    pages=BLOG_PAGES,
    additional_dirs=["content/posts", "content/drafts"],
)


# ============================================================================
# DOCS TEMPLATE
# ============================================================================

DOCS_PAGES = [
    PageTemplate(
        path="index.md",
        content="""---
title: Documentation
description: Complete documentation for your project
layout: docs
---

# Documentation

Welcome to the documentation! This site contains comprehensive guides and references.

## Getting Started

New here? Start with our [Quick Start Guide](getting-started/quickstart).

## Sections

- **Getting Started** - Installation and basic usage
- **Guides** - Step-by-step tutorials
- **API Reference** - Detailed API documentation
- **Advanced** - Advanced topics and best practices
""",
    ),
    PageTemplate(
        path="getting-started/index.md",
        content="""---
title: Getting Started
description: Get up and running quickly
section: getting-started
order: 1
---

# Getting Started

This section will help you get started quickly.

## Prerequisites

Before you begin, ensure you have:

- Python 3.8 or higher
- Basic command line knowledge

## Next Steps

1. [Installation](installation) - Install the software
2. [Quick Start](quickstart) - Your first project
3. [Configuration](configuration) - Configure your setup
""",
    ),
    PageTemplate(
        path="getting-started/installation.md",
        content="""---
title: Installation
description: How to install
section: getting-started
order: 2
---

# Installation

Learn how to install and set up your environment.

## Using pip

```bash
pip install your-package
```

## Using uv

```bash
uv pip install your-package
```

## Verify Installation

Check that everything is installed correctly:

```bash
your-command --version
```

## Next Steps

Continue with the [Quick Start Guide](quickstart).
""",
    ),
    PageTemplate(
        path="getting-started/quickstart.md",
        content="""---
title: Quick Start
description: Your first project in 5 minutes
section: getting-started
order: 3
---

# Quick Start

Get your first project running in just a few minutes.

## Step 1: Create a New Project

```bash
your-command new my-project
cd my-project
```

## Step 2: Start Development Server

```bash
your-command serve
```

## Step 3: Build for Production

```bash
your-command build
```

## What's Next?

- Explore the [Guides](../guides/) section
- Check out the [API Reference](../api/)
- Learn [Advanced Topics](../advanced/)
""",
    ),
    PageTemplate(
        path="guides/index.md",
        content="""---
title: Guides
description: Step-by-step tutorials
section: guides
order: 1
---

# Guides

Practical guides to help you accomplish specific tasks.

## Available Guides

- [Creating Your First Page](first-page)
- [Working with Assets](assets)
- [Customizing Themes](themes)
- [Deployment](deployment)

Each guide provides detailed, step-by-step instructions.
""",
    ),
    PageTemplate(
        path="api/index.md",
        content="""---
title: API Reference
description: Complete API documentation
section: api
---

# API Reference

Complete reference documentation for all APIs.

## Core APIs

- **Configuration** - Site configuration options
- **Content** - Working with content
- **Templates** - Template system reference
- **Assets** - Asset pipeline APIs

## Examples

Check each section for detailed examples and usage patterns.
""",
    ),
]

DOCS_TEMPLATE = SiteTemplate(
    name="docs",
    description="Technical documentation with navigation and sections",
    pages=DOCS_PAGES,
    additional_dirs=[
        "content/getting-started",
        "content/guides",
        "content/api",
        "content/advanced",
    ],
)


# ============================================================================
# PORTFOLIO TEMPLATE
# ============================================================================

PORTFOLIO_PAGES = [
    PageTemplate(
        path="index.md",
        content="""---
title: Portfolio
description: Welcome to my portfolio
layout: home
---

# Hi, I'm [Your Name]

I'm a [Your Profession] passionate about creating amazing things.

## Featured Projects

Check out some of my recent work below.

---

## About Me

I specialize in [your specialties] and love solving complex problems.

[View All Projects](/projects) | [About Me](/about) | [Contact](/contact)
""",
    ),
    PageTemplate(
        path="about.md",
        content="""---
title: About
description: Learn more about me
---

# About Me

I'm a creative professional with a passion for [your passion].

## Skills

- **Frontend**: React, Vue, CSS
- **Backend**: Python, Node.js
- **Tools**: Git, Docker, AWS

## Experience

### Current Position
**Company Name** - Role (2023 - Present)

- Achievement or responsibility
- Another achievement
- Key project

### Previous Position
**Previous Company** - Role (2021 - 2023)

- Key accomplishments
- Technologies used

## Education

**University Name**
Bachelor's Degree in Computer Science (2017-2021)

## Let's Connect

- Email: your.email@example.com
- GitHub: github.com/yourusername
- LinkedIn: linkedin.com/in/yourprofile
""",
    ),
    PageTemplate(
        path="projects/index.md",
        content="""---
title: Projects
description: My portfolio of work
---

# Projects

Here's a collection of projects I've worked on.

## Featured Work

Browse through my projects to see examples of my work and the technologies I use.
""",
    ),
    PageTemplate(
        path="projects/project-1.md",
        content=f"""---
title: E-Commerce Platform
date: {get_current_date()}
tags: [web, react, node]
featured: true
image: /assets/images/project1.jpg
demo_url: https://example.com
github_url: https://github.com/yourusername/project
---

# E-Commerce Platform

A full-featured e-commerce platform built with modern web technologies.

## Overview

This project demonstrates my ability to build scalable web applications with complex features.

## Technologies Used

- **Frontend**: React, TypeScript, Tailwind CSS
- **Backend**: Node.js, Express, PostgreSQL
- **Infrastructure**: AWS, Docker, Kubernetes

## Key Features

- User authentication and authorization
- Product catalog with search and filters
- Shopping cart and checkout flow
- Order management system
- Admin dashboard

## Challenges & Solutions

One of the main challenges was optimizing the search functionality for large product catalogs...

## Results

- 100k+ monthly active users
- 99.9% uptime
- Sub-second page load times

[View Live Demo](https://example.com) | [View on GitHub](https://github.com/yourusername/project)
""",
    ),
    PageTemplate(
        path="projects/project-2.md",
        content=f"""---
title: Mobile Fitness App
date: {get_current_date()}
tags: [mobile, react-native, health]
featured: true
image: /assets/images/project2.jpg
---

# Mobile Fitness App

A cross-platform mobile app for tracking workouts and nutrition.

## Overview

Built with React Native for iOS and Android, this app helps users track their fitness journey.

## Technologies

- React Native
- TypeScript
- Firebase
- Redux

## Features

- Workout tracking and history
- Nutrition logging
- Progress charts and analytics
- Social features and challenges
- Wearable device integration

## Impact

Downloaded by 50,000+ users with a 4.8-star average rating.
""",
    ),
    PageTemplate(
        path="contact.md",
        content="""---
title: Contact
description: Get in touch
---

# Let's Work Together

I'm always interested in hearing about new projects and opportunities.

## Get in Touch

- **Email**: your.email@example.com
- **GitHub**: [github.com/yourusername](https://github.com/yourusername)
- **LinkedIn**: [linkedin.com/in/yourprofile](https://linkedin.com/in/yourprofile)
- **Twitter**: [@yourusername](https://twitter.com/yourusername)

## Availability

I'm currently available for:

- Freelance projects
- Contract work
- Consulting opportunities
- Open source collaboration

Feel free to reach out via email or connect on social media!
""",
    ),
]

PORTFOLIO_TEMPLATE = SiteTemplate(
    name="portfolio",
    description="Portfolio site with projects showcase",
    pages=PORTFOLIO_PAGES,
    additional_dirs=["content/projects"],
)


# ============================================================================
# RESUME TEMPLATE
# ============================================================================

RESUME_PAGES = [
    PageTemplate(
        path="_index.md",
        content="""---
title: Resume
type: resume
template: resume/single.html
description: Professional resume and CV
---

This homepage uses the resume template to display your CV.
All resume data comes from `data/resume.yaml`.
""",
    ),
]

# Resume data file (separate from page content)
RESUME_DATA = {
    "resume.yaml": """# Resume Data
# This file contains all your resume information in a structured format.
# Edit this file to update your resume content.

name: Your Full Name
headline: Software Engineer | Full Stack Developer | Problem Solver

# Contact Information
contact:
  email: your.email@example.com
  phone: "+1 (555) 123-4567"
  location: "San Francisco, CA"
  website: https://yourportfolio.com
  linkedin: https://linkedin.com/in/yourprofile
  github: https://github.com/yourusername

# Professional Summary
summary: |
  Experienced software engineer with 6+ years of building scalable web applications and leading cross-functional teams.
  Proven track record of delivering high-quality solutions that drive business value. Passionate about clean code,
  user experience, and mentoring junior developers.

# Work Experience
experience:
  - title: Senior Software Engineer
    company: Tech Company Inc.
    location: San Francisco, CA
    start_date: "Jan 2022"
    end_date: Present
    description: Leading development of cloud-native applications serving 100k+ users
    highlights:
      - Architected and implemented microservices infrastructure, reducing deployment time by 60%
      - Led team of 5 engineers in developing customer-facing dashboard with React and TypeScript
      - Improved API response times by 40% through database optimization and caching strategies
      - Mentored 3 junior developers, helping them advance to mid-level positions
      - Established CI/CD pipelines using GitHub Actions and automated testing practices
    technologies:
      - Python
      - React
      - TypeScript
      - AWS
      - Docker
      - PostgreSQL
      - Redis

  - title: Software Engineer
    company: Digital Solutions Co.
    location: San Francisco, CA
    start_date: "Jun 2019"
    end_date: "Dec 2021"
    description: Developed and maintained customer-facing web applications
    highlights:
      - Built responsive web applications using modern JavaScript frameworks
      - Collaborated with design team to implement pixel-perfect UIs
      - Optimized database queries, improving page load times by 35%
      - Participated in code reviews and contributed to technical documentation
      - Implemented A/B testing framework that increased conversion by 15%
    technologies:
      - JavaScript
      - Vue.js
      - Node.js
      - MongoDB
      - Express

  - title: Junior Developer
    company: StartupXYZ
    location: Mountain View, CA
    start_date: "Jul 2017"
    end_date: "May 2019"
    description: Built RESTful APIs and contributed to full-stack development
    highlights:
      - Developed RESTful APIs for mobile and web applications
      - Fixed bugs and implemented new features across the stack
      - Wrote unit and integration tests achieving 85% code coverage
      - Contributed to open source projects and internal tooling
    technologies:
      - Python
      - Flask
      - PostgreSQL
      - jQuery

# Education
education:
  - degree: Bachelor of Science in Computer Science
    institution: University of California
    location: Berkeley, CA
    start_date: "2013"
    end_date: "2017"
    gpa: "3.8/4.0"
    honors:
      - Dean's List - All semesters
      - Graduated with Honors
      - Computer Science Department Award for Outstanding Achievement
    coursework:
      - Data Structures & Algorithms
      - Database Systems
      - Web Development
      - Software Engineering
      - Machine Learning

# Skills
skills:
  - category: Programming Languages
    items:
      - Python
      - JavaScript
      - TypeScript
      - SQL
      - Go
      - HTML/CSS

  - category: Frameworks & Libraries
    items:
      - React
      - Vue.js
      - Django
      - FastAPI
      - Node.js
      - Express
      - Tailwind CSS

  - category: Databases & Storage
    items:
      - PostgreSQL
      - MongoDB
      - Redis
      - MySQL
      - Elasticsearch

  - category: Cloud & DevOps
    items:
      - AWS (EC2, S3, Lambda, RDS)
      - Docker
      - Kubernetes
      - GitHub Actions
      - Terraform
      - CI/CD

  - category: Tools & Practices
    items:
      - Git
      - Agile/Scrum
      - TDD/BDD
      - REST APIs
      - GraphQL
      - Microservices

# Projects
projects:
  - name: Open Source Static Site Generator
    role: Core Contributor
    date: "2023 - Present"
    description: Contributing to a modern Python-based static site generator
    highlights:
      - Implemented plugin system for extensibility
      - Added support for incremental builds
      - Improved documentation and wrote tutorials
      - Project has 500+ GitHub stars and growing community
    technologies:
      - Python
      - Jinja2
      - Markdown
    github: https://github.com/yourusername/project
    demo: https://project-demo.com

  - name: E-Commerce Platform
    role: Full Stack Developer
    date: "2021"
    description: Built a full-featured e-commerce platform as a side project
    highlights:
      - Implemented shopping cart, checkout, and payment processing
      - Created admin dashboard for inventory management
      - Deployed to AWS with auto-scaling and load balancing
    technologies:
      - React
      - Node.js
      - PostgreSQL
      - Stripe API
      - AWS
    github: https://github.com/yourusername/ecommerce

  - name: Real-time Chat Application
    role: Personal Project
    date: "2020"
    description: Real-time chat app with WebSocket support
    highlights:
      - Built WebSocket server for real-time messaging
      - Implemented user authentication and authorization
      - Added file sharing and emoji support
    technologies:
      - Node.js
      - Socket.io
      - MongoDB
      - React

# Certifications
certifications:
  - name: AWS Certified Solutions Architect - Associate
    issuer: Amazon Web Services
    date: "2023"
    url: https://aws.amazon.com/certification/

  - name: Certified Kubernetes Administrator (CKA)
    issuer: Cloud Native Computing Foundation
    date: "2022"
    url: https://www.cncf.io/certification/cka/

  - name: Professional Scrum Master I (PSM I)
    issuer: Scrum.org
    date: "2021"

# Awards
awards:
  - name: Employee of the Quarter
    issuer: Tech Company Inc.
    date: Q3 2023
    description: Recognized for outstanding performance and leadership in Q3 2023

  - name: Hackathon Winner
    issuer: Tech Company Inc.
    date: "2022"
    description: First place in company internal hackathon with AI-powered code review tool

  - name: Best Technical Presentation
    issuer: Digital Solutions Co.
    date: "2021"
    description: Awarded for presentation on modern JavaScript architecture patterns

# Languages
languages:
  - language: English
    proficiency: Native

  - language: Spanish
    proficiency: Professional Working Proficiency

  - language: French
    proficiency: Basic

# Volunteer Experience
volunteer:
  - role: Coding Mentor
    organization: Code.org
    start_date: "2020"
    end_date: Present
    description: Mentoring students in web development and computer science fundamentals

  - role: Tech Workshop Instructor
    organization: Local Community Center
    start_date: "2019"
    end_date: "2021"
    description: Taught intro to programming workshops for underrepresented communities
"""
}

RESUME_TEMPLATE = SiteTemplate(
    name="resume",
    description="Professional resume/CV site with structured data",
    pages=RESUME_PAGES,
    additional_dirs=["data"],
)


# ============================================================================
# LANDING PAGE TEMPLATE
# ============================================================================

LANDING_PAGES = [
    PageTemplate(
        path="index.md",
        content="""---
title: Welcome to Our Product
description: The best solution for your needs
layout: landing
---

# Transform Your Workflow Today

The all-in-one solution that helps you work smarter, not harder.

[Get Started](#features) | [Learn More](#about)

---

## Features

### ⚡ Lightning Fast
Built for speed and performance. Get things done in seconds, not minutes.

### 🔒 Secure & Private
Your data is encrypted and protected with industry-standard security.

### 🎨 Beautiful Design
Clean, modern interface that's a joy to use every day.

### 🚀 Easy to Use
Get started in minutes with our intuitive interface and helpful guides.

### 📊 Powerful Analytics
Track your progress with detailed insights and reports.

### 🤝 Team Collaboration
Work together seamlessly with built-in collaboration tools.

---

## Why Choose Us?

We're not just another tool - we're your partner in success.

### Trusted by Thousands
Join 10,000+ happy customers who have transformed their workflow.

### Award Winning
Recognized as the best solution in our category by industry experts.

### 24/7 Support
Our dedicated team is here to help whenever you need us.

---

## Pricing

### Free
**$0/month**
- Up to 5 users
- Basic features
- Community support
- 1GB storage

[Start Free](#)

### Pro
**$29/month**
- Unlimited users
- All features
- Priority support
- 100GB storage
- Advanced analytics

[Start Trial](#)

### Enterprise
**Custom pricing**
- Custom solutions
- Dedicated support
- Unlimited storage
- SLA guarantee
- On-premise option

[Contact Sales](#)

---

## What Our Customers Say

> "This product completely transformed how we work. We're 10x more productive now!"
>
> — Jane Doe, CEO at Company

> "The best investment we made this year. Highly recommended!"
>
> — John Smith, Founder at Startup

> "Simple, powerful, and elegant. Everything a tool should be."
>
> — Sarah Johnson, Product Manager

---

## Ready to Get Started?

Join thousands of satisfied customers today.

[Start Free Trial](#) | [Schedule Demo](#) | [Contact Sales](#)

---

## Frequently Asked Questions

### How does it work?
Our platform uses cutting-edge technology to deliver results quickly and reliably.

### Is my data safe?
Yes! We use bank-level encryption and never share your data with third parties.

### Can I cancel anytime?
Absolutely. No long-term contracts or cancellation fees.

### Do you offer refunds?
Yes, we offer a 30-day money-back guarantee for all paid plans.

---

[Terms of Service](/terms) | [Privacy Policy](/privacy) | [Contact Us](/contact)
""",
    ),
    PageTemplate(
        path="privacy.md",
        content=f"""---
title: Privacy Policy
description: How we handle your data
---

# Privacy Policy

*Last updated: {get_current_date()}*

Your privacy is important to us. This policy explains how we collect, use, and protect your information.

## Information We Collect

We collect information you provide directly to us, including:

- Name and email address
- Account credentials
- Usage data and preferences

## How We Use Your Information

We use the information we collect to:

- Provide and improve our services
- Communicate with you
- Ensure security and prevent fraud
- Comply with legal obligations

## Data Security

We implement appropriate security measures to protect your information against unauthorized access.

## Your Rights

You have the right to:

- Access your data
- Correct inaccuracies
- Request deletion
- Opt-out of communications

## Contact Us

If you have questions about this policy, please contact us at privacy@example.com.
""",
    ),
    PageTemplate(
        path="terms.md",
        content=f"""---
title: Terms of Service
description: Terms and conditions
---

# Terms of Service

*Last updated: {get_current_date()}*

Please read these terms carefully before using our service.

## Acceptance of Terms

By accessing and using this service, you accept and agree to be bound by these terms.

## Use License

Permission is granted to use this service for personal or commercial purposes subject to these terms.

## Limitations

You may not:

- Use the service for any illegal purpose
- Attempt to gain unauthorized access
- Interfere with the service's operation
- Violate any applicable laws or regulations

## Disclaimer

The service is provided "as is" without warranties of any kind.

## Limitation of Liability

We shall not be liable for any damages arising from the use of this service.

## Changes to Terms

We reserve the right to modify these terms at any time.

## Contact

For questions about these terms, contact us at legal@example.com.
""",
    ),
]

LANDING_TEMPLATE = SiteTemplate(
    name="landing",
    description="Landing page for products or services",
    pages=LANDING_PAGES,
    additional_dirs=[],
)


# ============================================================================
# DEFAULT TEMPLATE (current behavior)
# ============================================================================

DEFAULT_PAGES = [
    PageTemplate(
        path="index.md",
        content="""---
title: Welcome to Bengal
---

# Welcome to Bengal SSG

This is your new Bengal static site. Start editing this file to begin!

## Features

- Fast builds with parallel processing
- Modular architecture
- Asset optimization
- SEO friendly

## Next Steps

1. Edit `content/index.md` (this file)
2. Create new pages with `bengal new page <name>`
3. Build your site with `bengal build`
4. Preview with `bengal serve`
""",
    ),
]

DEFAULT_TEMPLATE = SiteTemplate(
    name="default",
    description="Basic site structure",
    pages=DEFAULT_PAGES,
    additional_dirs=[],
)


# ============================================================================
# TEMPLATE REGISTRY
# ============================================================================

TEMPLATES: dict[str, SiteTemplate] = {
    "default": DEFAULT_TEMPLATE,
    "blog": BLOG_TEMPLATE,
    "docs": DOCS_TEMPLATE,
    "portfolio": PORTFOLIO_TEMPLATE,
    "resume": RESUME_TEMPLATE,
    "landing": LANDING_TEMPLATE,
}


def get_template(name: str) -> SiteTemplate:
    """Get a site template by name."""
    return TEMPLATES.get(name, DEFAULT_TEMPLATE)


def list_templates() -> list[tuple[str, str]]:
    """List all available templates with descriptions."""
    return [(name, template.description) for name, template in TEMPLATES.items()]
