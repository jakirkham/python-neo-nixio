# Data model mapping between Neo and NIX

## neo.Block

Maps directly to `nix.Block`.
  - Attributes

    | Neo                           | NIX                                  |
    |-------------------------------|--------------------------------------|
    | Block.name(string)            | Block.name(string)                   |
    | Block.description(string)     | Block.definition(string)             |
    | Block.rec\_datetime(datetime)  | Block.created\_at(int)                |
    | Block.file\_datetime(datetime) | Block.metadata(**Section**) [[1]](#notes) |
    | Block.file\_origin(string)     | Block.metadata(**Section**) [[1]](#notes) |

  - Objects
    - neo.Block.segments(**Segment**[]):  
    Maps directly to nix.Block.groups(**Group**[]).
    See the [neo.Segment](#neosegment) section for details.
    - neo.Block.recordingchannelgroups(**RecordingChannelGroup**[]):  
    Maps to nix.Block.sources(**Source**[]) with `type = "neo.recordingchannelgroup"`.
    See the [neo.RecordingChannelGroup](#neorecordingchannelgroup) section for details.


## neo.Segment

Maps directly to `nix.Group`.
  - Attributes

    | Neo                              | NIX                                  |
    |----------------------------------|--------------------------------------|
    | Segment.name(string)             | Group.name(string)                   |
    | Segment.description(string)      | Group.definition(string)             |
    | Segment.rec\_datetime(datetime)  | Group.created\_at(int)              |
    | Segment.file\_datetime(datetime) | Group.metadata(**Section**) [[1]](#notes) |
    | Segment.file\_origin(string)     | Group.metadata(**Section**) [[1]](#notes) |

  - Objects
    - Segment.analogsignals(**AnalogSignal**[]) & Segment.irregularlysampledsignals(**IrregularlySampledSignal**[]):  
    For each item in both lists, a `nix.DataArray` is created which holds the signal data and attributes.
    The `type` attribute of the `DataArray` is set to `neo.analogsignal` or `neo.irregularlysampledsignal` accordingly.
    These are stored in the `Group.data_arrays` list.
    See the [neo.AnalogSignal](#neoanalogsignal) and [neo.IrregularlySampledSignal](#neoirregularlysampledsignal) sections for details.
      - Signal objects in Neo can be grouped, e.g., `Segment.analogsignals` is a list of `AnalogSignal` objects, each of which can hold multiple signals.
      In order to be able to reconstruct the original signal groupings, all `DataArray` objects that belong to the same `AnalogSignal` (or `IrregularlySampledSignal`) have their `metadata` attribute point to the same `Section`.
    - Segment.epochs(**Epoch**[]):  
    For each item in `Segment.epochs`, a `nix.MultiTag` is created with `type = neo.epoch`.
    This is stored in the `Group.multi_tags` list.
    See the [neo.Epoch](#neoepoch) section for details.
    - Segment.events(**Event**[]):  
    For each item in `Segment.events`, a `nix.MultiTag` is created with `type = neo.event`.
    This is stored in the `Group.multi_tags` list.
    See the [neo.Event](#neoevent) section for details.
    - Segment.spiketrains(**SpikeTrain**[]):  
    For each item in `Segment.spiketrains`, a `nix.MultiTag` is created with `type = neo.spiketrain`.
    This is stored in the `Group.multi_tags` list.
    See the [neo.SpikeTrain](#neospiketrain) section for details.


## neo.RecordingChannelGroup

Maps to nix.Source with `type = neo.recordingchannelgroup`.

  - Attributes

    | Neo                                       | NIX                                   |
    |-------------------------------------------|---------------------------------------|
    | RecordingChannelGroup.name(string)        | Source.name(string)                   |
    | RecordingChannelGroup.description(string) | Source.definition(string)             |
    | RecordingChannelGroup.file_origin(string) | Source.metadata(**Section**) [[1]](#notes) |
    | RecordingChannelGroup.coordinates(Quantity 2D) | Source.metadata(**Section**) [[1]](#notes) |

    - RecordingChannelGroup.channel_indexes:  
    Are not mapped into any NIX object or attribute.
    When converting from NIX to Neo, the channel indexes are reconstructed from the contained `nix.Source` objects [[2]](#notes).

For each object contained in the group lists (`units`, `analogsignals`, `irregularlysampledsignals`), a child nix.Source is created with `type = neo.recordingchannel`.
Each `Source.name` is taken from the `RecordingChannelGroup.channel_names` array.
The sources also inherit the container's `metadata`.
The `Source.definition` string is constructed by appending the `Source.name` to container's `Source.definition`.

Each of the `nix.Source` objects that are created as children of a `neo.RecordingChannelGroup` are referenced by:
  - The corresponding `DataArray`, in the case of sources which were created from the `analogsignals` and `irregularlysampledsignals` lists.
  - The corresponding `MultiTag`, in the case of sources which were created from the `units` list.
      - These `MultiTag` objects also contain a second `Source` of type `neo.unit`.


## neo.AnalogSignal

Maps to a `nix.DataArray` with `type = neo.analogsignal`.

  - Attributes

    | Neo                           | NIX                                  |
    |-------------------------------|--------------------------------------|
    | AnalogSignal.name(string)            | DataArray.name(string)                   |
    | AnalogSignal.description(string)     | DataArray.definition(string)             |
    | AnalogSignal.file_origin(string)     | DataArray.metadata(**Section**) [[1]](#notes) |

  - Objects
    - AnalogSignal.signal(Quantity 2D):  
      - Maps directly to `DataArray.data(DataType[])`.
      - `DataArray.unit(string)` is set based on the units of the Quantity array (`AnalogSignal.signal`).
      - `DataArray.dimensions(Dimension[])` contains two objects:
          - A `SampledDimension` to denote that the signals are regularly sampled.
          The attributes of this dimension are:
              - `sampling_interval` assigned from the value of `AnalogSignal.sampling_rate(Quantity scalar)`.
              - `offset` assigned from the value of `AnalogSignal.t_start(Quantity scalar)`.
              - `unit` inheriting the value of the `DataArray.unit`.
        - A `SetDimension` to denote that the second dimension represents a set (collection) of signals.


## neo.IrregularlySampledSignal

Maps to a `nix.DataArray` with `type = neo.irregularlysampledsignal`.

  - Attributes

    | Neo                           | NIX                                  |
    |-------------------------------|--------------------------------------|
    | IrregularlySampledSignal.name(string)            | DataArray.name(string)                   |
    | IrregularlySampledSignal.description(string)     | DataArray.definition(string)             |
    | IrregularlySampledSignal.file_origin(string)     | DataArray.metadata(**Section**) [[1]](#notes) |

  - Objects
    - IrregularlySampledSignal.signal(Quantity 2D):  
      - Maps directly to `DataArray.data(DataType[])`.
      - `DataArray.unit(string)` is set based on the units of the Quantity array (`IrregularlySampledSignal.signal`).
      - `DataArray.dimensions(Dimension[])` contains two objects:
          - A `RangeDimension` to denote that the signals are irregularly sampled.
          The attributes of this dimension are:
              - `ticks` assigned from the value of `IrregularlySampledSignal.times(Quantity 1D)`.
              - `unit` inheriting the value of the `DataArray.unit`.
        - A `SetDimension` to denote that the second dimension represents a set (collection) of signals.


## neo.Epoch

Maps to a `nix.MultiTag` with `type = neo.epoch`.

  - Attributes

    | Neo                           | NIX                                  |
    |-------------------------------|--------------------------------------|
    | Epoch.name(string)            | MultiTag.name(string)                   |
    | Epoch.description(string)     | MultiTag.definition(string)             |
    | Epoch.file_origin(string)     | MultiTag.metadata(**Section**) [[1]](#notes) |

  - Objects
    - Epoch.times(Quantity 1D) maps to `MultiTag.positions(DataArray)` with type `neo.epoch.times`.
    - Epoch.durations(Quantity 1D) maps to `MultiTag.extents(DataArray)` with type `neo.epoch.durations`.
    - Epoch.labels(string[]) maps to the `label` attribute of each `DataArray` referenced by `MultiTag.positions`.


## neo.Event

Maps to a `nix.MultiTag` with `type = neo.event`.

  - Attributes

    | Neo                           | NIX                                  |
    |-------------------------------|--------------------------------------|
    | Event.name(string)            | MultiTag.name(string)                   |
    | Event.description(string)     | MultiTag.definition(string)             |
    | Event.file_origin(string)     | MultiTag.metadata(**Section**) [[1]](#notes) |

  - Objects
    - Event.times(Quantity 1D) maps to `MultiTag.positions(DataArray)` with type `neo.event.times`.
    - Event.labels(string[]) maps to the `label` attribute of each `DataArray` referenced by `MultiTag.positions`.


## neo.SpikeTrain

Maps to a `nix.MultiTag` with `type = neo.spiketrain`.

  - Attributes

    | Neo                           | NIX                                  |
    |-------------------------------|--------------------------------------|
    | SpikeTrain.name(string)                | MultiTag.name(string)                   |
    | SpikeTrain.description(string)         | MultiTag.definition(string)             |
    | SpikeTrain.file_origin(string)         | MultiTag.metadata(**Section**) [[1]](#notes) |
    | SpikeTrain.t_start(Quantity scalar)    | MultiTag.metadata(**Section**) [[1]](#notes) |
    | SpikeTrain.t_stop(Quantity scalar)     | MultiTag.metadata(**Section**) [[1]](#notes) |
    | SpikeTrain.left_sweep(Quantity scalar) | MultiTag.metadata(**Section**) [[1]](#notes) |

  - Objects
    - SpikeTrain.times(Quantity 1D):  
    Maps directly to `MultiTag.positions(DataArray)`.
      - The positions `DataArray` is of type `neo.spiketrain` and has a single `SetDimension`.
    - SpikeTrain.waveforms(Quantity 3D):  
    Waveform data and metadata associated with spikes are stored in a `DataArray` of type `neo.waveforms`.
    The `DataArray` is associated with the spiketrain `MultiTag` via a `nix.Feature`.
    Specifically, `MultiTag.features` holds a reference to a single `Feature` with `link_type = indexed`.
    `Feature.data` refers to the `DataArray` where the waveforms are stored.
    The `DataArray` also refers to a `metadata` Section that stores the `left_sweep` value.
    The `DataArray` has 3 dimensions:
      - `SetDimension`.
      - `SetDimension`.
      - `SampledDimension`: The `SpikeTrain.sampling_rate` is stored in this dimension's `sampling_interval` and the `unit` is set accordingly.


## neo.Unit

Maps to a `nix.Source` with `type = neo.unit`.

  - Attributes

    | Neo                           | NIX                                  |
    |-------------------------------|--------------------------------------|
    | Unit.name(string)                | Source.name(string)                   |
    | Unit.description(string)         | Source.definition(string)             |
    | Unit.file_origin(string)         | Source.metadata(**Section**) [[1]](#notes) |

  - Objects
    - Unit.spiketrains is represented by the `MultiTag` which references a given `nix.Source` object.
    See the description of the mapping for [neo.RecordingChannelGroup](#neorecordingchannelgroup).


-------

## Notes:
  1. The NIX objects each hold only one `metadata` attribute.
  Neo attributes such as `file_datetime` and `file_origin` are mapped to properties within the same `nix.Section` to which the `metadata` attribute refers.
  A metadata section is only created for a NIX object if necessary, i.e., it is not created if the Neo object attributes are not set.
  The `Section.name` should match the corresponding NIX object `name`.
  2. The role of `channel_indexes` in `neo.RecordingChannelGroup` is still unclear.
  The mapping is still not complete and is therefore subject to change.