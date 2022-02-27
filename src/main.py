import sys

if sys.argv[1] == 'cli':
    import cli

    cli.StartCLI()

elif sys.argv[1] == 'rpimode':
    import kickstarter

    kickstarter.StartController()