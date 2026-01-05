#!/usr/bin/env python3
"""Benchmark Rosettes state machine lexers vs Pygments.

Compares performance across all supported languages with realistic code samples.
"""

from __future__ import annotations

import gc
import statistics
import time
from collections.abc import Callable
from dataclasses import dataclass

# Rosettes (external package)
import rosettes

# Pygments
try:
    from pygments import highlight as pygments_highlight
    from pygments.formatters import HtmlFormatter as PygmentsHtmlFormatter
    from pygments.lexers import get_lexer_by_name as pygments_get_lexer

    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False
    print("⚠️  Pygments not installed, will only benchmark Rosettes")


# =============================================================================
# Sample code for each language
# =============================================================================

SAMPLES: dict[str, str] = {
    "python": '''
def fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number recursively."""
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


class Calculator:
    """A simple calculator with history tracking."""

    def __init__(self) -> None:
        self.history: list[str] = []

    def add(self, a: float, b: float) -> float:
        result = a + b
        self.history.append(f"{a} + {b} = {result}")
        return result

    @property
    def last_operation(self) -> str | None:
        return self.history[-1] if self.history else None


# F-string example
name = "World"
greeting = f"Hello, {name}! The answer is {fibonacci(10)}"
print(greeting)
''',
    "javascript": """
class EventEmitter {
  constructor() {
    this.events = new Map();
  }

  on(event, callback) {
    if (!this.events.has(event)) {
      this.events.set(event, []);
    }
    this.events.get(event).push(callback);
    return this;
  }

  emit(event, ...args) {
    const callbacks = this.events.get(event) || [];
    callbacks.forEach(cb => cb(...args));
    return this;
  }
}

const emitter = new EventEmitter();
emitter.on('data', (msg) => console.log(`Received: ${msg}`));
emitter.emit('data', 'Hello, World!');

// Arrow functions and destructuring
const users = [
  { name: 'Alice', age: 30 },
  { name: 'Bob', age: 25 },
];
const names = users.map(({ name }) => name);
""",
    "typescript": """
interface User {
  id: number;
  name: string;
  email: string;
  createdAt: Date;
}

type UserWithoutId = Omit<User, 'id'>;

class UserService {
  private users: Map<number, User> = new Map();
  private nextId = 1;

  async createUser(data: UserWithoutId): Promise<User> {
    const user: User = {
      id: this.nextId++,
      ...data,
    };
    this.users.set(user.id, user);
    return user;
  }

  async findById(id: number): Promise<User | undefined> {
    return this.users.get(id);
  }
}

const service = new UserService();
const user = await service.createUser({
  name: 'Alice',
  email: 'alice@example.com',
  createdAt: new Date(),
});
""",
    "rust": """
use std::collections::HashMap;
use std::sync::{Arc, Mutex};

#[derive(Debug, Clone)]
pub struct Config {
    pub host: String,
    pub port: u16,
    pub max_connections: usize,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            host: "localhost".to_string(),
            port: 8080,
            max_connections: 100,
        }
    }
}

pub async fn start_server(config: Config) -> Result<(), Box<dyn std::error::Error>> {
    let connections: Arc<Mutex<HashMap<u64, String>>> = Arc::new(Mutex::new(HashMap::new()));

    println!("Starting server on {}:{}", config.host, config.port);

    // Async loop would go here
    Ok(())
}

fn main() {
    let config = Config::default();
    println!("{:?}", config);
}
""",
    "go": """
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"sync"
	"time"
)

type Server struct {
	mu       sync.RWMutex
	handlers map[string]http.HandlerFunc
}

func NewServer() *Server {
	return &Server{
		handlers: make(map[string]http.HandlerFunc),
	}
}

func (s *Server) Handle(path string, handler http.HandlerFunc) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.handlers[path] = handler
}

func (s *Server) Start(ctx context.Context, addr string) error {
	srv := &http.Server{
		Addr:         addr,
		ReadTimeout:  5 * time.Second,
		WriteTimeout: 10 * time.Second,
	}

	go func() {
		<-ctx.Done()
		srv.Shutdown(context.Background())
	}()

	return srv.ListenAndServe()
}

func main() {
	server := NewServer()
	server.Handle("/api/health", func(w http.ResponseWriter, r *http.Request) {
		json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
	})
	fmt.Println("Server starting...")
}
""",
    "java": """
package com.example.service;

import java.util.*;
import java.util.concurrent.*;
import java.util.stream.*;

public class UserRepository {
    private final Map<Long, User> users = new ConcurrentHashMap<>();
    private final AtomicLong idGenerator = new AtomicLong(0);

    public User create(String name, String email) {
        long id = idGenerator.incrementAndGet();
        User user = new User(id, name, email);
        users.put(id, user);
        return user;
    }

    public Optional<User> findById(Long id) {
        return Optional.ofNullable(users.get(id));
    }

    public List<User> findByNameContaining(String pattern) {
        return users.values().stream()
            .filter(u -> u.getName().contains(pattern))
            .sorted(Comparator.comparing(User::getName))
            .collect(Collectors.toList());
    }
}

record User(Long id, String name, String email) {}
""",
    "sql": """
-- Create users table with constraints
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for faster lookups
CREATE INDEX idx_users_email ON users(email);

-- Insert sample data
INSERT INTO users (username, email) VALUES
    ('alice', 'alice@example.com'),
    ('bob', 'bob@example.com'),
    ('charlie', 'charlie@example.com');

-- Complex query with joins and aggregation
SELECT
    u.username,
    COUNT(o.id) as order_count,
    COALESCE(SUM(o.total), 0) as total_spent
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
WHERE u.created_at >= '2024-01-01'
GROUP BY u.id, u.username
HAVING COUNT(o.id) > 0
ORDER BY total_spent DESC
LIMIT 10;
""",
    "html": """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Example Page</title>
    <link rel="stylesheet" href="/styles/main.css">
</head>
<body>
    <header class="site-header">
        <nav class="navbar">
            <a href="/" class="logo">Brand</a>
            <ul class="nav-links">
                <li><a href="/about">About</a></li>
                <li><a href="/contact">Contact</a></li>
            </ul>
        </nav>
    </header>

    <main id="content">
        <article class="post">
            <h1>Welcome to Our Site</h1>
            <p>This is a <strong>sample</strong> paragraph with <em>inline</em> styles.</p>
            <img src="/images/hero.jpg" alt="Hero image" loading="lazy">
        </article>
    </main>

    <script src="/js/app.js" defer></script>
</body>
</html>
""",
    "css": """
:root {
    --primary-color: #3498db;
    --secondary-color: #2ecc71;
    --font-stack: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    font-family: var(--font-stack);
    line-height: 1.6;
    color: #333;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 1rem;
}

@media (min-width: 768px) {
    .grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 2rem;
    }
}

.btn {
    display: inline-block;
    padding: 0.75rem 1.5rem;
    background: var(--primary-color);
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    transition: background-color 0.3s ease;
}

.btn:hover {
    background: darken(var(--primary-color), 10%);
}
""",
    "json": """
{
  "name": "my-awesome-project",
  "version": "1.0.0",
  "description": "A sample JSON configuration",
  "main": "index.js",
  "scripts": {
    "start": "node index.js",
    "test": "jest --coverage",
    "build": "webpack --mode production"
  },
  "dependencies": {
    "express": "^4.18.2",
    "lodash": "^4.17.21"
  },
  "devDependencies": {
    "jest": "^29.0.0",
    "typescript": "^5.0.0"
  },
  "config": {
    "port": 3000,
    "database": {
      "host": "localhost",
      "port": 5432,
      "name": "mydb"
    },
    "features": {
      "auth": true,
      "cache": true,
      "rateLimit": 100
    }
  }
}
""",
    "yaml": """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  namespace: production
  labels:
    app: web
    tier: frontend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
        - name: web
          image: nginx:1.21
          ports:
            - containerPort: 80
          resources:
            limits:
              cpu: "500m"
              memory: "128Mi"
            requests:
              cpu: "250m"
              memory: "64Mi"
          env:
            - name: NODE_ENV
              value: "production"
            - name: API_KEY
              valueFrom:
                secretKeyRef:
                  name: api-secrets
                  key: api-key
          livenessProbe:
            httpGet:
              path: /health
              port: 80
            initialDelaySeconds: 30
            periodSeconds: 10
""",
    "toml": """
[package]
name = "my-project"
version = "0.1.0"
edition = "2021"
authors = ["Developer <dev@example.com>"]
description = "A sample Rust project"
license = "MIT"
repository = "https://github.com/example/my-project"

[dependencies]
tokio = { version = "1.0", features = ["full"] }
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
anyhow = "1.0"

[dev-dependencies]
criterion = "0.5"
mockall = "0.11"

[profile.release]
opt-level = 3
lto = true
codegen-units = 1

[[bin]]
name = "server"
path = "src/bin/server.rs"

[features]
default = ["tokio"]
full = ["tokio", "serde"]
""",
    "bash": """
#!/bin/bash
set -euo pipefail

# Configuration
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly LOG_FILE="/var/log/deploy.log"
readonly MAX_RETRIES=3

log() {
    local level="$1"
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $*" | tee -a "$LOG_FILE"
}

deploy_app() {
    local app_name="$1"
    local version="${2:-latest}"

    log "INFO" "Deploying $app_name version $version"

    for ((i=1; i<=MAX_RETRIES; i++)); do
        if docker pull "registry.example.com/$app_name:$version"; then
            log "INFO" "Successfully pulled image"
            break
        else
            log "WARN" "Attempt $i failed, retrying..."
            sleep $((i * 5))
        fi
    done

    docker-compose -f "$SCRIPT_DIR/docker-compose.yml" up -d
}

main() {
    if [[ $# -lt 1 ]]; then
        echo "Usage: $0 <app-name> [version]" >&2
        exit 1
    fi

    deploy_app "$@"
    log "INFO" "Deployment complete"
}

main "$@"
""",
    "c": """
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>

#define MAX_THREADS 4
#define BUFFER_SIZE 1024

typedef struct {
    int id;
    char *data;
    size_t length;
} Task;

typedef struct {
    Task *tasks;
    int count;
    int capacity;
    pthread_mutex_t lock;
} TaskQueue;

TaskQueue* queue_create(int capacity) {
    TaskQueue *queue = malloc(sizeof(TaskQueue));
    if (!queue) return NULL;

    queue->tasks = malloc(sizeof(Task) * capacity);
    queue->count = 0;
    queue->capacity = capacity;
    pthread_mutex_init(&queue->lock, NULL);

    return queue;
}

void queue_push(TaskQueue *queue, Task task) {
    pthread_mutex_lock(&queue->lock);
    if (queue->count < queue->capacity) {
        queue->tasks[queue->count++] = task;
    }
    pthread_mutex_unlock(&queue->lock);
}

int main(int argc, char **argv) {
    TaskQueue *queue = queue_create(100);

    for (int i = 0; i < 10; i++) {
        Task t = {.id = i, .data = "test", .length = 4};
        queue_push(queue, t);
    }

    printf("Queue has %d tasks\\n", queue->count);
    return 0;
}
""",
    "cpp": """
#include <iostream>
#include <vector>
#include <memory>
#include <algorithm>
#include <ranges>

template<typename T>
class ThreadPool {
public:
    explicit ThreadPool(size_t threads) : stop_(false) {
        workers_.reserve(threads);
        for (size_t i = 0; i < threads; ++i) {
            workers_.emplace_back([this] { this->worker_loop(); });
        }
    }

    ~ThreadPool() {
        stop_ = true;
        for (auto& worker : workers_) {
            if (worker.joinable()) {
                worker.join();
            }
        }
    }

    template<typename F>
    auto submit(F&& func) -> std::future<decltype(func())> {
        using return_type = decltype(func());
        auto task = std::make_shared<std::packaged_task<return_type()>>(
            std::forward<F>(func)
        );
        return task->get_future();
    }

private:
    void worker_loop() {
        while (!stop_) {
            // Process tasks
        }
    }

    std::vector<std::thread> workers_;
    std::atomic<bool> stop_;
};

int main() {
    auto numbers = std::vector{1, 2, 3, 4, 5};
    auto squared = numbers
        | std::views::transform([](int n) { return n * n; })
        | std::views::filter([](int n) { return n > 4; });

    for (int n : squared) {
        std::cout << n << " ";
    }
    return 0;
}
""",
    "ruby": """
# frozen_string_literal: true

require 'json'
require 'net/http'

module API
  class Client
    BASE_URL = 'https://api.example.com'

    attr_reader :api_key, :timeout

    def initialize(api_key:, timeout: 30)
      @api_key = api_key
      @timeout = timeout
    end

    def get(endpoint, params = {})
      uri = build_uri(endpoint, params)
      request = Net::HTTP::Get.new(uri)
      execute(request)
    end

    def post(endpoint, body = {})
      uri = build_uri(endpoint)
      request = Net::HTTP::Post.new(uri)
      request.body = body.to_json
      execute(request)
    end

    private

    def build_uri(endpoint, params = {})
      uri = URI("#{BASE_URL}/#{endpoint}")
      uri.query = URI.encode_www_form(params) unless params.empty?
      uri
    end

    def execute(request)
      request['Authorization'] = "Bearer #{api_key}"
      request['Content-Type'] = 'application/json'

      response = Net::HTTP.start(request.uri.host, request.uri.port, use_ssl: true) do |http|
        http.request(request)
      end

      JSON.parse(response.body, symbolize_names: true)
    rescue StandardError => e
      { error: e.message }
    end
  end
end

client = API::Client.new(api_key: ENV['API_KEY'])
result = client.get('users', page: 1, limit: 10)
puts result.inspect
""",
    "markdown": """
# Project Documentation

## Overview

This is a **sample** project demonstrating _markdown_ syntax highlighting.

### Features

- Fast performance
- Easy to use
- Well documented

### Installation

```bash
pip install my-package
```

### Usage Example

Here's how to get started:

1. Import the library
2. Create an instance
3. Call the methods

> **Note**: Make sure you have Python 3.8+ installed.

### API Reference

| Method | Description | Returns |
|--------|-------------|---------|
| `get()` | Fetch data | `dict` |
| `post()` | Send data | `bool` |
| `delete()` | Remove data | `None` |

### Links

- [Documentation](https://docs.example.com)
- [GitHub](https://github.com/example/project)

---

*Last updated: 2024*
""",
    "dockerfile": """
# Multi-stage build for Python application
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \\
    build-essential \\
    libpq-dev \\
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.12-slim AS production

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:create_app()"]
""",
    "xml": """
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
                             http://maven.apache.org/xsd/maven-4.0.0.xsd">

    <modelVersion>4.0.0</modelVersion>

    <groupId>com.example</groupId>
    <artifactId>my-application</artifactId>
    <version>1.0.0-SNAPSHOT</version>
    <packaging>jar</packaging>

    <properties>
        <java.version>17</java.version>
        <spring.version>3.2.0</spring.version>
    </properties>

    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
            <version>${spring.version}</version>
        </dependency>

        <dependency>
            <groupId>org.junit.jupiter</groupId>
            <artifactId>junit-jupiter</artifactId>
            <version>5.10.0</version>
            <scope>test</scope>
        </dependency>
    </dependencies>

    <build>
        <plugins>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-compiler-plugin</artifactId>
                <configuration>
                    <source>${java.version}</source>
                    <target>${java.version}</target>
                </configuration>
            </plugin>
        </plugins>
    </build>
</project>
""",
    "kotlin": """
package com.example.app

import kotlinx.coroutines.*
import kotlinx.coroutines.flow.*

data class User(
    val id: Long,
    val name: String,
    val email: String
)

interface UserRepository {
    suspend fun findById(id: Long): User?
    fun findAll(): Flow<User>
    suspend fun save(user: User): User
}

class UserService(
    private val repository: UserRepository,
    private val dispatcher: CoroutineDispatcher = Dispatchers.IO
) {
    suspend fun getUser(id: Long): Result<User> = withContext(dispatcher) {
        runCatching {
            repository.findById(id) ?: throw NoSuchElementException("User not found")
        }
    }

    fun getAllUsers(): Flow<User> = repository.findAll()
        .catch { e -> emit(User(-1, "Error", e.message ?: "Unknown")) }
        .flowOn(dispatcher)

    suspend fun createUser(name: String, email: String): User {
        val user = User(
            id = System.currentTimeMillis(),
            name = name,
            email = email
        )
        return repository.save(user)
    }
}

fun main() = runBlocking {
    println("Hello, Kotlin!")
}
""",
    "swift": """
import Foundation

protocol DataService {
    associatedtype T: Codable
    func fetch() async throws -> [T]
    func save(_ item: T) async throws
}

struct User: Codable, Identifiable {
    let id: UUID
    var name: String
    var email: String
    var createdAt: Date
}

actor UserStore: DataService {
    typealias T = User

    private var users: [UUID: User] = [:]

    func fetch() async throws -> [User] {
        return Array(users.values)
    }

    func save(_ user: User) async throws {
        users[user.id] = user
    }

    func findById(_ id: UUID) async -> User? {
        return users[id]
    }
}

@MainActor
class UserViewModel: ObservableObject {
    @Published var users: [User] = []
    @Published var isLoading = false

    private let store: UserStore

    init(store: UserStore = UserStore()) {
        self.store = store
    }

    func loadUsers() async {
        isLoading = true
        defer { isLoading = false }

        do {
            users = try await store.fetch()
        } catch {
            print("Error loading users: \\(error)")
        }
    }
}
""",
    "php": """
<?php

declare(strict_types=1);

namespace App\\Services;

use App\\Models\\User;
use App\\Repositories\\UserRepository;
use Illuminate\\Support\\Collection;

readonly class UserService
{
    public function __construct(
        private UserRepository $repository,
        private CacheService $cache,
    ) {}

    public function findById(int $id): ?User
    {
        return $this->cache->remember(
            key: "user:{$id}",
            ttl: 3600,
            callback: fn() => $this->repository->find($id)
        );
    }

    public function findByEmail(string $email): ?User
    {
        return $this->repository->findByEmail($email);
    }

    /**
     * @return Collection<int, User>
     */
    public function getActiveUsers(): Collection
    {
        return $this->repository
            ->query()
            ->where('status', 'active')
            ->orderBy('created_at', 'desc')
            ->get();
    }

    public function createUser(array $data): User
    {
        $user = new User([
            'name' => $data['name'],
            'email' => $data['email'],
            'password' => password_hash($data['password'], PASSWORD_ARGON2ID),
        ]);

        $this->repository->save($user);

        return $user;
    }
}
""",
    "hcl": """
terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket = "my-terraform-state"
    key    = "prod/terraform.tfstate"
    region = "us-east-1"
  }
}

variable "environment" {
  type        = string
  description = "Deployment environment"
  default     = "production"
}

variable "instance_count" {
  type    = number
  default = 3
}

resource "aws_instance" "web" {
  count         = var.instance_count
  ami           = data.aws_ami.ubuntu.id
  instance_type = "t3.medium"

  tags = {
    Name        = "web-${count.index + 1}"
    Environment = var.environment
  }

  lifecycle {
    create_before_destroy = true
  }
}

output "instance_ips" {
  value       = aws_instance.web[*].public_ip
  description = "Public IPs of web servers"
}
""",
    "scala": """
package com.example.app

import scala.concurrent.{ExecutionContext, Future}
import scala.util.{Failure, Success, Try}

case class User(id: Long, name: String, email: String)

trait UserRepository {
  def findById(id: Long): Future[Option[User]]
  def findAll(): Future[Seq[User]]
  def save(user: User): Future[User]
}

class UserService(repository: UserRepository)(implicit ec: ExecutionContext) {

  def getUser(id: Long): Future[Either[String, User]] = {
    repository.findById(id).map {
      case Some(user) => Right(user)
      case None => Left(s"User with id $id not found")
    }
  }

  def createUser(name: String, email: String): Future[User] = {
    val user = User(
      id = System.currentTimeMillis(),
      name = name,
      email = email
    )
    repository.save(user)
  }

  def processUsers(): Future[List[String]] = {
    repository.findAll().map { users =>
      users.toList
        .filter(_.email.contains("@"))
        .map(u => s"${u.name} <${u.email}>")
        .sorted
    }
  }
}

object Main extends App {
  println("Hello, Scala!")

  val numbers = (1 to 10).toList
  val squared = numbers.map(n => n * n)
  val filtered = squared.filter(_ > 25)

  filtered.foreach(println)
}
""",
    "elixir": '''
defmodule MyApp.Users do
  @moduledoc """
  User management functions.
  """

  alias MyApp.Repo
  alias MyApp.Users.User

  @doc """
  Gets a user by ID.

  ## Examples

      iex> get_user(123)
      %User{id: 123, name: "Alice"}

  """
  def get_user(id) when is_integer(id) do
    Repo.get(User, id)
  end

  def get_user(_), do: {:error, :invalid_id}

  def list_users(opts \\\\ []) do
    limit = Keyword.get(opts, :limit, 100)
    offset = Keyword.get(opts, :offset, 0)

    User
    |> limit(^limit)
    |> offset(^offset)
    |> Repo.all()
  end

  def create_user(attrs) do
    %User{}
    |> User.changeset(attrs)
    |> Repo.insert()
  end

  def update_user(%User{} = user, attrs) do
    user
    |> User.changeset(attrs)
    |> Repo.update()
  end
end

defmodule MyApp.Users.User do
  use Ecto.Schema
  import Ecto.Changeset

  schema "users" do
    field :name, :string
    field :email, :string
    field :password_hash, :string

    timestamps()
  end

  def changeset(user, attrs) do
    user
    |> cast(attrs, [:name, :email])
    |> validate_required([:name, :email])
    |> validate_format(:email, ~r/@/)
    |> unique_constraint(:email)
  end
end
''',
    "graphql": """
type Query {
  user(id: ID!): User
  users(filter: UserFilter, pagination: Pagination): UserConnection!
  posts(authorId: ID): [Post!]!
}

type Mutation {
  createUser(input: CreateUserInput!): UserPayload!
  updateUser(id: ID!, input: UpdateUserInput!): UserPayload!
  deleteUser(id: ID!): DeletePayload!
}

type Subscription {
  userCreated: User!
  postPublished(authorId: ID): Post!
}

type User {
  id: ID!
  name: String!
  email: String!
  avatar: String
  posts(first: Int, after: String): PostConnection!
  createdAt: DateTime!
  updatedAt: DateTime!
}

type Post {
  id: ID!
  title: String!
  content: String!
  author: User!
  tags: [String!]!
  publishedAt: DateTime
}

input CreateUserInput {
  name: String!
  email: String!
  password: String!
}

input UpdateUserInput {
  name: String
  email: String
  avatar: String
}

input UserFilter {
  name: String
  email: String
  createdAfter: DateTime
}

input Pagination {
  first: Int
  after: String
  last: Int
  before: String
}

type UserConnection {
  edges: [UserEdge!]!
  pageInfo: PageInfo!
  totalCount: Int!
}

type UserEdge {
  node: User!
  cursor: String!
}

type PageInfo {
  hasNextPage: Boolean!
  hasPreviousPage: Boolean!
  startCursor: String
  endCursor: String
}

type UserPayload {
  user: User
  errors: [Error!]
}

type DeletePayload {
  success: Boolean!
  errors: [Error!]
}

type Error {
  field: String
  message: String!
}

scalar DateTime
""",
    "diff": """
diff --git a/src/config.py b/src/config.py
index 1234567..abcdefg 100644
--- a/src/config.py
+++ b/src/config.py
@@ -1,10 +1,15 @@
 import os
+from pathlib import Path

 class Config:
     DEBUG = False
-    DATABASE_URL = "sqlite:///app.db"
+    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///app.db")
+    SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
+
+    # New settings
+    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
+    CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))

 class DevelopmentConfig(Config):
     DEBUG = True
-    DATABASE_URL = "sqlite:///dev.db"
+    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///dev.db")
+    LOG_LEVEL = "DEBUG"
""",
}

# Add more minimal samples for languages without detailed examples
MINIMAL_SAMPLES = {
    "lua": """
local function greet(name)
    print("Hello, " .. name)
end

local Person = {}
Person.__index = Person

function Person:new(name, age)
    local self = setmetatable({}, Person)
    self.name = name
    self.age = age
    return self
end

function Person:introduce()
    print(string.format("I am %s, %d years old", self.name, self.age))
end

local p = Person:new("Alice", 30)
p:introduce()
""",
    "perl": """
#!/usr/bin/perl
use strict;
use warnings;
use v5.36;

package Person {
    sub new {
        my ($class, %args) = @_;
        return bless \\%args, $class;
    }

    sub greet {
        my ($self) = @_;
        say "Hello, I am $self->{name}";
    }
}

my $person = Person->new(name => "Alice", age => 30);
$person->greet();

my @numbers = (1, 2, 3, 4, 5);
my @squared = map { $_ ** 2 } @numbers;
print join(", ", @squared), "\\n";
""",
    "haskell": """
module Main where

import Data.List (sort)
import Control.Monad (forM_)

data Person = Person
  { name :: String
  , age :: Int
  } deriving (Show, Eq)

greet :: Person -> String
greet person = "Hello, " ++ name person

fibonacci :: Int -> Int
fibonacci 0 = 0
fibonacci 1 = 1
fibonacci n = fibonacci (n - 1) + fibonacci (n - 2)

main :: IO ()
main = do
  let alice = Person "Alice" 30
  putStrLn $ greet alice

  let fibs = map fibonacci [0..10]
  forM_ fibs print
""",
    "r": """
library(tidyverse)
library(ggplot2)

# Load data
data <- read.csv("data.csv")

# Data transformation
processed <- data %>%
  filter(value > 0) %>%
  mutate(
    log_value = log(value),
    category = factor(category)
  ) %>%
  group_by(category) %>%
  summarise(
    mean_value = mean(value),
    sd_value = sd(value),
    n = n()
  )

# Create plot
ggplot(processed, aes(x = category, y = mean_value, fill = category)) +
  geom_bar(stat = "identity") +
  geom_errorbar(aes(ymin = mean_value - sd_value,
                    ymax = mean_value + sd_value),
                width = 0.2) +
  labs(title = "Mean Values by Category",
       x = "Category",
       y = "Mean Value") +
  theme_minimal()
""",
    "clojure": """
(ns myapp.core
  (:require [clojure.string :as str]))

(defn greet
  "Returns a greeting string"
  [name]
  (str "Hello, " name "!"))

(defrecord Person [name age])

(defn create-person
  [name age]
  (->Person name age))

(def people
  [(create-person "Alice" 30)
   (create-person "Bob" 25)
   (create-person "Charlie" 35)])

(defn adults
  [people]
  (filter #(>= (:age %) 18) people))

(defn -main
  [& args]
  (println (greet "World"))
  (doseq [p (adults people)]
    (println (str (:name p) " is " (:age p) " years old"))))
""",
    "julia": """
module MyModule

using LinearAlgebra
using Statistics

struct Point{T<:Real}
    x::T
    y::T
end

function distance(p1::Point, p2::Point)
    sqrt((p1.x - p2.x)^2 + (p1.y - p2.y)^2)
end

function fibonacci(n::Int)::Int
    n <= 1 && return n
    return fibonacci(n - 1) + fibonacci(n - 2)
end

function process_data(data::Vector{Float64})
    μ = mean(data)
    σ = std(data)
    normalized = (data .- μ) ./ σ
    return normalized
end

# Main execution
function main()
    p1 = Point(0.0, 0.0)
    p2 = Point(3.0, 4.0)
    println("Distance: $(distance(p1, p2))")

    fibs = [fibonacci(i) for i in 0:10]
    println("Fibonacci: $fibs")
end

end # module
""",
    "dart": """
import 'dart:async';
import 'dart:convert';

class User {
  final int id;
  final String name;
  final String email;

  const User({
    required this.id,
    required this.name,
    required this.email,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'] as int,
      name: json['name'] as String,
      email: json['email'] as String,
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'name': name,
    'email': email,
  };
}

Future<List<User>> fetchUsers() async {
  await Future.delayed(Duration(seconds: 1));
  return [
    User(id: 1, name: 'Alice', email: 'alice@example.com'),
    User(id: 2, name: 'Bob', email: 'bob@example.com'),
  ];
}

void main() async {
  final users = await fetchUsers();
  for (final user in users) {
    print('${user.name} <${user.email}>');
  }
}
""",
    "nim": """
import strutils, sequtils, tables

type
  Person = object
    name: string
    age: int

  PersonRef = ref Person

proc newPerson(name: string, age: int): PersonRef =
  result = PersonRef(name: name, age: age)

proc greet(p: PersonRef): string =
  "Hello, " & p.name

proc fibonacci(n: int): int =
  if n <= 1:
    return n
  return fibonacci(n - 1) + fibonacci(n - 2)

proc main() =
  let alice = newPerson("Alice", 30)
  echo alice.greet()

  let numbers = @[1, 2, 3, 4, 5]
  let squared = numbers.mapIt(it * it)
  echo "Squared: ", squared

  let fibs = (0..10).toSeq.mapIt(fibonacci(it))
  echo "Fibonacci: ", fibs

when isMainModule:
  main()
""",
    "zig": """
const std = @import("std");
const Allocator = std.mem.Allocator;

const Person = struct {
    name: []const u8,
    age: u32,

    pub fn init(name: []const u8, age: u32) Person {
        return .{ .name = name, .age = age };
    }

    pub fn greet(self: Person) void {
        std.debug.print("Hello, {s}!\\n", .{self.name});
    }
};

fn fibonacci(n: u32) u32 {
    if (n <= 1) return n;
    return fibonacci(n - 1) + fibonacci(n - 2);
}

pub fn main() !void {
    const allocator = std.heap.page_allocator;

    var list = std.ArrayList(u32).init(allocator);
    defer list.deinit();

    var i: u32 = 0;
    while (i < 10) : (i += 1) {
        try list.append(fibonacci(i));
    }

    const alice = Person.init("Alice", 30);
    alice.greet();

    std.debug.print("Fibonacci: ", .{});
    for (list.items) |item| {
        std.debug.print("{} ", .{item});
    }
}
""",
    "mojo": """
from python import Python

struct Person:
    var name: String
    var age: Int

    fn __init__(inout self, name: String, age: Int):
        self.name = name
        self.age = age

    fn greet(self) -> String:
        return "Hello, " + self.name

fn fibonacci(n: Int) -> Int:
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)

fn main():
    let alice = Person("Alice", 30)
    print(alice.greet())

    # Compute fibonacci numbers
    for i in range(10):
        print(fibonacci(i))
""",
    "gleam": """
import gleam/io
import gleam/list
import gleam/string

pub type Person {
  Person(name: String, age: Int)
}

pub fn greet(person: Person) -> String {
  "Hello, " <> person.name <> "!"
}

pub fn fibonacci(n: Int) -> Int {
  case n {
    0 -> 0
    1 -> 1
    _ -> fibonacci(n - 1) + fibonacci(n - 2)
  }
}

pub fn main() {
  let alice = Person("Alice", 30)
  io.println(greet(alice))

  let fibs = list.range(0, 10)
    |> list.map(fibonacci)
    |> list.map(fn(n) { string.inspect(n) })
    |> string.join(", ")

  io.println("Fibonacci: " <> fibs)
}
""",
    "groovy": """
import groovy.transform.CompileStatic
import groovy.json.JsonSlurper

@CompileStatic
class Person {
    String name
    int age

    String greet() {
        "Hello, ${name}!"
    }
}

def fibonacci(int n) {
    n <= 1 ? n : fibonacci(n - 1) + fibonacci(n - 2)
}

// Main script
def alice = new Person(name: 'Alice', age: 30)
println alice.greet()

def numbers = [1, 2, 3, 4, 5]
def squared = numbers.collect { it * it }
println "Squared: $squared"

def fibs = (0..10).collect { fibonacci(it) }
println "Fibonacci: $fibs"

// JSON parsing
def json = new JsonSlurper()
def data = json.parseText('{"name": "Bob", "age": 25}')
println "Parsed: ${data.name}"
""",
    "powershell": """
#Requires -Version 7.0

class Person {
    [string]$Name
    [int]$Age

    Person([string]$name, [int]$age) {
        $this.Name = $name
        $this.Age = $age
    }

    [string] Greet() {
        return "Hello, $($this.Name)!"
    }
}

function Get-Fibonacci {
    param([int]$n)

    if ($n -le 1) { return $n }
    return (Get-Fibonacci ($n - 1)) + (Get-Fibonacci ($n - 2))
}

# Main script
$alice = [Person]::new("Alice", 30)
Write-Host $alice.Greet()

$numbers = 1..5
$squared = $numbers | ForEach-Object { $_ * $_ }
Write-Host "Squared: $($squared -join ', ')"

$fibs = 0..10 | ForEach-Object { Get-Fibonacci $_ }
Write-Host "Fibonacci: $($fibs -join ', ')"

# File operations
Get-ChildItem -Path . -Filter "*.txt" |
    Where-Object { $_.Length -gt 1KB } |
    Sort-Object -Property Length -Descending |
    Select-Object -First 5 Name, Length
""",
    "protobuf": """
syntax = "proto3";

package myapp.users.v1;

option go_package = "github.com/example/myapp/proto/users/v1";
option java_package = "com.example.myapp.proto.users.v1";

import "google/protobuf/timestamp.proto";
import "google/protobuf/empty.proto";

message User {
  int64 id = 1;
  string name = 2;
  string email = 3;
  UserStatus status = 4;
  google.protobuf.Timestamp created_at = 5;
  repeated string roles = 6;
  map<string, string> metadata = 7;
}

enum UserStatus {
  USER_STATUS_UNSPECIFIED = 0;
  USER_STATUS_ACTIVE = 1;
  USER_STATUS_INACTIVE = 2;
  USER_STATUS_BANNED = 3;
}

message CreateUserRequest {
  string name = 1;
  string email = 2;
}

message CreateUserResponse {
  User user = 1;
}

message GetUserRequest {
  int64 id = 1;
}

message ListUsersRequest {
  int32 page_size = 1;
  string page_token = 2;
}

message ListUsersResponse {
  repeated User users = 1;
  string next_page_token = 2;
}

service UserService {
  rpc CreateUser(CreateUserRequest) returns (CreateUserResponse);
  rpc GetUser(GetUserRequest) returns (User);
  rpc ListUsers(ListUsersRequest) returns (ListUsersResponse);
  rpc DeleteUser(GetUserRequest) returns (google.protobuf.Empty);
}
""",
    "ini": """
; Application configuration
[app]
name = MyApplication
version = 1.0.0
debug = true
log_level = INFO

[database]
host = localhost
port = 5432
name = mydb
user = admin
password = ${DB_PASSWORD}
pool_size = 10
timeout = 30

[cache]
enabled = true
backend = redis
host = localhost
port = 6379
ttl = 3600

[server]
host = 0.0.0.0
port = 8080
workers = 4
keep_alive = 120

[logging]
format = %(asctime)s - %(name)s - %(levelname)s - %(message)s
file = /var/log/app.log
max_size = 10MB
backup_count = 5
""",
    "makefile": """
.PHONY: all build test clean install dev

# Variables
BINARY_NAME := myapp
VERSION := $(shell git describe --tags --always --dirty)
BUILD_DIR := ./build
GO_FILES := $(shell find . -type f -name '*.go')

# Build flags
LDFLAGS := -ldflags "-X main.version=$(VERSION)"

all: build

build: $(BUILD_DIR)/$(BINARY_NAME)

$(BUILD_DIR)/$(BINARY_NAME): $(GO_FILES)
\t@mkdir -p $(BUILD_DIR)
\tgo build $(LDFLAGS) -o $@ ./cmd/$(BINARY_NAME)

test:
\tgo test -v -race -coverprofile=coverage.out ./...

coverage: test
\tgo tool cover -html=coverage.out -o coverage.html

clean:
\trm -rf $(BUILD_DIR)
\trm -f coverage.out coverage.html

install: build
\tcp $(BUILD_DIR)/$(BINARY_NAME) /usr/local/bin/

dev:
\tair -c .air.toml

docker-build:
\tdocker build -t $(BINARY_NAME):$(VERSION) .

docker-push: docker-build
\tdocker push $(BINARY_NAME):$(VERSION)
""",
    "nginx": """
upstream backend {
    least_conn;
    server backend1.example.com:8080 weight=5;
    server backend2.example.com:8080;
    server backup.example.com:8080 backup;
}

server {
    listen 80;
    listen [::]:80;
    server_name example.com www.example.com;

    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name example.com www.example.com;

    ssl_certificate /etc/ssl/certs/example.com.crt;
    ssl_certificate_key /etc/ssl/private/example.com.key;
    ssl_protocols TLSv1.2 TLSv1.3;

    root /var/www/html;
    index index.html index.htm;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 30s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location ~* \\.(jpg|jpeg|png|gif|ico|css|js)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
""",
}

# Merge samples
SAMPLES.update(MINIMAL_SAMPLES)


# =============================================================================
# Benchmark infrastructure
# =============================================================================


@dataclass
class BenchmarkResult:
    language: str
    rosettes_mean_ms: float
    rosettes_std_ms: float
    pygments_mean_ms: float | None
    pygments_std_ms: float | None
    speedup: float | None
    code_chars: int
    iterations: int


def benchmark_function(
    func: Callable[[], str], iterations: int = 100, warmup: int = 5
) -> tuple[float, float]:
    """Benchmark a function, returning (mean_ms, std_ms)."""
    # Warmup
    for _ in range(warmup):
        func()

    # Collect samples
    gc.disable()
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        func()
        elapsed = time.perf_counter() - start
        times.append(elapsed * 1000)  # Convert to ms
    gc.enable()

    return statistics.mean(times), statistics.stdev(times) if len(times) > 1 else 0.0


def benchmark_language(language: str, code: str, iterations: int = 100) -> BenchmarkResult | None:
    """Benchmark both Rosettes and Pygments for a language."""

    # Rosettes benchmark
    def rosettes_highlight():
        return rosettes.highlight(code, language)

    try:
        rosettes_mean, rosettes_std = benchmark_function(rosettes_highlight, iterations)
    except Exception as e:
        print(f"| {language[:12].ljust(12)} | {len(code):5} | ERROR: {str(e)[:30]} |")
        return None

    # Pygments benchmark (if available)
    pygments_mean = None
    pygments_std = None
    speedup = None

    if PYGMENTS_AVAILABLE:
        try:
            pygments_lexer = pygments_get_lexer(language)
            pygments_formatter = PygmentsHtmlFormatter()

            def pygments_do_highlight():
                return pygments_highlight(code, pygments_lexer, pygments_formatter)

            pygments_mean, pygments_std = benchmark_function(pygments_do_highlight, iterations)
            speedup = pygments_mean / rosettes_mean if rosettes_mean > 0 else 0
        except Exception:
            pass  # Language not supported in Pygments

    return BenchmarkResult(
        language=language,
        rosettes_mean_ms=rosettes_mean,
        rosettes_std_ms=rosettes_std,
        pygments_mean_ms=pygments_mean,
        pygments_std_ms=pygments_std,
        speedup=speedup,
        code_chars=len(code),
        iterations=iterations,
    )


def format_result_row(result: BenchmarkResult) -> str:
    """Format a single result as a table row."""
    lang = result.language[:12].ljust(12)
    chars = str(result.code_chars).rjust(5)
    rosettes = f"{result.rosettes_mean_ms:6.3f} ± {result.rosettes_std_ms:5.3f}"

    if result.pygments_mean_ms is not None:
        pygments = f"{result.pygments_mean_ms:6.3f} ± {result.pygments_std_ms:5.3f}"
        speedup = f"{result.speedup:5.2f}x"
        if result.speedup >= 1.5:
            speedup = f"🚀 {speedup}"
        elif result.speedup >= 1.0:
            speedup = f"✅ {speedup}"
        else:
            speedup = f"❌ {speedup}"
    else:
        pygments = "      N/A       "
        speedup = "  N/A "

    return f"| {lang} | {chars} | {rosettes} | {pygments} | {speedup} |"


def main():
    print("=" * 90)
    print("🏎️  Rosettes vs Pygments Benchmark")
    print("=" * 90)
    print()
    print(f"Rosettes version: {rosettes.__version__}")
    print(f"Languages to benchmark: {len(SAMPLES)}")
    print(f"Pygments available: {PYGMENTS_AVAILABLE}")
    print()

    # Header
    print("-" * 90)
    print("| Language     | Chars | Rosettes (ms)     | Pygments (ms)     | Speedup |")
    print("|--------------|-------|-------------------|-------------------|---------|")

    results: list[BenchmarkResult] = []
    total_rosettes = 0.0
    total_pygments = 0.0
    compared_count = 0

    # Sort languages alphabetically
    for language in sorted(SAMPLES.keys()):
        code = SAMPLES[language]

        # Check if Rosettes supports this language
        if not rosettes.supports_language(language):
            print(
                f"| {language[:12].ljust(12)} | {len(code):5} | {'UNSUPPORTED':^17} | {'---':^17} | {'---':^7} |"
            )
            continue

        result = benchmark_language(language, code, iterations=100)
        if result is None:
            continue

        results.append(result)

        print(format_result_row(result))

        total_rosettes += result.rosettes_mean_ms
        if result.pygments_mean_ms is not None:
            total_pygments += result.pygments_mean_ms
            compared_count += 1

    print("-" * 90)

    # Summary statistics
    print()
    print("=" * 90)
    print("📊 Summary Statistics")
    print("=" * 90)

    if results:
        rosettes_times = [r.rosettes_mean_ms for r in results]
        print("\nRosettes:")
        print(f"  Total time: {total_rosettes:.2f} ms")
        print(f"  Average per language: {statistics.mean(rosettes_times):.3f} ms")
        print(f"  Median: {statistics.median(rosettes_times):.3f} ms")
        print(
            f"  Min: {min(rosettes_times):.3f} ms ({min(results, key=lambda r: r.rosettes_mean_ms).language})"
        )
        print(
            f"  Max: {max(rosettes_times):.3f} ms ({max(results, key=lambda r: r.rosettes_mean_ms).language})"
        )

    if compared_count > 0:
        speedups = [r.speedup for r in results if r.speedup is not None]
        faster_count = sum(1 for s in speedups if s >= 1.0)

        print("\nPygments:")
        print(f"  Total time: {total_pygments:.2f} ms")
        print(f"  Languages compared: {compared_count}")

        print("\nComparison:")
        print(f"  Overall speedup: {total_pygments / total_rosettes:.2f}x")
        print(f"  Average speedup: {statistics.mean(speedups):.2f}x")
        print(f"  Median speedup: {statistics.median(speedups):.2f}x")
        print(
            f"  Rosettes faster: {faster_count}/{len(speedups)} languages ({100 * faster_count / len(speedups):.0f}%)"
        )

        # Top 5 fastest
        print("\n🏆 Top 5 Speedups:")
        top5 = sorted([r for r in results if r.speedup], key=lambda r: r.speedup, reverse=True)[:5]
        for i, r in enumerate(top5, 1):
            print(f"  {i}. {r.language}: {r.speedup:.2f}x faster")

        # Bottom 5 (if any slower)
        slower = [r for r in results if r.speedup and r.speedup < 1.0]
        if slower:
            print("\n⚠️  Languages where Pygments is faster:")
            for r in sorted(slower, key=lambda r: r.speedup):
                print(f"  - {r.language}: {1 / r.speedup:.2f}x slower")

    print()
    print("=" * 90)
    print("✅ Benchmark complete!")
    print("=" * 90)


if __name__ == "__main__":
    main()
