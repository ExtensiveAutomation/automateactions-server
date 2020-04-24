# Automate Actions Server

## Server in development

```
cd src/
py automateactions.py --help
Usage: ./automateactions.py [start|stop|status|reload|version]

Options:
  -h, --help  show this help message and exit
  --start     Start the server.
  --version   Show the version.
  --stop      Stop the server.
  --status    Show the current status of the server.
  --reload    Reload the configuration of the server.
```

## Starting server 

```
py automateactions.py --start
server successfully started!
```

The server is running at http://localhost:8081