# Automate Actions Server

Automation Actions server is a complete rewrite of the extensive automation server 
started 10 years ago.

## How to start the server

```
cd src/
py automateactions.py --start
server successfully started!
```

The server is running at http://localhost:8081

## Rest API

### Authenticate

  - POST /v1/session { "login": ..., "password": .... }
  - DELETE /v1/session

### Manage users

  - GET /v1/users[/login]
  - POST /v1/users { "login": ..., "password": ...., "role": .... }
  - DELETE /v1/users/[login]
  
### Manage globals variables

  - GET /v1/globals[/entry_name]?workspace=[name]
  - POST /v1/globals?workspace=[name] {"value": ...}
  
### Manage workspace

  - GET /v1/workspaces
  - POST /v1/workspaces {"name": ...}
  - DELETE /v1/workspaces/[name]
  
### Manage jobs
  - GET /v1/jobs[/id]?workspace=[name]
  - POST /v1/jobs {"yaml-file": ..., "yaml-content": ..., "workspace": ..., "mode":..., "schedule-at": ....}
  - DELETE /v1/jobs/[id]
  
### Manage executions

  - GET /v1/executions[/id]?workspace=[name]&log_index=[id]
  - DELETE /v1/executions/[id]
  
### Manage actions files

  - GET /v1/actions[/filepath]?workspace=[name]
  - POST /v1/actions[/filepath]?workspace=[name] {"content": ...}
  - DELETE /v1/actions/[filepath]?workspace=[name]
  
### Manage snippets files

  - GET /v1/snippets[/filepath]?workspace=[name]
  - POST /v1/snippets[/filepath]?workspace=[name] {"content": ...}
  - DELETE /v1/snippets/[filepath]?workspace=[name]