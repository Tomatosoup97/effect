"""
Twisted integration for the Effect library.

This is largely concerned with bridging the gap between Effects and Deferreds.

Note that the core effect library does *not* depend on Twisted, but this module
does.

The main useful thing you should be concerned with is the :func:`perform`
function, which is like effect.perform except that it returns a Deferred with
the final result, and also sets up Twisted/Deferred specific effect handling
by using its default effect dispatcher, twisted_dispatcher.
"""

from __future__ import absolute_import

import sys
from functools import wraps

from twisted.internet.defer import Deferred, maybeDeferred, gatherResults
from twisted.python.failure import Failure

from . import dispatch_method, perform as base_perform
from effect import ParallelEffects


def deferred_to_box(d, box):
    """
    Make a Deferred pass its success or fail events on to the given box.
    """
    d.addCallbacks(box.succeed, lambda f: box.fail((f.value, f.type, f.tb)))


def twisted_dispatcher(intent, box):
    """
    Do the same as :func:`effect.default_dispatcher`, but handle 'parallel'
    intents by passing them to :func:`perform_parallel`.
    """
    if type(intent) is ParallelEffects:
        perform_parallel(intent, twisted_dispatcher, box)
    else:
        try:
            result = dispatch_method(intent, twisted_dispatcher)
        except:
            box.fail(sys.exc_info())
        else:
            if isinstance(result, Deferred):
                deferred_to_box(result, box)
            else:
                box.succeed(result)


def perform_parallel(parallel, dispatcher, box):
    """
    Perform a ParallelEffects intent by using the Deferred gatherResults
    function.
    """
    d = gatherResults(
        [maybeDeferred(perform, e, dispatcher) for e in parallel.effects])
    deferred_to_box(d, box)


def perform(effect, dispatcher=twisted_dispatcher):
    """
    Perform an effect, and return a Deferred that will fire with that effect's
    ultimate result.

    Defaults to using the twisted_dispatcher as the dispatcher.
    """
    d = Deferred()
    eff = effect.on(
        success=d.callback,
        error=lambda e: d.errback(Failure(e[1], e[0], e[2])))
    base_perform(eff, dispatcher=dispatcher)
    return d
