This is the ``web3ref`` library, which implements a reference
implementation of the `Web3 specification
<http://github.com/mcdonc/web3>`_.

To install it under a Python 2 virtualenv, do "python setup.py
develop", then run the ``simple_server.py`` file within the web3ref
package to see output.

This software can be installed in a virtualenv3 with ``distribute``
installed by doing ``$VENV/bin/python setup.py install``.  When that
is done, 2to3 will be run on the code in the package, and the result
will be present in an egg within the virtualenv3's site-packages
directory.  You can run the ``simple_server.py`` file within the egg
to see the output.

