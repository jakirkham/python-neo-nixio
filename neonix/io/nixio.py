# Copyright (c) 2014, German Neuroinformatics Node (G-Node)
#                     Achilleas Koutsou <achilleas.k@gmail.com>
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted under the terms of the BSD License. See
# LICENSE file in the root of the Project.

from __future__ import absolute_import

import time


from neo.io.baseio import BaseIO
from neo.core import (Block, Segment, RecordingChannelGroup, AnalogSignal,
                      IrregularlySampledSignal, Epoch, Event, SpikeTrain, Unit)

try:
    import nix
except ImportError:  # pragma: no cover
    raise ImportError("Failed to import NIX (NIXPY not found). "
                      "The NixIO requires the Python bindings for NIX.")


def calculate_timestamp(dt):
    return int(time.mktime(dt.timetuple()))


class NixIO(BaseIO):
    """
    Class for reading and writing NIX files.
    """

    is_readable = False  # for now
    is_writable = True

    supported_objects = [Block, Segment, RecordingChannelGroup,
                         AnalogSignal, IrregularlySampledSignal,
                         Epoch, Event, SpikeTrain, Unit]
    readable_objects = []
    writeable_objects = [Block, Segment, RecordingChannelGroup,
                         AnalogSignal, IrregularlySampledSignal,
                         Epoch, Event, SpikeTrain, Unit]

    name = "NIX"
    extensions = ["h5"]
    mode = "file"

    def __init__(self, filename):
        """
        Initialise IO instance and NIX file.

        :param filename: Full path to the file
        """
        BaseIO.__init__(self, filename)
        self.filename = filename
        self.nix_file = nix.File.open(self.filename, nix.FileMode.Overwrite)
        self.neo_nix_map = {}

    def __del__(self):
        self.nix_file.close()

    def write_block(self, neo_block):
        """
        Convert ``neo_block`` to the NIX equivalent and write it to the file.

        :param neo_block: Neo block to be written
        :return: The new NIX Block
        """
        nix_name = neo_block.name
        if not nix_name:
            nblocks = len(self.nix_file.blocks)
            nix_name = "neo.Block{}".format(nblocks)
        nix_type = "neo.block"
        nix_definition = neo_block.description
        nix_block = self.nix_file.create_block(nix_name, nix_type)
        nix_block.definition = nix_definition
        object_path = [("block", nix_name)]
        self.neo_nix_map[id(neo_block)] = nix_block
        if neo_block.rec_datetime:
            nix_block.force_created_at(
                    calculate_timestamp(neo_block.rec_datetime)
            )
        if neo_block.file_datetime:
            block_metadata = self._get_or_init_metadata(nix_block)
            block_metadata.create_property(
                    "file_datetime",
                    nix.Value(calculate_timestamp(neo_block.file_datetime))
            )
        if neo_block.file_origin:
            block_metadata = self._get_or_init_metadata(nix_block)
            block_metadata.create_property("file_origin",
                                           nix.Value(neo_block.file_origin))
        self._copy_annotations(neo_block, nix_block, object_path)
        for segment in neo_block.segments:
            self.write_segment(segment, object_path)
        for rcg in neo_block.recordingchannelgroups:
            self.write_recordingchannelgroup(rcg, object_path)
        return nix_block

    def write_all_blocks(self, neo_blocks):
        """
        Convert all ``neo_blocks`` to the NIX equivalent and write them to the
        file.

        :param neo_blocks: List (or iterable) containing Neo blocks
        :return: A list containing the new NIX Blocks
        """
        nix_blocks = list()
        for nb in neo_blocks:
            nix_blocks.append(self.write_block(nb))
        return nix_blocks

    def write_segment(self, segment, parent_path):
        """
        Convert the provided ``segment`` to a NIX Group and write it to the NIX
        file at the location defined by ``parent_path``.

        :param segment: Neo segment to be written
        :param parent_path: Path to the parent of the new segment
        :return: The newly created NIX Group
        """
        parent_block = self._get_object_at(parent_path)
        nix_name = segment.name
        if not nix_name:
            ngroups = len(parent_block.groups)
            nix_name = "{}.Segment{}".format(parent_block.name, ngroups)
        nix_type = "neo.segment"
        nix_definition = segment.description
        nix_group = parent_block.create_group(nix_name, nix_type)
        nix_group.definition = nix_definition
        object_path = parent_path + [("group", nix_name)]
        self.neo_nix_map[id(segment)] = nix_group
        if segment.rec_datetime:
            nix_group.force_created_at(calculate_timestamp(segment.rec_datetime))
        if segment.file_datetime:
            group_metadata = self._get_or_init_metadata(nix_group, object_path)
            group_metadata .create_property(
                    "file_datetime",
                    nix.Value(calculate_timestamp(segment.file_datetime))
            )
        if segment.file_origin:
            group_metadata = self._get_or_init_metadata(nix_group, object_path)
            group_metadata.create_property("file_origin",
                                           nix.Value(segment.file_origin))
        self._copy_annotations(segment, nix_group, object_path)
        for anasig in segment.analogsignals:
            self.write_analogsignal(anasig, object_path)
        for irsig in segment.irregularlysampledsignals:
            self.write_irregularlysampledsignal(irsig, object_path)
        for ep in segment.epochs:
            self.write_epoch(ep, object_path)
        for ev in segment.events:
            self.write_event(ev, object_path)
        for sptr in segment.spiketrains:
            self.write_spiketrain(sptr, object_path)

        return nix_group

    def write_recordingchannelgroup(self, rcg, parent_path):
        """
        Convert the provided ``rcg`` (RecordingChannelGroup) to a NIX Source
        and write it to the NIX file at the location defined by ``parent_path``.

        :param rcg: The Neo RecordingChannelGroup to be written
        :param parent_path: Path to the parent of the new segment
        :return: The newly created NIX Source
        """
        parent_block = self._get_object_at(parent_path)
        nix_name = rcg.name
        if not nix_name:
            nsources = len(parent_block.sources)
            nix_name = "{}.RecordingChannelGroup{}".format(parent_block.name,
                                                           nsources)
        nix_type = "neo.recordingchannelgroup"
        nix_definition = rcg.description
        nix_source = parent_block.create_source(nix_name, nix_type)
        nix_source.definition = nix_definition
        object_path = parent_path + [("source", nix_name)]
        self.neo_nix_map[id(rcg)] = nix_source
        if rcg.file_origin:
            source_metadata = self._get_or_init_metadata(nix_source,
                                                         object_path)
            source_metadata.create_property("file_origin",
                                            nix.Value(rcg.file_origin))
        self._copy_annotations(rcg, nix_source, object_path)
        for idx, channel in enumerate(rcg.channel_indexes):
            # create a child source object to represent the individual channel
            if len(rcg.channel_names):
                nix_chan_name = rcg.channel_names[idx]
            else:
                nix_chan_name = "{}.{}".format(nix_name, idx)
            nix_chan_type = "neo.recordingchannel"
            nix_chan = nix_source.create_source(nix_chan_name, nix_chan_type)
            nix_chan.definition = nix_definition
            chan_obj_path = object_path + [("source", nix_chan_name)]
            if rcg.file_origin:
                chan_metadata = self._get_or_init_metadata(nix_chan,
                                                           chan_obj_path)
                chan_metadata.create_property("file_origin",
                                              nix.Value(rcg.file_origin))

            if hasattr(rcg, "coordinates"):
                chan_coords = rcg.coordinates[idx]
                chan_metadata = self._get_or_init_metadata(nix_chan,
                                                           chan_obj_path)

                nix_coord_values = tuple(nix.Value(c.magnitude.item())
                                         for c in chan_coords)
                nix_coord_units = tuple(nix.Value(str(c.dimensionality))
                                        for c in chan_coords)
                chan_metadata.create_property("coordinates",
                                              nix_coord_values)
                chan_metadata.create_property("coordinates.units",
                                              nix_coord_units)
        for unit in rcg.units:
            self.write_unit(unit, object_path)

        # add signal references
        for nix_asigs in self._get_mapped_objects(rcg.analogsignals):
            # One AnalogSignal maps to list of DataArrays
            for da in nix_asigs:
                da.sources.append(nix_source)
        for nix_isigs in self._get_mapped_objects(rcg.irregularlysampledsignals):
            # One IrregularlySampledSignal maps to list of DataArrays
            for da in nix_isigs:
                da.sources.append(nix_source)

        return nix_source

    def write_analogsignal(self, anasig, parent_path):
        """
        Convert the provided ``anasig`` (AnalogSignal) to a list of NIX
        DataArray objects and write them to the NIX file at the location defined
        by ``parent_path``. All DataArray objects created from the same
        AnalogSignal have their metadata section point to the same object.

        :param anasig: The Neo AnalogSignal to be written
        :param parent_path: Path to the parent of the new segment
        :return: A list containing the newly created NIX DataArrays
        """
        parent_group = self._get_object_at(parent_path)
        parent_block = self._get_object_at([parent_path[0]])
        nix_name = anasig.name
        if not nix_name:
            nda = len(parent_block.data_arrays)
            nix_name = "{}.AnalogSignal{}".format(parent_block.name, nda)
        nix_type = "neo.analogsignal"
        nix_definition = anasig.description
        parent_metadata = self._get_or_init_metadata(parent_group, parent_path)
        anasig_group_segment = parent_metadata.create_section(
            nix_name, nix_type+".metadata"
        )

        if anasig.file_origin:
            anasig_group_segment.create_property("file_origin",
                                                 nix.Value(anasig.file_origin))
        if anasig.annotations:
            NixIO._add_annotations(anasig.annotations, anasig_group_segment)

        # common properties
        data_units = str(anasig.units.dimensionality)
        # often sampling period is in 1/Hz or 1/kHz - simplifying to s
        time_units = str(anasig.sampling_period.units.dimensionality.simplified)
        # rescale after simplification
        offset = anasig.t_start.rescale(time_units).item()
        sampling_interval = anasig.sampling_period.rescale(time_units).item()

        nix_data_arrays = list()
        for idx, sig in enumerate(anasig.transpose()):
            nix_data_array = parent_block.create_data_array(
                "{}.{}".format(nix_name, idx),
                nix_type,
                data=sig.magnitude
            )
            nix_data_array.definition = nix_definition
            nix_data_array.unit = data_units

            timedim = nix_data_array.append_sampled_dimension(sampling_interval)
            timedim.unit = time_units
            timedim.label = "time"
            timedim.offset = offset
            chandim = nix_data_array.append_set_dimension()
            parent_group.data_arrays.append(nix_data_array)
            # point metadata to common section
            nix_data_array.metadata = anasig_group_segment
            nix_data_arrays.append(nix_data_array)
        self.neo_nix_map[id(anasig)] = nix_data_arrays
        return nix_data_arrays

    def write_irregularlysampledsignal(self, irsig, parent_path):
        """
        Convert the provided ``irsig`` (IrregularlySampledSignal) to a list of
        NIX DataArray objects and write them to the NIX file at the location
        defined by ``parent_path``. All DataArray objects created from the same
        IrregularlySampledSignal have their metadata section point to the same
        object.

        :param irsig: The Neo IrregularlySampledSignal to be written
        :param parent_path: Path to the parent of the new
        :return: The newly created NIX DataArray
        """
        parent_group = self._get_object_at(parent_path)
        parent_block = self._get_object_at([parent_path[0]])
        nix_name = irsig.name
        if not nix_name:
            nda = len(parent_block.data_arrays)
            nix_name = "{}.IrregularlySampledSignal{}".format(parent_block.name,
                                                              nda)
        nix_type = "neo.irregularlysampledsignal"
        nix_definition = irsig.description
        parent_metadata = self._get_or_init_metadata(parent_group, parent_path)
        irsig_group_segment = parent_metadata.create_section(
            nix_name, nix_type+".metadata"
        )

        if irsig.file_origin:
            irsig_group_segment.create_property("file_origin",
                                                nix.Value(irsig.file_origin))

        if irsig.annotations:
            NixIO._add_annotations(irsig.annotations, irsig_group_segment)

        # common properties
        data_units = str(irsig.units.dimensionality)
        time_units = str(irsig.times.units.dimensionality)
        times = irsig.times.magnitude.tolist()

        nix_data_arrays = list()
        for idx, sig in enumerate(irsig.transpose()):
            nix_data_array = parent_block.create_data_array(
                "{}.{}".format(nix_name, idx),
                nix_type,
                data=sig.magnitude
            )
            nix_data_array.definition = nix_definition
            nix_data_array.unit = data_units

            timedim = nix_data_array.append_range_dimension(times)
            timedim.unit = time_units
            timedim.label = "time"
            chandim = nix_data_array.append_set_dimension()
            parent_group.data_arrays.append(nix_data_array)
            # point metadata to common section
            nix_data_array.metadata = irsig_group_segment
            nix_data_arrays.append(nix_data_array)
        self.neo_nix_map[id(irsig)] = nix_data_arrays
        return nix_data_arrays

    def write_epoch(self, ep, parent_path):
        """
        Convert the provided ``ep`` (Epoch) to a NIX MultiTag and write it to
        the NIX file at the location defined by ``parent_path``.

        :param ep: The Neo Epoch to be written
        :param parent_path: Path to the parent of the new MultiTag
        :return: The newly created NIX MultiTag
        """
        parent_group = self._get_object_at(parent_path)
        parent_block = self._get_object_at([parent_path[0]])
        nix_name = ep.name
        if not nix_name:
            nmt = len(parent_group.multi_tags)
            nix_name = "{}.Epoch{}".format(parent_group.name, nmt)
        nix_type = "neo.epoch"
        nix_definition = ep.description

        # times -> positions
        times = ep.times.magnitude
        time_units = str(ep.times.units.dimensionality)

        times_da = parent_block.create_data_array("{}.times".format(nix_name),
                                                  "neo.epoch.times",
                                                  data=times)
        times_da.unit = time_units

        # durations -> extents
        durations = ep.durations.magnitude
        duration_units = str(ep.durations.units.dimensionality)

        durations_da = parent_block.create_data_array(
            "{}.durations".format(nix_name),
            "neo.epoch.durations",
            data=durations
        )
        durations_da.unit = duration_units

        # ready to create MTag
        nix_multi_tag = parent_block.create_multi_tag(nix_name, nix_type,
                                                      times_da)
        label_dim = nix_multi_tag.positions.append_set_dimension()
        label_dim.labels = ep.labels.tolist()
        nix_multi_tag.extents = durations_da
        parent_group.multi_tags.append(nix_multi_tag)
        nix_multi_tag.definition = nix_definition
        object_path = parent_path + [("multi_tag", nix_name)]
        self.neo_nix_map[id(ep)] = nix_multi_tag

        if ep.file_origin:
            mtag_metadata = self._get_or_init_metadata(nix_multi_tag,
                                                       object_path)
            mtag_metadata.create_property("file_origin",
                                          nix.Value(ep.file_origin))
        self._copy_annotations(ep, nix_multi_tag, object_path)

        nix_multi_tag.references.extend(
            NixIO._get_contained_signals(parent_group)
        )
        return nix_multi_tag

    def write_event(self, ev, parent_path):
        """
        Convert the provided ``ev`` (Event) to a NIX MultiTag and write it to
        the NIX file at the location defined by ``parent_path``.

        :param ev: The Neo Event to be written
        :param parent_path: Path to the parent of the new MultiTag
        :return: The newly created NIX MultiTag
        """
        parent_group = self._get_object_at(parent_path)
        parent_block = self._get_object_at([parent_path[0]])
        nix_name = ev.name
        if not nix_name:
            nmt = len(parent_group.multi_tags)
            nix_name = "{}.Event{}".format(parent_group.name, nmt)
        nix_type = "neo.event"
        nix_definition = ev.description

        # times -> positions
        times = ev.times.magnitude
        time_units = str(ev.times.units.dimensionality)

        times_da = parent_block.create_data_array("{}.times".format(nix_name),
                                                  "neo.event.times",
                                                  data=times)
        times_da.unit = time_units

        # ready to create MTag
        nix_multi_tag = parent_block.create_multi_tag(nix_name, nix_type,
                                                      times_da)
        label_dim = nix_multi_tag.positions.append_set_dimension()
        label_dim.labels = ev.labels.tolist()
        parent_group.multi_tags.append(nix_multi_tag)
        nix_multi_tag.definition = nix_definition
        object_path = parent_path + [("multi_tag", nix_name)]
        self.neo_nix_map[id(ev)] = nix_multi_tag

        if ev.file_origin:
            mtag_metadata = self._get_or_init_metadata(nix_multi_tag,
                                                       object_path)
            mtag_metadata.create_property("file_origin",
                                          nix.Value(ev.file_origin))
        self._copy_annotations(ev, nix_multi_tag, object_path)

        nix_multi_tag.references.extend(
            NixIO._get_contained_signals(parent_group)
        )
        return nix_multi_tag

    def write_spiketrain(self, sptr, parent_path):
        """
        Convert the provided ``sptr`` (SpikeTrain) to a NIX MultiTag and write
        it to the NIX file at the location defined by ``parent_path``.

        :param sptr: The Neo SpikeTrain to be written
        :param parent_path: Path to the parent of the new MultiTag
        :return: The newly created NIX MultiTag
        """
        parent_obj = self._get_object_at(parent_path)
        parent_block = self._get_object_at([parent_path[0]])
        nix_name = sptr.name
        if not nix_name:
            nmt = len(parent_block.multi_tags)
            nix_name = "{}.SpikeTrain{}".format(parent_block.name, nmt)
        nix_type = "neo.spiketrain"
        nix_definition = sptr.description

        # spike times
        time_units = str(sptr.times.units.dimensionality)
        times = sptr.times.magnitude
        times_da = parent_block.create_data_array("{}.times".format(nix_name),
                                                  "neo.epoch.times",
                                                  data=times)
        times_da.unit = time_units

        # ready to create MTag
        nix_multi_tag = parent_block.create_multi_tag(nix_name, nix_type,
                                                      times_da)
        # attach MTag to parent object
        if isinstance(parent_obj, nix.Group):
            parent_obj.multi_tags.append(nix_multi_tag)
        elif isinstance(parent_obj, nix.Source):
            nix_multi_tag.sources.append(parent_obj)

        nix_multi_tag.definition = nix_definition
        object_path = parent_path + [("multi_tag", nix_name)]
        self.neo_nix_map[id(sptr)] = nix_multi_tag

        mtag_metadata = self._get_or_init_metadata(nix_multi_tag,
                                                   object_path)
        self._copy_annotations(sptr, nix_multi_tag, object_path)

        # other attributes
        if sptr.file_origin:
            mtag_metadata.create_property("file_origin",
                                          nix.Value(sptr.file_origin))
        if sptr.t_start:
            t_start = sptr.t_start.rescale(time_units).magnitude.item()
            mtag_metadata.create_property("t_start",
                                          nix.Value(t_start))
        # t_stop is not optional
        t_stop = sptr.t_stop.rescale(time_units).magnitude.item()
        mtag_metadata.create_property("t_stop", nix.Value(t_stop))

        # waveforms
        if sptr.waveforms is not None:
            wf_data = [wf.magnitude for wf in
                       [wfgroup for wfgroup in sptr.waveforms]]
            wf_name = "{}.waveforms".format(nix_name)
            waveforms_da = parent_block.create_data_array(wf_name,
                                                          "neo.waveforms",
                                                          data=wf_data)
            wf_unit = str(sptr.waveforms.units.dimensionality)
            waveforms_da.unit = wf_unit
            nix_multi_tag.create_feature(waveforms_da, nix.LinkType.Indexed)
            time_units = str(sptr.sampling_period.units.dimensionality.
                             simplified)
            sampling_interval = sptr.sampling_period.rescale(time_units).item()
            wf_spikedim = waveforms_da.append_set_dimension()
            wf_chandim = waveforms_da.append_set_dimension()
            wf_timedim = waveforms_da.append_sampled_dimension(sampling_interval)
            wf_timedim.unit = time_units
            wf_timedim.label = "time"
            wf_path = object_path + [("data_array", wf_name)]
            waveforms_da.metadata = self._get_or_init_metadata(waveforms_da,
                                                               wf_path)
            if sptr.left_sweep:
                left_sweep = sptr.left_sweep.rescale(time_units).\
                    magnitude.item()
                waveforms_da.metadata.create_property("left_sweep",
                                                      nix.Value(left_sweep))

        return nix_multi_tag

    def write_unit(self, ut, parent_path):
        """
        Convert the provided ``ut`` (Unit) to a NIX Source and write it to the
        NIX file at the location defined by ``parent_path``.

        :param ut: The Neo Unit to be written
        :param parent_path: Path to the parent of the new Source
        :return: The newly created NIX Source
        """
        parent_source = self._get_object_at(parent_path)
        nix_name = ut.name
        if not nix_name:
            nsrc = len(parent_source.sources)
            nix_name = "{}.Unit{}".format(parent_source.name, nsrc)
        nix_type = "neo.unit"
        nix_definition = ut.description
        nix_source = parent_source.create_source(nix_name, nix_type)
        nix_source.definition = nix_definition
        object_path = parent_path + [("source", nix_name)]
        self.neo_nix_map[id(ut)] = nix_source
        self._copy_annotations(ut, nix_source, object_path)

        if ut.file_origin:
            mtag_metadata = self._get_or_init_metadata(nix_source,
                                                       object_path)
            mtag_metadata.create_property("file_origin",
                                          nix.Value(ut.file_origin))

        # Make contained spike trains refer to parent rcg and new unit
        for nix_st in self._get_mapped_objects(ut.spiketrains):
            nix_st.sources.append(parent_source)
            nix_st.sources.append(nix_source)

        return nix_source

    def _get_or_init_metadata(self, nix_obj, obj_path=list()):
        """
        Creates a metadata Section for the provided NIX object if it doesn't
        have one already. Returns the new or existing metadata section.

        :param nix_obj: The object to which the Section is attached
        :param obj_path: Path to nix_obj
        :return: The metadata section of the provided object
        """
        if nix_obj.metadata is None:
            if len(obj_path) <= 1:  # nix_obj is root block
                parent_metadata = self.nix_file
            else:
                obj_parent = self._get_object_at(obj_path[:-1])
                parent_metadata = self._get_or_init_metadata(obj_parent,
                                                             obj_path[:-1])
            nix_obj.metadata = parent_metadata.create_section(
                    nix_obj.name, nix_obj.type+".metadata"
            )
        return nix_obj.metadata

    def _get_object_at(self, path):
        """
        Returns the object at the location defined by the path. ``path`` is a
        list of tuples. Each tuple contains the NIX type of each object as a
        string and the name of the object at the location in the path.
        Valid object type strings are: block, group, source, data_array, tag,
        multi_tag, feature.

        :param path: List of tuples that define a location in the file
        :return: The object at the location defined by the path
        """
        # NOTE: This could be simplified to:
        #   return parent.__getattribute__(obj_type+"s")[obj_name]
        obj = self.nix_file
        for obj_type, obj_name in path:
            if obj_type == "block":
                obj = obj.blocks[obj_name]
            elif obj_type == "group":
                obj = obj.groups[obj_name]
            elif obj_type == "source":
                obj = obj.sources[obj_name]
            elif obj_type == "data_array":
                obj = obj.data_arrays[obj_name]
            elif obj_type == "tag":
                obj = obj.tags[obj_name]
            elif obj_type == "multi_tag":
                obj = obj.multi_tags[obj_name]
            elif obj_type == "feature":
                obj = obj.features[obj_name]
            else:
                return None
        return obj

    def _get_mapped_objects(self, neo_object_list):
        return [self._get_mapped_object(neo_obj) for neo_obj in neo_object_list]

    def _get_mapped_object(self, neo_object):
        try:
            return self.neo_nix_map[id(neo_object)]
        except KeyError:
            raise KeyError("Attempting to get reference to NIX equivalent "
                           "object before writing. This can occur if a signal "
                           "or spiketrain object is referenced only by a "
                           "RecordingChannelGroup or Unit and is not part of a "
                           "Segment.")

    def _copy_annotations(self, neo_object, nix_object, object_path):
        if neo_object.annotations:
            metadata = self._get_or_init_metadata(nix_object, object_path)
            NixIO._add_annotations(neo_object.annotations, metadata)

    @staticmethod
    def _add_annotations(annotations, metadata):
            for k, v in annotations.items():
                metadata.create_property(k, nix.Value(v))

    @staticmethod
    def _get_contained_signals(obj):
        return [da for da in obj.data_arrays
                if da.type in ["neo.analogsignal",
                               "neo.irregularlysampledsignal"]]