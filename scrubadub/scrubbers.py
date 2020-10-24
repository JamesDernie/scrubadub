import warnings
from typing import Optional, Sequence, Generator, Dict, Type, Union, List

from . import detectors
from . import post_processors
from .detectors import Detector
from .post_processors import PostProcessor
from .filth import Filth


class Scrubber(object):
    """The Scrubber class is used to clean personal information out of dirty
    dirty text. It manages a set of ``Detector``'s that are each responsible
    for identifying their particular kind of ``Filth``.
    """

    def __init__(self, detector_list: Optional[Sequence[Union[Type[Detector], Detector, str]]] = None,
                 post_processor_list: Optional[Sequence[Union[Type[PostProcessor], PostProcessor, str]]] = None):
        super().__init__()

        # instantiate all of the detectors which, by default, uses all of the
        # detectors that are in the detectors.types dictionary
        self._detectors = {}  # type: Dict[str, Detector]
        self._post_processors = []  # type: List[PostProcessor]

        if detector_list is None:
            detector_list = [
                config['detector']
                for name, config in detectors.detector_configuration.items()
                if config['autoload']
            ]

        for detector in detector_list:
            self.add_detector(detector)

        if post_processor_list is None:
            post_processor_list = [
                config['post_processor']
                for config in sorted(
                    post_processors.post_processor_configuration.values(),
                    key=lambda x: x['index'],
                )
                if config['autoload']
            ]

        for post_processor in post_processor_list:
            self.add_post_processor(post_processor)

    def add_detector(self, detector: Union[Detector, Type[Detector], str]):
        """Add a ``Detector`` to scrubadub"""
        if isinstance(detector, type):
            if not issubclass(detector, Detector):
                raise TypeError((
                    '"%(detector)s" is not a subclass of Detector'
                ) % locals())
            self._check_and_add_detector(detector())
        elif isinstance(detector, Detector):
            self._check_and_add_detector(detector)
        elif isinstance(detector, str):
            if detector in detectors.detector_configuration:
                self._check_and_add_detector(detectors.detector_configuration[detector]['detector']())
            else:
                raise ValueError("Unknown Detector: {}".format(detector))

    def remove_detector(self, detector: Union[Detector, Type[Detector], str]):
        """Remove a ``Detector`` from scrubadub"""
        if isinstance(detector, type):
            self._detectors.pop(detector().name)
        elif isinstance(detector, detectors.base.Detector):
            self._detectors.pop(detector.name)
        elif isinstance(detector, str):
            self._detectors.pop(detector)

    def _check_and_add_detector(self, detector: Detector):
        """Check the types and add the detector to the scrubber"""
        if not isinstance(detector, Detector):
            raise TypeError((
                'The detector "{}" is not an instance of the '
                'Detector class.'
            ).format(detector))
        name = detector.name
        if name in self._detectors:
            raise KeyError((
                'can not add Detector "%(name)s" to this Scrubber, this name is already in use. '
                'Try removing it first.'
            ) % locals())
        self._detectors[name] = detector

    def add_post_processor(self, post_processor: Union[PostProcessor, Type[PostProcessor], str], index: int = None):
        """Add a ``Detector`` to scrubadub"""
        if isinstance(post_processor, type):
            if not issubclass(post_processor, PostProcessor):
                raise TypeError((
                    '"%(post_processor)s" is not a subclass of PostProcessor'
                ) % locals())
            self._check_and_add_post_processor(post_processor(), index=index)
        elif isinstance(post_processor, PostProcessor):
            self._check_and_add_post_processor(post_processor, index=index)
        elif isinstance(post_processor, str):
            if post_processor in post_processors.post_processor_configuration:
                self._check_and_add_post_processor(
                    post_processors.post_processor_configuration[post_processor]['post_processor'](), index=index
                )
            else:
                raise ValueError("Unknown PostProcessor: {}".format(post_processor))

    def remove_post_processor(self, post_processor: Union[PostProcessor, Type[PostProcessor], str]):
        """Remove a ``Detector`` from scrubadub"""
        if isinstance(post_processor, type):
            self._post_processors = [x for x in self._post_processors if x.name != post_processor().name]
        elif isinstance(post_processor, post_processors.base.PostProcessor):
            self._post_processors = [x for x in self._post_processors if x.name != post_processor.name]
        elif isinstance(post_processor, str):
            self._post_processors = [x for x in self._post_processors if x.name != post_processor]

    def _check_and_add_post_processor(self, post_processor: PostProcessor, index: int = None):
        """Check the types and add the PostProcessor to the scrubber"""
        if not isinstance(post_processor, PostProcessor):
            raise TypeError((
                'The PostProcessor "{}" is not an instance of the '
                'PostProcessor class.'
            ).format(post_processor))
        name = post_processor.name
        if name in [pp.name for pp in self._post_processors]:
            raise KeyError((
                'can not add PostProcessor "%(name)s" to this Scrubber, this name is already in use. '
                'Try removing it first.'
            ) % locals())
        if index is None:
            self._post_processors.append(post_processor)
        else:
            self._post_processors.insert(index, post_processor)

    def clean(self, text: str, **kwargs) -> str:
        """This is the master method that cleans all of the filth out of the
        dirty dirty ``text``. All keyword arguments to this function are passed
        through to the  ``Filth.replace_with`` method to fine-tune how the
        ``Filth`` is cleaned.
        """
        if 'replace_with' in kwargs:
            warnings.warn("Use of replace_with is depreciated in favour of using PostProcessors", DeprecationWarning)

        # We are collating all Filths so that they can all be passed to the post processing step together.
        # This is needed for some operations within the PostProcesssors.
        # It could be improved if we know which post processors need collated Filths.
        filth_list = list(self.iter_filth(text))  # type: Sequence[Filth]
        filth_list = self._post_process_filth_list(filth_list)
        return self._replace_text(text=text, filth_list=filth_list, **kwargs)

    def clean_documents(self, documents: Union[Sequence[str], Dict[str, str]], **kwargs) -> \
            Union[Dict[str, str], Sequence[str]]:
        """This is the master method that cleans all of the filth out of the
        dirty dirty ``text``. All keyword arguments to this function are passed
        through to the  ``Filth.replace_with`` method to fine-tune how the
        ``Filth`` is cleaned.
        """
        if 'replace_with' in kwargs:
            warnings.warn("Use of replace_with is depreciated in favour of using PostProcessors", DeprecationWarning)

        # We are collating all Filths so that they can all be passed to the post processing step together.
        # This is needed for some operations within the PostProcesssors.
        # It could be improved if we know which post processors need collated Filths.
        filth_list = []  # type: Sequence[Filth]
        if isinstance(documents, list):
            filth_list = [
                filth
                for name, document in enumerate(documents)
                for filth in self.iter_filth(document, document_name=str(name))
            ]
        elif isinstance(documents, dict):
            filth_list = [
                filth
                for name, document in documents.items()
                for filth in self.iter_filth(document, document_name=name)
            ]
        else:
            raise TypeError(
                'documents type should be one of: list of strings or a dict of strings with the key as the '
                'document title.'
            )

        filth_list = self._post_process_filth_list(filth_list)

        if isinstance(documents, list):
            return [
                self._replace_text(text=text, filth_list=filth_list, document_name=str(name), **kwargs)
                for name, text in enumerate(documents)
            ]
        elif isinstance(documents, dict):
            return {
                name: self._replace_text(text=text, filth_list=filth_list, document_name=name, **kwargs)
                for name, text in documents.items()
            }
        return []

    def _replace_text(
            self, text: str, filth_list: Sequence[Filth], document_name: Optional[str] = None, **kwargs
    ) -> str:
        if document_name is not None:
            filth_list = [filth for filth in filth_list if filth.document_name == document_name]

        filth_list = self._sort_filths(filth_list)  # TODO: expensive sort may not be needed
        clean_chunks = []
        filth = Filth()
        for next_filth in filth_list:
            clean_chunks.append(text[filth.end:next_filth.beg])
            if next_filth.replacement_string is not None:
                clean_chunks.append(next_filth.replacement_string)
            else:
                clean_chunks.append(next_filth.replace_with(**kwargs))
            filth = next_filth
        clean_chunks.append(text[filth.end:])
        return u''.join(clean_chunks)

    def _post_process_filth_list(self, filth_list: Sequence[Filth]) -> Sequence[Filth]:
        # We are collating all Filths so that they can all be passed to the post processing step together.
        # This is needed for some operations within the PostProcesssors.
        # It could be improved if we know which post processors need collated Filths.
        for post_processor in self._post_processors:
            filth_list = post_processor.process_filth(filth_list)

        return filth_list

    def iter_filth(
            self, text: str, document_name: Optional[str] = None, run_post_processors: bool = True,
            exclude_detectors: Optional[List[str]] = None
    ) -> Generator[Filth, None, None]:
        """Iterate over the different types of filth that can exist.
        """
        # currently doing this by aggregating all_filths and then sorting
        # inline instead of with a Filth.__cmp__ method, which is apparently
        # much slower http://stackoverflow.com/a/988728/564709
        #
        # NOTE: we could probably do this in a more efficient way by iterating
        # over all detectors simultaneously. just trying to get something
        # working right now and we can worry about efficiency later
        all_filths = []  # type: List[Filth]
        for name, detector in self._detectors.items():
            if exclude_detectors is None or name not in exclude_detectors:
                for filth in detector.iter_filth(text, document_name=document_name):
                    if not isinstance(filth, Filth):
                        raise TypeError('iter_filth must always yield Filth')
                    all_filths.append(filth)

        # This is split up so that we only have to use lists if we have to post_process Filth
        if run_post_processors:
            all_filths = list(self._merge_filths(all_filths))
            all_filths = list(self._post_process_filth_list(all_filths))

            # Here we loop over a list of Filth...
            for filth in all_filths:
                yield filth
        else:
            # ... but here, we're using a generator. If we try to use the same variable it would have two types and
            # fail static typing in mypy
            for filth in self._merge_filths(all_filths):
                yield filth

    def iter_filth_documents(
            self,
            documents: Union[Sequence[str], Dict[str, str]],
            run_post_processors: bool = True
    ) -> Generator[Filth, None, None]:
        """Iterate over the different types of filth that can exist."""
        if not isinstance(documents, (dict, list)):
            raise TypeError('documents must be one of a string, list of strings or dict of strings.')

        # Figures out which detectors have iter_filth_documents and applies to them

        document_detectors_names = []
        filth_list = []

        for name, detector in self._detectors.items():
            document_iterator = getattr(detector, 'iter_filth_documents', None)
            if callable(document_iterator):
                document_detectors_names.append(name)
                for filth in document_iterator(documents):
                    filth_list.append(filth)

        if run_post_processors:
            # Only collect the filts into a list if we need to do post processing
            if isinstance(documents, dict):
                filth_list += [
                    filth
                    for name, text in documents.items()
                    for filth in self.iter_filth(text, document_name=name, run_post_processors=False,
                                                 exclude_detectors=document_detectors_names)
                ]
            elif isinstance(documents, list):
                filth_list += [
                    filth
                    for i_name, text in enumerate(documents)
                    for filth in self.iter_filth(text, document_name=str(i_name), run_post_processors=False,
                                                 exclude_detectors=document_detectors_names)
                ]

            for filth in self._post_process_filth_list(filth_list):
                yield filth
        else:
            # Use generators when we dont post process the Filth
            if isinstance(documents, dict):
                for name, text in documents.items():
                    for filth in self.iter_filth(text, document_name=name, run_post_processors=False,
                                                 exclude_detectors=document_detectors_names):
                        yield filth
            elif isinstance(documents, list):
                for i_name, text in enumerate(documents):
                    for filth in self.iter_filth(text, document_name=str(i_name), run_post_processors=False,
                                                 exclude_detectors=document_detectors_names):
                        yield filth

    @staticmethod
    def _sort_filths(filth_list: Sequence[Filth]) -> List[Filth]:
        """Sorts a list of filths, needed before merging and concatenating"""
        # Sort by start position. If two filths start in the same place then
        # return the longer one first
        filth_list = list(filth_list)
        filth_list.sort(key=lambda f: (
            str(getattr(f, 'document_name', None) if hasattr(f, 'document_name') else ''), f.beg, -f.end
        ))
        return filth_list

    @staticmethod
    def _merge_filths(filth_list: Sequence[Filth]) -> Generator[Filth, None, None]:
        """This is where the Scrubber does its hard work and merges any
        overlapping filths.
        """
        if not filth_list:
            return

        document_name_set = {f.document_name for f in filth_list}
        document_names = []  # type: Sequence[Optional[str]]
        if None in document_name_set:
            list_with_none = [None]  # type: Sequence[Optional[str]]
            list_with_others = sorted([x for x in document_name_set if x is not None])  # type: Sequence[Optional[str]]
            document_names = list(list_with_none) + list(list_with_others)
        else:
            document_names = sorted([x for x in document_name_set if x is not None])

        for document_name in document_names:
            document_filth_list = Scrubber._sort_filths([f for f in filth_list if f.document_name == document_name])

            filth = document_filth_list[0]
            for next_filth in document_filth_list[1:]:
                if filth.end < next_filth.beg:
                    yield filth
                    filth = next_filth
                else:
                    filth = filth.merge(next_filth)
            yield filth
