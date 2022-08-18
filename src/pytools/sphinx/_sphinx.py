"""
Implementation of sphinx module.
"""
import logging
from abc import ABCMeta, abstractmethod
from typing import Any, List, Optional, Tuple

from pytools.api import AllTracker

log = logging.getLogger(__name__)


#
# Exported names
#

__all__ = [
    "AutodocBeforeProcessSignature",
    "AutodocProcessBases",
    "AutodocProcessDocstring",
    "AutodocProcessSignature",
    "AutodocSkipMember",
    "ObjectDescriptionTransform",
    "SphinxCallback",
]

#
# Type variables
#

#: Mock type declaration: Sphinx application object.
Sphinx = Any


#
# Ensure all symbols introduced below are included in __all__
#

__tracker = AllTracker(globals())


#
# Classes
#


class SphinxCallback(metaclass=ABCMeta):
    """
    Abstract base class for autodoc processors.

    Can be passed to :meth:`~sphinx.application.Sphinx.connect` as a callback for an
    event.
    """

    @property
    @abstractmethod
    def event(self) -> str:
        """
        The event processed by this callback.

        Used to connect this callback to sphinx in method :meth:`.connect`.

        :return: name of the event
        """
        pass

    def connect(self, app: Sphinx, priority: Optional[int] = None) -> int:
        """
        Register this callback to be called when :attr:`.event` is emitted.

        Registered callbacks will be invoked on event in the order of priority and
        registration. The priority is ascending order.

        :param app: the Sphinx application to register this processor with
        :param priority: the priority of this processor
        :return: a listener ID that can be used as an argument to
            :meth:`~sphinx.application.Sphinx.disconnect`.
        """

        listener_id: int

        if priority is None:
            listener_id = app.connect(event=self.event, callback=self)
        else:
            listener_id = app.connect(
                event=self.event, callback=self, priority=priority
            )

        return listener_id


# noinspection SpellCheckingInspection
class ObjectDescriptionTransform(SphinxCallback, metaclass=ABCMeta):
    """
    Callback for low-level processing of objects in the document tree being built by
    Sphinx.
    """

    @property
    def event(self) -> str:
        """
        ``"object-description-transform"``
        """
        return "object-description-transform"

    @abstractmethod
    def process(
        self,
        app: Sphinx,
        domain: str,
        objtype: str,
        contentnode: Any,
    ) -> None:
        """
        Process content of objects after their object description directive has run.

        :param app: the Sphinx application object
        :param domain: domain of the object description
        :param objtype: type of the object description
        :param contentnode: content for the object; can be modified in-place
        """
        pass

    def __call__(
        self,
        app: Sphinx,
        domain: str,
        objtype: str,
        contentnode: Any,
    ) -> None:
        try:
            self.process(
                app=app, domain=domain, objtype=objtype, contentnode=contentnode
            )
        except Exception as e:
            log.error(repr(e))
            raise


class AutodocProcessDocstring(SphinxCallback, metaclass=ABCMeta):
    """
    An *autodoc* processor for docstrings.
    """

    @property
    def event(self) -> str:
        """
        ``"autodoc-process-docstring"``
        """
        return "autodoc-process-docstring"

    @abstractmethod
    def process(
        self,
        app: Sphinx,
        what: str,
        name: str,
        obj: object,
        options: object,
        lines: List[str],
    ) -> None:
        """
        Process an event.

        :param app: the Sphinx application object
        :param what: the type of the object which the docstring belongs to (one of
            "module", "class", "exception", "function", "method", "attribute")
        :param name: the fully qualified name of the object
        :param obj: the object itself
        :param options: the options given to the directive: an object with attributes
            ``inherited_members``, ``undoc_members``, ``show_inheritance`` and
            ``noindex`` that are ``True`` if the flag option of same name was given to
            the auto directive
        :param lines: the lines of the docstring
        """
        pass

    def __call__(
        self,
        app: Sphinx,
        what: str,
        name: str,
        obj: object,
        options: object,
        lines: List[str],
    ) -> None:
        try:
            self.process(
                app=app, what=what, name=name, obj=obj, options=options, lines=lines
            )
        except Exception as e:
            log.error(repr(e))
            raise


class AutodocBeforeProcessSignature(SphinxCallback, metaclass=ABCMeta):
    """
    An *autodoc* processor invoked before processing signatures.
    """

    @property
    def event(self) -> str:
        """
        ``"autodoc-before-process-signature"``
        """
        return "autodoc-before-process-signature"

    @abstractmethod
    def process(self, app: Sphinx, obj: Any, bound_method: bool) -> None:
        """
        Process an event.

        :param app: the Sphinx application object
        :param obj: the object itself
        :param bound_method: indicates an object is bound method or not
        """
        pass

    def __call__(
        self, app: Sphinx, obj: object, bound_method: bool
    ) -> Optional[Tuple[str, str]]:
        try:
            return self.process(app=app, obj=obj, bound_method=bound_method)
        except Exception as e:
            log.error(repr(e))
            raise


class AutodocProcessSignature(SphinxCallback, metaclass=ABCMeta):
    """
    An *autodoc* processor for processing signatures.
    """

    @property
    def event(self) -> str:
        """
        ``"autodoc-process-signature"``
        """
        return "autodoc-process-signature"

    @abstractmethod
    def process(
        self,
        app: Sphinx,
        what: str,
        name: str,
        obj: object,
        options: object,
        signature: Optional[str],
        return_annotation: Optional[str],
    ) -> Optional[Tuple[Optional[str], Optional[str]]]:
        """
        Process an event.

        :param app: the Sphinx application object
        :param what: the type of the object which the docstring belongs to (one of
            "module", "class", "exception", "function", "method", "attribute")
        :param name: the fully qualified name of the object
        :param obj: the object itself
        :param options: the options given to the directive: an object with attributes
            ``inherited_members``, ``undoc_members``, ``show_inheritance`` and
            ``noindex`` that are ``True`` if the flag option of same name was given to
            the auto directive
        :param signature: function signature, as a string of the form
            ``(parameter_1, parameter_2)``, or ``None`` if introspection did not succeed
            and signature was not specified in the directive
        :param return_annotation: function return annotation as a string of the form
            `` -> <annotation>``, or ``None`` if there is no return annotation
        :return: a tuple with the revised signature and return annotation
        """
        pass

    def __call__(
        self,
        app: Sphinx,
        what: str,
        name: str,
        obj: object,
        options: object,
        signature: Optional[str],
        return_annotation: Optional[str],
    ) -> Optional[Tuple[Optional[str], Optional[str]]]:
        try:
            return self.process(
                app=app,
                what=what,
                name=name,
                obj=obj,
                options=options,
                signature=signature,
                return_annotation=return_annotation,
            )
        except Exception as e:
            log.error(repr(e))
            raise


class AutodocSkipMember(SphinxCallback, metaclass=ABCMeta):
    """
    An *autodoc-skip-member* processor.
    """

    @property
    def event(self) -> str:
        """
        ``"autodoc-skip-member"``
        """
        return "autodoc-skip-member"

    @abstractmethod
    def process(
        self,
        app: Sphinx,
        what: str,
        name: str,
        obj: object,
        skip: bool,
        options: object,
    ) -> Optional[bool]:
        """
        Decide whether a member should be included in the documentation.

        :param app: the Sphinx application object
        :param what: the type of the object which the docstring belongs to (one of
            "module", "class", "exception", "function", "method", "attribute")
        :param name: the fully qualified name of the object
        :param obj: the object itself
        :param skip: a boolean indicating if autodoc will skip this member if the user
            handler does not override the decision
        :param options: the options given to the directive: an object with attributes
            ``inherited_members``, ``undoc_members``, ``show_inheritance`` and
            ``noindex`` that are ``True`` if the flag option of same name was given to
            the auto directive
        :return: ``True`` if the member should be excluded; ``False`` if the member
            should be included; ``None`` to fall back to the skipping behavior of
            autodoc and other enabled extensions


        """
        pass

    def __call__(
        self,
        app: Sphinx,
        what: str,
        name: str,
        obj: object,
        skip: bool,
        options: object,
    ) -> Optional[bool]:
        try:
            return self.process(
                app=app, what=what, name=name, obj=obj, skip=skip, options=options
            )
        except Exception as e:
            log.error(repr(e))
            raise


class AutodocProcessBases(SphinxCallback, metaclass=ABCMeta):
    """
    An *autodoc-process-bases* processor.
    """

    @property
    def event(self) -> str:
        """
        ``autodoc-process-bases``
        """
        return "autodoc-process-bases"

    @abstractmethod
    def process(
        self, app: Sphinx, name: str, obj: object, options: object, bases: List[type]
    ) -> None:
        """
        Decide whether a member should be included in the documentation.

        :param app: the Sphinx application object
        :param name: the fully qualified name of the object
        :param obj: the object itself
        :param options: the options given to the directive: an object with attributes
            ``inherited_members``, ``undoc_members``, ``show_inheritance`` and
            ``noindex`` that are ``True`` if the flag option of same name was given to
            the auto directive
        :param bases: list of classes that the event handler can modify in place to
            change what Sphinx puts into the output
        """
        pass

    def __call__(
        self, app: Sphinx, name: str, obj: object, options: object, bases: List[type]
    ) -> None:
        try:
            self.process(app=app, name=name, obj=obj, options=options, bases=bases)
        except Exception as e:
            log.error(repr(e))
            raise


#
# validate __all__
#

__tracker.validate()
