##############################################################################
##############################################################################
##############################################################################
##############################################################################
####
#### name:      mupy/quiet.py
####
#### synopsis:  Provide quietable replacement for built-in print()
####
#### copyright: (c) 2020 nbyoung@nbyoung.com
####
#### license:   MIT License
####            https://mit-license.org/
####

isQuiet = False

def qprint(*args, **kwargs):
    if not isQuiet: print(*args, **kwargs)
