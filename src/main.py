import sys

if sys.argv[1] == 'gui':
    import gui

    gui.StartGUI()

elif sys.argv[1] == 'rpimode':
    import kickstarter

    kickstarter.StartController()