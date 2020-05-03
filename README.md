[![Build Status](https://travis-ci.com/sonelu/roboglia.svg?branch=master)](https://travis-ci.com/sonelu/roboglia)
[![Documentation Status](https://readthedocs.org/projects/roboglia/badge/?version=latest)](https://roboglia.readthedocs.io/en/latest/?badge=latest)

# Roboglia

``roboglia`` is a framework that helps developers with the setup of robots
in a more reusable fashion. Most of the times the creation of robots involve
integrating actuators, sensors, cameras and microphones, periodically accessing
the information provided by these or supplying commands according to the desired
activities.

The name `roboglia` is derived from the glial cells present in the brian.
Their role is to support the neurons' functions by supplying them
with nutirients, energy and disposing of waste. The analogy is that ``roboglia``
provides this boring, but very complex activity of putting together the specific
functions of the physical devices used in robots in order to provide a more
accessible high-level representation of the robot for the use of the "smart"
control logic that sits at the top.

With ``roboglia`` low level functionality, currently split across multiple
libraries and frameworks are put together and integrated in an extensible way
making it easier for developer to focus on the higher level functionality,
rather than gritty details.

## Installation

Please read carefully the installation instrcutions from the documentation.
As ``roboglia`` needs to interact with a lot of hardware devices, it is very
sensitive to the platform and OS version used.

## Documentation

You can access the detailed documentation on the
[readthedocs.io](https://roboglia.readthedocs.io/en/latest/) website. If you
want to access the documentation in PDF format you can get it from
[here](https://roboglia.readthedocs.io/_/downloads/en/latest/pdf/).
There is also an epub version that can be accessed
[here](https://roboglia.readthedocs.io/_/downloads/en/latest/epub/).

## Contribution

We are very receptive for contributions. Please clone the repository and
sumbit pull requests with the desired contrbution. They will be moderated and,
if they add values to the users, they will be integrated. Please note that
the [Travis CI](https://travis-ci.com) integration will perform the following
two tests on the pull requests:

* it will run all automated tests located in ``tests/`` folder. Please make
  sure that you also run them **before** submitting the pull request to avoid
  it failing. You you should install first your version of the package on
  your machine an then run the tests like this (you should be in the top
  directory of the cloned repository)::

    sudo python setup.py install
    cd tests
    pyton all_tests.py

  Make sure that there are no errors issued by the unit tests. If you created
  new classes or new functions that are not covered by testing, then you will
  also need to write a test class or add a test method in an exiting class
  to test that functionlity and submit those changes too.

* it will check PEP8 on the Python code using flake8. You should install
  (if you don't have it already) on your machine and run this (from the
  top directory of the cloned repository)::

    flake8 roboglia --statistics --count

  Make sure flake8 does not report any problems, and correct any issues
  **before** submitting you are allowed to use ``# noqa`` directives if
  justified.

* if you add classes or methods the documentation templates that produce
  the API Reference might need to be updated too, but this is something that
  will be moderated and can be performed centrally once the code is stable.
  If you know [sphinx](https://www.sphinx-doc.org/en/master/) then you can
  attempt modifying the files in ``docs/`` folder too and include the changes
  in the pull request too.
